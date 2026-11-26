"""The recommendation workflow, shared by the web API and the command line."""
from __future__ import annotations

import threading
from collections import Counter
from pathlib import Path

from . import config, db, network, nutrition, scoring
from .models import Ingredient, Swap
from .sources.usda import NUTRIENTS

CANDIDATES_RETURNED = 8
REJECTED_RETURNED = 6


class NotFound(LookupError):
    pass


class _Cache:
    """Ingredients and the network, reloaded only when the database file changes."""

    def __init__(self):
        self.lock = threading.Lock()
        self.key = None
        self.value = None

    def get(self, path: Path):
        with self.lock:
            stat = path.stat()
            key = (str(path), stat.st_mtime_ns, stat.st_size)
            if key != self.key:
                with db.connect(path, must_exist=True) as connection:
                    ingredients = db.load_ingredients(connection)
                self.value = (ingredients, network.build_graph(ingredients))
                self.key = key
            return self.value


_cache = _Cache()


class Service:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path or config.DB_PATH)

    def _knowledge(self):
        if not self.db_path.exists():
            raise db.DatabaseNotReady(
                "The recipe database has not been built yet. Run: python -m recipe_optimizer build"
            )
        return _cache.get(self.db_path)

    def health(self) -> dict:
        self._knowledge()
        with db.connect(self.db_path, must_exist=True) as connection:
            return {
                "status": "ok",
                "stats": db.stats(connection),
                "sources": db.source_rows(connection),
                "goals": [vars(g) for g in scoring.GOALS.values()],
                "default_weights": scoring.DEFAULT_WEIGHTS,
                "presets": scoring.PRESETS,
                "thresholds": {
                    "min_line_improvement": scoring.MIN_LINE_IMPROVEMENT,
                    "min_recipe_gain": scoring.MIN_RECIPE_GAIN,
                    "min_region_recipes": scoring.MIN_REGION_RECIPES,
                    "min_flavor_molecules": network.MIN_PROFILE_MOLECULES,
                    "tradeoff": scoring.TRADEOFF_THRESHOLD,
                    "min_gain_per_100g": scoring.MIN_GAIN_PER_100G,
                    "guardrails": scoring.GUARDRAILS,
                },
            }

    def regions(self) -> list[dict]:
        with db.connect(self.db_path, must_exist=True) as connection:
            return db.regions(connection)

    def search(self, **filters) -> dict:
        with db.connect(self.db_path, must_exist=True) as connection:
            return db.search_recipes(connection, **filters)

    def _load(self, recipe_id: int):
        ingredients, graph = self._knowledge()
        with db.connect(self.db_path, must_exist=True) as connection:
            recipe = db.get_recipe(connection, recipe_id)
            if recipe is None:
                raise NotFound(f"No recipe with id {recipe_id}")
            total, counts = db.cuisine_counts(connection, recipe["region"])
        cuisine = scoring.CuisineStats(recipe["region"], total, counts)
        return recipe, db.recipe_lines(recipe), ingredients, graph, cuisine

    def recipe(self, recipe_id: int) -> dict:
        recipe, lines, ingredients, _, cuisine = self._load(recipe_id)
        for row in recipe["ingredients"]:
            item = ingredients.get(row["ingredient_id"] or "")
            row["ingredient"] = None if item is None else describe(item)
            row["cuisine_score"] = cuisine.score(item.id) if item else None
        recipe["nutrition"] = nutrition.compare(lines, ingredients, servings=recipe["servings"])
        recipe["coverage"] = nutrition.coverage(lines, ingredients)
        return recipe

    def evaluate(
        self,
        recipe_id: int,
        goal_id: str,
        *,
        scope: str = "recipe",
        line_id: int | None = None,
        weights: dict[str, float] | None = None,
        selections: dict[int, str | None] | None = None,
        ratios: dict[int, float] | None = None,
        min_flavor: float = 0.0,
        min_cuisine: float = 0.0,
        keep_title_ingredients: bool = True,
        guardrails: bool = True,
    ) -> dict:
        """Rank substitutes, apply the chosen ones and compare the two recipes."""
        if goal_id not in scoring.GOALS:
            raise ValueError(f"unknown goal {goal_id!r}")
        if scope not in {"ingredient", "recipe"}:
            raise ValueError("scope must be 'ingredient' or 'recipe'")
        goal = scoring.GOALS[goal_id]
        recipe, lines, ingredients, graph, cuisine = self._load(recipe_id)
        used_weights = scoring.normalise_weights(weights)
        recommendations = scoring.recommend(
            lines, ingredients, graph, goal, cuisine, title=recipe["title"],
            weights=used_weights, min_flavor=min_flavor, min_cuisine=min_cuisine,
            guardrails=guardrails,
        )
        by_line = {r["line_id"]: r for r in recommendations}
        if scope == "ingredient" and line_id not in by_line:
            line_id = next((r["line_id"] for r in recommendations if r["candidates"]), None)

        chosen = {
            s.line_id: (s, "recommended")
            for s in scoring.choose_swaps(recommendations, scope, line_id,
                                          keep_title_ingredients=keep_title_ingredients)
        }
        for target, candidate_id in (selections or {}).items():
            if scope == "ingredient" and target != line_id:
                continue
            if candidate_id is None:
                chosen.pop(target, None)
                continue
            entry = by_line.get(target)
            known = {} if entry is None else {
                c["ingredient_id"]: c for c in entry["candidates"] + entry["rejected"]
            }
            if candidate_id not in known:
                raise ValueError(f"{candidate_id!r} is not a role-compatible substitute for line {target}")
            chosen[target] = (Swap(target, candidate_id), "your choice")

        swaps = []
        for target, (swap, origin) in list(chosen.items()):
            ratio = float((ratios or {}).get(target, 1.0))
            if not 0.1 <= ratio <= 5:
                raise ValueError("quantity ratio must be between 0.1 and 5")
            swaps.append(Swap(target, swap.ingredient_id, ratio))
            chosen[target] = (swaps[-1], origin)

        rows = nutrition.compare(lines, ingredients, swaps, servings=recipe["servings"])
        line_by_id = {line.id: line for line in lines}
        applied = []
        for swap in sorted(swaps, key=lambda s: s.line_id):
            line, entry = line_by_id[swap.line_id], by_line[swap.line_id]
            detail = next(c for c in entry["candidates"] + entry["rejected"]
                          if c["ingredient_id"] == swap.ingredient_id)
            target = ingredients[swap.ingredient_id]
            before = ingredients[line.ingredient_id]
            applied.append({
                "line_id": swap.line_id,
                "from_id": before.id, "from_name": before.name,
                "to_id": target.id, "to_name": target.name,
                "grams": line.grams, "new_grams": line.grams * swap.ratio, "ratio": swap.ratio,
                "ratio_basis": ("assumed 1:1 by weight; no sourced substitution ratio"
                                if abs(swap.ratio - 1) < 1e-9
                                else "ratio chosen by you; not a sourced substitution ratio"),
                "chosen_by": chosen[swap.line_id][1],
                "eligible": detail["eligible"],
                "reasons": detail["reasons"],
                "notes": detail["notes"],
                "overall": detail["overall"],
                "scores": detail["scores"],
            })

        goal_row = next(r for r in rows if r["key"] == goal.nutrient)
        gain = scoring.recipe_gain(rows, goal)
        trimmed = []
        selected_ids = {(s.line_id, s.ingredient_id) for s in swaps}
        for entry in recommendations:
            shown = entry["candidates"][:CANDIDATES_RETURNED]
            shown_ids = {c["ingredient_id"] for c in shown}
            # Always include a candidate the user picked, even if ranked low.
            shown += [c for c in entry["candidates"] + entry["rejected"]
                      if (entry["line_id"], c["ingredient_id"]) in selected_ids
                      and c["ingredient_id"] not in shown_ids]
            rejected = entry["rejected"]
            trimmed.append({
                **entry,
                "candidates": shown,
                "eligible_count": len(entry["candidates"]),
                "rejected": rejected[:REJECTED_RETURNED],
                "rejected_count": len(rejected),
                "rejection_reasons": dict(Counter(r for c in rejected for r in c["reasons"])),
            })

        return {
            "recipe_id": recipe_id,
            "goal": vars(goal),
            "scope": scope,
            "line_id": line_id,
            "weights": used_weights,
            "recommendations": trimmed,
            "applied": applied,
            "comparison": rows,
            "goal_result": {
                "improved": bool(swaps) and gain > 1e-9,
                "gain_percent": gain * 100,
                "label": NUTRIENTS[goal.nutrient][2],
                "unit": NUTRIENTS[goal.nutrient][1],
                "original": goal_row["original"],
                "modified": goal_row["modified"],
            },
            "tradeoffs": scoring.tradeoffs(rows, goal),
            "similarity": scoring.similarity_summary(lines, ingredients, swaps, cuisine),
            "coverage": nutrition.coverage(lines, ingredients),
            "servings": recipe["servings"],
            "servings_estimated": recipe["servings_estimated"],
        }

    def ingredient_network(self, ingredient_id: str, *, limit: int = 12, region: str = "") -> dict:
        ingredients, graph = self._knowledge()
        if ingredient_id not in ingredients:
            raise NotFound(f"No ingredient {ingredient_id!r}")
        data = network.ego(graph, ingredient_id, limit)
        if region:
            with db.connect(self.db_path, must_exist=True) as connection:
                stats = scoring.CuisineStats(region, *db.cuisine_counts(connection, region))
            for edge in data["edges"]:
                edge["cuisine_score"] = stats.score(edge["target"])
        data["center_name"] = ingredients[ingredient_id].name
        return data


def describe(item: Ingredient) -> dict:
    """Provenance and data-availability facts about one ingredient."""
    return {
        "id": item.id,
        "name": item.name,
        "role": item.role_label,
        "family": item.family_label,
        "substitutable": item.substitutable,
        "nutrition_source": item.nutrition_source,
        "nutrition_match": item.nutrition_match,
        "nutrition_note": item.nutrition_note,
        "source_food_id": item.source_food_id,
        "source_food_name": item.source_food_name,
        "per_100g": item.nutrients,
        "flavor_entity": item.flavor_entity_name,
        "flavor_match": item.flavor_match,
        "flavor_molecules": len(item.molecules),
        "flavor_usable": len(item.molecules) >= network.MIN_PROFILE_MOLECULES,
    }
