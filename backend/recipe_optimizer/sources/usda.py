"""USDA FoodData Central: SR Legacy bulk CSV download (no API key required).

SR Legacy is used because it covers common cooking ingredients broadly and ships
household-measure gram weights (cup, tbsp, clove, large...), which are needed to
turn recipe quantities into grams.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .. import config
from ..fetch import fetch

# project nutrient key -> (FoodData Central nutrient id, unit, label)
NUTRIENTS: dict[str, tuple[int, str, str]] = {
    "calories": (1008, "kcal", "Calories"),
    "protein": (1003, "g", "Protein"),
    "fat": (1004, "g", "Total fat"),
    "satFat": (1258, "g", "Saturated fat"),
    "carbs": (1005, "g", "Carbohydrates"),
    "fiber": (1079, "g", "Fiber"),
    "sugars": (2000, "g", "Sugars"),
    "sodium": (1093, "mg", "Sodium"),
    "cholesterol": (1253, "mg", "Cholesterol"),
    "potassium": (1092, "mg", "Potassium"),
    "calcium": (1087, "mg", "Calcium"),
    "iron": (1089, "mg", "Iron"),
}


@dataclass
class Food:
    fdc_id: int
    description: str
    category: str
    ndb_number: str | None = None
    nutrients: dict[str, float] = field(default_factory=dict)  # per 100 g
    portions: list[dict] = field(default_factory=list)


def download(*, offline: bool = False, refresh: bool = False) -> bytes:
    return fetch(config.USDA_SR_LEGACY_URL, "usda", suffix=".zip", offline=offline, refresh=refresh)


def _table(archive: zipfile.ZipFile, name: str, **kwargs) -> pd.DataFrame:
    matches = [n for n in archive.namelist() if n == name or n.endswith("/" + name)]
    if not matches:
        raise ValueError(f"{name} is missing from the USDA archive")
    with archive.open(matches[0]) as handle:
        return pd.read_csv(handle, **kwargs)


class SRLegacy:
    """In-memory view of the SR Legacy tables this project needs."""

    def __init__(self, archive: bytes | str | Path):
        source = io.BytesIO(archive) if isinstance(archive, bytes) else archive
        with zipfile.ZipFile(source) as z:
            foods = _table(z, "food.csv", usecols=["fdc_id", "description", "food_category_id"])
            categories = _table(z, "food_category.csv", usecols=["id", "description"])
            legacy = _table(z, "sr_legacy_food.csv", dtype=str)
            values = _table(z, "food_nutrient.csv", usecols=["fdc_id", "nutrient_id", "amount"])
            portions = _table(
                z,
                "food_portion.csv",
                usecols=["fdc_id", "seq_num", "amount", "portion_description", "modifier", "gram_weight"],
            )
        category_names = dict(zip(categories["id"], categories["description"]))
        ndb = {int(f): n for f, n in zip(legacy["fdc_id"], legacy["NDB_number"])}

        self.foods: dict[int, Food] = {}
        for row in foods.itertuples(index=False):
            fdc_id = int(row.fdc_id)
            self.foods[fdc_id] = Food(
                fdc_id=fdc_id,
                description=str(row.description),
                category=str(category_names.get(row.food_category_id, "")),
                ndb_number=ndb.get(fdc_id),
            )
        self.by_description = {f.description.casefold(): f for f in self.foods.values()}
        self._values = values[values["nutrient_id"].isin([n[0] for n in NUTRIENTS.values()])]
        self._portions = portions
        self._loaded: set[int] = set()

    def find(self, description: str) -> Food | None:
        """Exact (case-insensitive) description lookup. Deliberately not fuzzy."""
        food = self.by_description.get(description.casefold())
        return self.details(food.fdc_id) if food else None

    def search(self, *words: str, limit: int = 30) -> list[str]:
        """Descriptions containing every word. A helper for maintaining the catalog."""
        needles = [w.casefold() for w in words]
        hits = [f.description for f in self.foods.values()
                if all(n in f.description.casefold() for n in needles)]
        return sorted(hits, key=len)[:limit]

    def details(self, fdc_id: int) -> Food:
        food = self.foods[fdc_id]
        if fdc_id in self._loaded:
            return food
        by_id = {n[0]: key for key, n in NUTRIENTS.items()}
        for row in self._values[self._values["fdc_id"] == fdc_id].itertuples(index=False):
            if pd.notna(row.amount):  # absent stays absent: never default to zero
                food.nutrients[by_id[int(row.nutrient_id)]] = float(row.amount)
        rows = self._portions[self._portions["fdc_id"] == fdc_id].sort_values("seq_num")
        for row in rows.itertuples(index=False):
            label = row.modifier if pd.notna(row.modifier) else row.portion_description
            if pd.isna(label) or pd.isna(row.gram_weight) or float(row.gram_weight) <= 0:
                continue
            amount = float(row.amount) if pd.notna(row.amount) and float(row.amount) > 0 else 1.0
            food.portions.append(
                {"amount": amount, "description": str(label), "gram_weight": float(row.gram_weight)}
            )
        self._loaded.add(fdc_id)
        return food
