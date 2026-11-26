"""Paths, source metadata and environment settings.

No source used by this project needs an API key or database password. Everything
configurable comes from environment variables (see ``.env.example``).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
CATALOG_PATH = BACKEND_DIR / "catalog" / "ingredients.json"


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader so no extra dependency is needed. Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


DATA_DIR = Path(_env("RECIPE_DATA_DIR", str(REPO_ROOT / "data")))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(_env("RECIPE_DB_PATH", str(DATA_DIR / "recipes.db")))

# Generic on purpose: do not put a personal name or e-mail address here.
USER_AGENT = _env("RECIPE_USER_AGENT", "recipe-substitution-coursework-importer/1.0")
REQUEST_DELAY_SECONDS = max(1.0, float(_env("RECIPE_REQUEST_DELAY", "2.0")))
REQUEST_TIMEOUT_SECONDS = float(_env("RECIPE_REQUEST_TIMEOUT", "180"))
CORS_ORIGINS = [
    origin.strip()
    for origin in _env(
        "RECIPE_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:4173,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:4173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

RECIPEDB_BASE = "https://cosylab.iiitd.edu.in/recipedb"
FLAVORDB_BASE = "https://cosylab.iiitd.edu.in/flavordb2"
USDA_SR_LEGACY_URL = (
    "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"
)
INDB_URL = "https://www.anuvaad.org.in/wp-content/uploads/2020/07/Anuvaad_INDB_2024.11.xlsx"

CC_BY_NC_SA = "CC BY-NC-SA 3.0"

SOURCES = {
    "recipedb": {
        "name": "RecipeDB (CoSyLab, IIIT-Delhi)",
        "url": "https://cosylab.iiitd.edu.in/recipedb/",
        "license": CC_BY_NC_SA,
        "notes": "Recipes, ingredient lines, servings, region and cooking processes.",
    },
    "usda_sr_legacy": {
        "name": "USDA FoodData Central, SR Legacy (April 2018)",
        "url": "https://fdc.nal.usda.gov/download-datasets/",
        "license": "Public domain (CC0 1.0)",
        "notes": "Nutrients per 100 g and household-measure gram weights.",
    },
    "flavordb2": {
        "name": "FlavorDB2 (CoSyLab, IIIT-Delhi)",
        "url": "https://cosylab.iiitd.edu.in/flavordb2/",
        "license": CC_BY_NC_SA,
        "notes": "Flavor molecules associated with ingredients.",
    },
    "indb": {
        "name": "Indian Nutrient Databank (Anuvaad), 2024.11",
        "url": "https://www.anuvaad.org.in/indian-nutrient-databank/",
        "license": "No licence stated by the publisher (checked 2026-11-25)",
        "notes": "Optional. Composite Indian preparations only.",
    },
}


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
