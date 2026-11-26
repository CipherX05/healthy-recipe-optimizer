"""Substitute scoring, eligibility and ranking.

Four component scores, each on a 0..1 scale:

  health   share of the target nutrient removed (or added) on that recipe line:
           gain / max(original amount, new amount). 0 if it does not improve.
  flavor   Jaccard similarity of the two FlavorDB2 flavor-molecule sets
           (no value if either set has fewer than 10 molecules).
  cuisine  ln(1 + n) / ln(1 + n_max): n = imported recipes of this cuisine that
           use the candidate, n_max = the count for that cuisine's most used one.
  role     1.0 same cooking role, 0.6 related role (see network.role_score).

  overall = sum(weight_i x score_i), weights rescaled to sum to 1.

A component with no data is reported as None and earns no points. It is never
guessed, and the other weights are not inflated to hide the gap.

Eligibility is separate from the score. A candidate must have a compatible role
AND improve the chosen nutrient by a meaningful amount, so flavor alone can never
get it recommended. By default it must also pass the guardrails above.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import networkx as nx

from . import network, nutrition
from .matching import tokens
from .models import Ingredient, Line, Swap
from .sources.usda import NUTRIENTS


@dataclass(frozen=True)
class Goal:
    id: str
    label: str
    nutrient: str
    direction: str  # "min" | "max"


GOALS = {g.id: g for g in (
    Goal("satFat", "Reduce saturated fat", "satFat", "min"),
    Goal("calories", "Reduce calories", "calories", "min"),
    Goal("protein", "Increase protein", "protein", "max"),
    Goal("fiber", "Increase fiber", "fiber", "max"),
)}

COMPONENTS = ("health", "flavor", "cuisine", "role")
DEFAULT_WEIGHTS = {"health": 0.30, "flavor": 0.35, "cuisine": 0.25, "role": 0.10}
PRESETS = {
    "balanced": DEFAULT_WEIGHTS,
    "health_first": {"health": 0.55, "flavor": 0.20, "cuisine": 0.15, "role": 0.10},
    "flavor_first": {"health": 0.20, "flavor": 0.55, "cuisine": 0.15, "role": 0.10},
    "cuisine_first": {"health": 0.20, "flavor": 0.20, "cuisine": 0.50, "role": 0.10},
}

MIN_LINE_IMPROVEMENT = 0.02  # a swap must improve the target on its line by >2%
MIN_RECIPE_GAIN = 0.01  # ...and a line is "relevant" if it can move the recipe by 1%
MIN_REGION_RECIPES = 20  # fewer imported recipes than this gives no cuisine score
TRADEOFF_THRESHOLD = 0.05
# Nutritional suitability (project choices, shown to users).
# 1. The gain must be big enough to matter, per 100 g of the ingredient replaced.
#    Without this, 0.0 -> 0.2 g of fiber counts as a "100% better" swap.
MIN_GAIN_PER_100G = {"calories": 10.0, "satFat": 0.5, "protein": 2.0, "fiber": 1.0}
# 2. Guardrails: a swap for one goal must not sharply raise these. Each is
#    (relative rise on the line, minimum absolute rise per 100 g replaced).
#    Without this, "fewer calories" suggests butter in place of olive oil.
GUARDRAILS = {"satFat": (0.25, 2.0), "sodium": (0.25, 200.0), "calories": (0.50, 100.0)}
# Other nutrients checked for side effects: True means more is better.
TRADEOFF_NUTRIENTS = {"calories": False, "satFat": False, "sodium": False, "sugars": False,
                      "protein": True, "fiber": True}
GENERIC_NAME_WORDS = set(
    "ground plain whole light dry raw fresh red white green black heavy low fat reduced sodium "
    "brown canned cooked uncooked extra half and lean all purpose drained free nonfat soft firm "
    "style home sweet powder seed part skim meat only table wheat".split()
)


@dataclass(frozen=True)
class CuisineStats:
    region: str | None
    region_recipes: int
    counts: dict[str, int]  # ingredient id -> recipes in the region using it

    def score(self, ingredient_id: str) -> float | None:
        if not self.region or self.region_recipes < MIN_REGION_RECIPES or not self.counts:
            return None
        top = max(self.counts.values())
        if top <= 0:
            return None
        return math.log1p(self.counts.get(ingredient_id, 0)) / math.log1p(top)


def normalise_weights(weights: dict[str, float] | None) -> dict[str, float]:
    if weights is None:
        weights = DEFAULT_WEIGHTS
    unknown = set(weights) - set(COMPONENTS)
    if unknown:
        raise ValueError(f"unknown weight(s): {sorted(unknown)}")
    values = {key: float(weights.get(key, 0.0)) for key in COMPONENTS}
    if any(not math.isfinite(v) or v < 0 for v in values.values()):
        raise ValueError("weights must be finite and not negative")
    total = sum(values.values())
    if total <= 0:
        raise ValueError("at least one weight must be above zero")
    return {key: value / total for key, value in values.items()}


def health_score(original_amount: float, new_amount: float, direction: str) -> float:
    gain = original_amount - new_amount if direction == "min" else new_amount - original_amount
    largest = max(original_amount, new_amount)
    return min(1.0, gain / largest) if gain > 0 and largest > 0 else 0.0


def overall_score(components: dict[str, float | None], weights: dict[str, float]) -> float:
    return sum(weights[key] * (components[key] or 0.0) for key in COMPONENTS)


def in_title(ingredient: Ingredient, title: str) -> bool:
    """True if a distinctive word of the ingredient's name is in the recipe title."""
    name = re.sub(r"\([^)]*\)", " ", ingredient.name)
    words = set(tokens(name)) - GENERIC_NAME_WORDS
    return bool(words & set(tokens(title)))


