"""Recipe-level nutrition and original-versus-modified comparison.

Everything here is an estimate: sum over lines of (per-100 g value x grams / 100),
using raw USDA records. Cooking losses, absorbed frying oil and discarded
marinades are not modelled.

Missing data is never treated as zero. For each nutrient, a line is counted only
if its grams are known and the value exists for the original ingredient *and*,
when swapped, for the replacement. Both totals therefore cover the same lines.
"""
from __future__ import annotations

from .models import Ingredient, Line, Swap
from .sources.usda import NUTRIENTS


def contribution(ingredient: Ingredient | None, grams: float | None, nutrient: str) -> float | None:
    if ingredient is None or grams is None:
        return None
    per_100g = ingredient.nutrients.get(nutrient)
    return None if per_100g is None else per_100g * grams / 100.0


def line_status(line: Line, ingredients: dict[str, Ingredient]) -> str:
    if line.ingredient_id is None or line.ingredient_id not in ingredients:
        return "unmatched"
    if not ingredients[line.ingredient_id].nutrients:
        return "no_nutrition_data"
    return "ok" if line.grams is not None else "unknown_quantity"


def coverage(lines: list[Line], ingredients: dict[str, Ingredient]) -> dict:
    statuses = [line_status(line, ingredients) for line in lines]
    counted = statuses.count("ok")
    return {
        "total_lines": len(lines),
        "counted_lines": counted,
        "fraction": counted / len(lines) if lines else 0.0,
        "excluded": [
            {"line_id": line.id, "phrase": line.original_phrase, "reason": status}
            for line, status in zip(lines, statuses)
            if status != "ok"
        ],
    }


def compare(
    lines: list[Line],
    ingredients: dict[str, Ingredient],
    swaps: list[Swap] | None = None,
    servings: float | None = None,
) -> list[dict]:
    """One row per nutrient with original, modified, absolute and percent change."""
    by_line = {swap.line_id: swap for swap in swaps or []}
    rows = []
    for key, (_, unit, label) in NUTRIENTS.items():
        original = modified = 0.0
        counted = 0
        missing_lines = []
        for line in lines:
            if line_status(line, ingredients) != "ok":
                continue
            before = contribution(ingredients[line.ingredient_id], line.grams, key)
            swap = by_line.get(line.id)
            after = before
            if swap is not None:
                after = contribution(ingredients.get(swap.ingredient_id), line.grams * swap.ratio, key)
            if before is None or after is None:
                missing_lines.append(line.id)
                continue
            original += before
            modified += after
            counted += 1
        if counted == 0:
            rows.append({"key": key, "label": label, "unit": unit, "original": None,
                         "modified": None, "change": None, "percent_change": None,
                         "per_serving": None, "counted_lines": 0,
                         "lines_missing_value": missing_lines})
            continue
        change = modified - original
        per_serving = None
        if servings and servings > 0:
            per_serving = {"original": original / servings, "modified": modified / servings,
                           "change": change / servings}
        rows.append({
            "key": key,
            "label": label,
            "unit": unit,
            "original": original,
            "modified": modified,
            "change": change,
            # A percentage of a zero baseline is undefined, so report none.
            "percent_change": change / original * 100.0 if original > 1e-9 else None,
            "per_serving": per_serving,
            "counted_lines": counted,
            "lines_missing_value": missing_lines,
        })
    return rows


def total(lines: list[Line], ingredients: dict[str, Ingredient], nutrient: str) -> float | None:
    values = [
        contribution(ingredients.get(line.ingredient_id), line.grams, nutrient)
        for line in lines
        if line.ingredient_id
    ]
    known = [v for v in values if v is not None]
    return sum(known) if known else None
