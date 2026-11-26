"""Indian Nutrient Databank (optional).

The downloadable workbook holds 1,014 *cooked recipes* (per 100 g), not raw
ingredients. It is therefore used only for catalog entries that are themselves
prepared Indian foods and name an exact INDB dish in their ``indb`` field.
USDA values take priority whenever both exist. The publisher states no licence.
"""
from __future__ import annotations

import io
import math

from .. import config
from ..fetch import fetch

# INDB column -> (project nutrient key, multiplier into the project's unit)
COLUMNS = {
    "energy_kcal": ("calories", 1.0),
    "protein_g": ("protein", 1.0),
    "fat_g": ("fat", 1.0),
    "sfa_mg": ("satFat", 0.001),  # stored in mg; the project uses g
    "carb_g": ("carbs", 1.0),
    "fibre_g": ("fiber", 1.0),
    "sodium_mg": ("sodium", 1.0),
    "cholesterol_mg": ("cholesterol", 1.0),
    "potassium_mg": ("potassium", 1.0),
    "calcium_mg": ("calcium", 1.0),
    "iron_mg": ("iron", 1.0),
}


def download(*, offline: bool = False, refresh: bool = False) -> bytes:
    return fetch(config.INDB_URL, "indb", suffix=".xlsx", offline=offline, refresh=refresh)


def parse_rows(header: list[str], rows) -> dict[str, dict]:
    position = {name: index for index, name in enumerate(header)}
    required = {"food_code", "food_name", *COLUMNS}
    if not required <= position.keys():
        raise ValueError(f"INDB columns missing: {sorted(required - position.keys())}")
    foods = {}
    for row in rows:
        name = row[position["food_name"]]
        if not name:
            continue
        nutrients = {}
        for column, (key, factor) in COLUMNS.items():
            value = row[position[column]]
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                nutrients[key] = float(value) * factor
        foods[str(name).strip().casefold()] = {
            "food_code": str(row[position["food_code"]]),
            "name": str(name).strip(),
            "nutrients": nutrients,
        }
    return foods


def load(workbook: bytes) -> dict[str, dict]:
    import openpyxl  # only needed when INDB is requested

    sheet = openpyxl.load_workbook(io.BytesIO(workbook), read_only=True, data_only=True).worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = [str(c) for c in next(rows)]
    return parse_rows(header, rows)