def tradeoffs(rows: list[dict], goal: Goal) -> list[dict]:
    """Other nutrients that get materially worse (>5% of the recipe total)."""
    found = []
    for row in rows:
        key = row["key"]
        if key == goal.nutrient or key not in TRADEOFF_NUTRIENTS:
            continue
        percent = row["percent_change"]
        if percent is None:
            continue
        worse = -percent if TRADEOFF_NUTRIENTS[key] else percent
        if worse > TRADEOFF_THRESHOLD * 100:
            found.append({"key": key, "label": row["label"], "unit": row["unit"],
                          "change": row["change"], "percent_change": percent})
    return found


def _goal_row(rows: list[dict], goal: Goal) -> dict:
    return next(r for r in rows if r["key"] == goal.nutrient)


def recipe_gain(rows: list[dict], goal: Goal) -> float:
    """Improvement as a fraction of the original recipe total (positive is good)."""
    row = _goal_row(rows, goal)
    if row["original"] is None:
        return 0.0
    gain = -row["change"] if goal.direction == "min" else row["change"]
    if row["original"] > 1e-9:
        return gain / row["original"]
    return 1.0 if gain > 1e-9 else 0.0


def flavor_gap(original: Ingredient, candidate: Ingredient) -> str:
    """Say which of the two lacks a usable FlavorDB2 profile, and why."""
    problems = []
    for item in (original, candidate):
        count = len(item.molecules)
        if count == 0:
            problems.append(f"no FlavorDB2 profile for {item.name}")
        elif count < network.MIN_PROFILE_MOLECULES:
            problems.append(f"FlavorDB2 lists only {count} molecule{'' if count == 1 else 's'} for {item.name}")
    return "; ".join(problems)


def broken_guardrails(
    original: Ingredient, candidate: Ingredient, grams: float, ratio: float, goal: Goal
) -> list[str]:
    """Reasons this swap sharply raises a nutrient other than the goal."""
    reasons = []
    for key, (relative, per_100g) in GUARDRAILS.items():
        if key == goal.nutrient:
            continue
        before = nutrition.contribution(original, grams, key)
        after = nutrition.contribution(candidate, grams * ratio, key)
        if before is None or after is None or grams <= 0:
            continue  # unknown values cannot be judged; they stay visible as missing
        rise = after - before
        if rise > relative * before and rise / grams * 100 >= per_100g:
            reasons.append(
                f"raises {NUTRIENTS[key][2].lower()} on this ingredient by more than {relative:.0%}"
            )
    return reasons


def score_candidates(
    line: Line,
    lines: list[Line],
    ingredients: dict[str, Ingredient],
    graph: nx.Graph,
    goal: Goal,
    cuisine: CuisineStats,
    weights: dict[str, float],
    *,
    ratio: float = 1.0,
    min_flavor: float = 0.0,
    min_cuisine: float = 0.0,
    guardrails: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Return (eligible, rejected) candidates for one line, eligible ones ranked."""
    original = ingredients.get(line.ingredient_id or "")
    if original is None or line.grams is None:
        return [], []
    before = nutrition.contribution(original, line.grams, goal.nutrient)
    if before is None:
        return [], []

    eligible, rejected = [], []
    for candidate_id in network.neighbours(graph, original.id):
        candidate = ingredients[candidate_id]
        after = nutrition.contribution(candidate, line.grams * ratio, goal.nutrient)
        flavor = network.flavor_similarity(original, candidate)
        components = {
            "health": None if after is None else health_score(before, after, goal.direction),
            "flavor": flavor,
            "cuisine": cuisine.score(candidate_id),
            "role": network.role_score(original, candidate),
        }
        reasons = []
        if after is None:
            reasons.append(f"no {goal.nutrient} value for this ingredient")
        elif components["health"] <= MIN_LINE_IMPROVEMENT:
            reasons.append("does not improve the chosen nutrient by more than 2%")
        elif line.grams > 0 and abs(after - before) / line.grams * 100 < MIN_GAIN_PER_100G[goal.nutrient]:
            reasons.append(
                f"gain is too small to matter (under {MIN_GAIN_PER_100G[goal.nutrient]:g} "
                f"{NUTRIENTS[goal.nutrient][1]} per 100 g replaced)"
            )
        if guardrails:
            reasons += broken_guardrails(original, candidate, line.grams, ratio, goal)
        if min_flavor > 0 and (flavor is None or flavor < min_flavor):
            reasons.append("below the minimum flavor similarity")
        if min_cuisine > 0 and (components["cuisine"] is None or components["cuisine"] < min_cuisine):
            reasons.append("below the minimum cuisine compatibility")

        swap = Swap(line.id, candidate_id, ratio)
        rows = nutrition.compare(lines, ingredients, [swap])
        notes = []
        if candidate.role != original.role:
            notes.append(f"Different cooking role ({original.role_label.lower()} to "
                         f"{candidate.role_label.lower()}): texture and quantity may need adjusting.")
        if candidate.nutrition_match == "proxy" and candidate.nutrition_note:
            notes.append(candidate.nutrition_note + ".")
        flavor_detail = None
        if flavor is not None:
            flavor_detail = {
                "shared": len(original.molecules & candidate.molecules),
                "union": len(original.molecules | candidate.molecules),
                "original_entity": original.flavor_entity_name,
                "candidate_entity": candidate.flavor_entity_name,
                "same_entity": original.flavor_entity_id == candidate.flavor_entity_id,
                "proxy": "proxy" in (original.flavor_match, candidate.flavor_match),
            }
        eligible_flag = not reasons
        entry = {
            "ingredient_id": candidate_id,
            "name": candidate.name,
            "scores": components,
            "overall": overall_score(components, weights),
            "weight_with_data": sum(weights[k] for k in COMPONENTS if components[k] is not None),
            "flavor_detail": flavor_detail,
            "flavor_gap": None if flavor is not None else flavor_gap(original, candidate),
            "cuisine_detail": {
                "recipes_using": cuisine.counts.get(candidate_id, 0),
                "region_recipes": cuisine.region_recipes,
                "region": cuisine.region,
            },
            "line_amount": {"original": before, "modified": after},
            "recipe_gain_percent": recipe_gain(rows, goal) * 100,
            "tradeoffs": tradeoffs(rows, goal),
            "ratio": ratio,
            "notes": notes,
            "eligible": eligible_flag,
            "reasons": reasons,
        }
        (eligible if eligible_flag else rejected).append(entry)

    # Ties break on the larger health gain, then name, so results are repeatable.
    def order(item: dict):
        return (-item["overall"], -(item["scores"]["health"] or 0), item["name"])

    return sorted(eligible, key=order), sorted(rejected, key=order)


def recommend(
    lines: list[Line],
    ingredients: dict[str, Ingredient],
    graph: nx.Graph,
    goal: Goal,
    cuisine: CuisineStats,
    *,
    title: str = "",
    weights: dict[str, float] | None = None,
    ratios: dict[int, float] | None = None,
    min_flavor: float = 0.0,
    min_cuisine: float = 0.0,
    guardrails: bool = True,
) -> list[dict]:
    """Steps 1-5: find the lines that matter for the goal and rank substitutes."""
    weights = normalise_weights(weights)
    ratios = ratios or {}
    recipe_total = nutrition.total(lines, ingredients, goal.nutrient) or 0.0
    results = []
    for line in lines:
        original = ingredients.get(line.ingredient_id or "")
        if original is None or not original.substitutable:
            continue
        eligible, rejected = score_candidates(
            line, lines, ingredients, graph, goal, cuisine, weights,
            ratio=ratios.get(line.id, 1.0), min_flavor=min_flavor, min_cuisine=min_cuisine,
            guardrails=guardrails,
        )
        if not (eligible or rejected):
            continue
        amount = nutrition.contribution(original, line.grams, goal.nutrient) or 0.0
        best_gain = max((c["recipe_gain_percent"] for c in eligible), default=0.0)
        results.append({
            "line_id": line.id,
            "ingredient_id": original.id,
            "ingredient_name": original.name,
            "phrase": line.original_phrase,
            "grams": line.grams,
            "amount": amount,
            "share_percent": amount / recipe_total * 100 if recipe_total > 0 else None,
            "best_gain_percent": best_gain,
            "relevant": bool(eligible) and best_gain >= MIN_RECIPE_GAIN * 100,
            "in_title": in_title(original, title),
            "candidates": eligible,
            "rejected": rejected,
        })
    return sorted(results, key=lambda r: (not r["relevant"], -r["best_gain_percent"], r["line_id"]))


def choose_swaps(
    recommendations: list[dict],
    scope: str,
    selected_line: int | None = None,
    *,
    keep_title_ingredients: bool = True,
) -> list[Swap]:
    """Pick the top eligible candidate for the lines in scope (independently)."""
    chosen = []
    for entry in recommendations:
        if scope == "ingredient":
            if entry["line_id"] != selected_line or not entry["candidates"]:
                continue
        elif not entry["relevant"] or (keep_title_ingredients and entry["in_title"]):
            continue
        best = entry["candidates"][0]
        chosen.append(Swap(entry["line_id"], best["ingredient_id"], best["ratio"]))
    return chosen


def similarity_summary(
    lines: list[Line], ingredients: dict[str, Ingredient], swaps: list[Swap], cuisine: CuisineStats
) -> dict:
    """Flavor and cuisine scores of the swapped lines only, weighted by grams.

    Unchanged ingredients are left out: counting them as "100% similar" would
    make every modification look almost identical to the original.
    """
    by_line = {line.id: line for line in lines}
    flavor, cuisine_values = [], []
    same_record = 0
    for swap in swaps:
        line = by_line[swap.line_id]
        original, candidate = ingredients[line.ingredient_id], ingredients[swap.ingredient_id]
        weight = line.grams or 0.0
        score = network.flavor_similarity(original, candidate)
        if score is not None:
            flavor.append((score, weight))
            same_record += original.flavor_entity_id == candidate.flavor_entity_id
        score = cuisine.score(swap.ingredient_id)
        if score is not None:
            cuisine_values.append((score, weight))

    def average(pairs):
        weight = sum(w for _, w in pairs)
        return sum(s * w for s, w in pairs) / weight if weight > 0 else None

    return {
        "flavor": average(flavor),
        "cuisine": average(cuisine_values),
        "flavor_swaps_with_data": len(flavor),
        # These score 1.00 only because FlavorDB2 has one record for both foods.
        "flavor_same_record_swaps": same_record,
        "cuisine_swaps_with_data": len(cuisine_values),
        "swaps": len(swaps),
    }
