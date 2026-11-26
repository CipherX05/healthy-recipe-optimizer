"""RecipeDB importer.

RecipeDB documents no API and no recipe bulk download. Each search-results page
embeds one JSON record per recipe (passed to ``handleInfoClick``), so this module
reads those records. 20 recipes arrive per request.

Only identity data is trusted from these records. RecipeDB's per-ingredient
nutrition and USDA codes are *not* used for calculations: some codes are wrong
(plain "oil" is linked to NDB 1003, "Butter oil, anhydrous"). The code is kept
for provenance only.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Iterable

from .. import config
from ..fetch import FetchError, fetch

log = logging.getLogger(__name__)

PAGE_SIZE = 20
_MARKER = re.compile(r"handleInfoClick\((?=\{)")

DEFAULT_REGIONS = [
    "Indian Subcontinent",
    "Italian",
    "US",
    "Chinese and Mongolian",
    "Mexican",
    "Middle Eastern",
    "Greek",
    "French",
    "Thai",
]


def parse_search_page(page_html: str) -> list[dict]:
    """Extract the embedded recipe records from one search-results page."""
    decoder = json.JSONDecoder()
    records, seen = [], set()
    for match in _MARKER.finditer(page_html):
        try:
            raw, _ = decoder.raw_decode(page_html, match.end())
        except ValueError:
            log.warning("skipping an unreadable RecipeDB record at offset %d", match.end())
            continue
        recipe = normalise_record(raw)
        if recipe and recipe["source_id"] not in seen:
            seen.add(recipe["source_id"])
            records.append(recipe)
    return records


def _text(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip() if value is not None else ""


def _optional(value) -> str | None:
    text = _text(value)
    return text if text and text.lower() not in {"none", "null", "nan", "-"} else None


def _minutes(value) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def parse_servings(raw) -> tuple[float | None, bool]:
    """Return (servings, is_estimate). A range such as "4-6" becomes its midpoint."""
    text = _text(raw)
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return None, False
    if len(numbers) >= 2 and re.search(r"\d\s*(?:-|to|–)\s*\d", text):
        value, estimated = (numbers[0] + numbers[1]) / 2, True
    else:
        value, estimated = numbers[0], False
    return (value, estimated) if 0 < value <= 200 else (None, False)


def _split_list(raw) -> list[str]:
    return [part.strip() for part in _text(raw).split("||") if part.strip()]


def normalise_record(raw: dict) -> dict | None:
    """Convert a raw RecipeDB record to this project's shape; None if unusable."""
    source_id, title = _optional(raw.get("Recipe_id")), _optional(raw.get("Recipe_title"))
    ingredients = []
    for entry in raw.get("Ingredients") or []:
        phrase = _optional(entry.get("ingredient_Phrase"))
        name = _optional(entry.get("ingredient_name"))
        if not (phrase or name):
            continue
        ingredients.append(
            {
                "original_phrase": phrase or name,
                "source_name": name or "",
                "quantity_raw": _text(entry.get("quantity")),
                "unit_raw": _text(entry.get("unit")),
                "state": _text(entry.get("state")),
                "size": _text(entry.get("size")),
                "temperature": _text(entry.get("temperature")),
                "dried_fresh": _text(entry.get("D_F")),
                "source_ndb_id": _optional(entry.get("ndb_id")),
            }
        )
    if not (source_id and title and ingredients):
        return None

    servings, estimated = parse_servings(raw.get("Servings"))
    instructions = None
    for key in ("instructions", "Instructions", "Recipe_steps"):
        text = _optional(raw.get(key))
        if text and "not available" not in text.lower():
            instructions = text
            break

    url = _optional(raw.get("url"))
    if url and not re.match(r"^https?://", url, re.I):
        url = None
    diets = [
        label
        for key, label in (
            ("vegan", "Vegan"),
            ("lacto_vegetarian", "Lacto-vegetarian"),
            ("ovo_vegetarian", "Ovo-vegetarian"),
            ("ovo_lacto_vegetarian", "Ovo-lacto-vegetarian"),
            ("pescetarian", "Pescetarian"),
        )
        if _text(raw.get(key)) in {"1", "1.0", "1.0000"}
    ]
    return {
        "source": "recipedb",
        "source_id": source_id,
        "title": title,
        "region": _optional(raw.get("Region")),
        "sub_region": _optional(raw.get("Sub_region")),
        "continent": _optional(raw.get("Continent")),
        "servings_raw": _optional(raw.get("Servings")),
        "servings": servings,
        "servings_estimated": estimated,
        "prep_minutes": _minutes(raw.get("prep_time")),
        "cook_minutes": _minutes(raw.get("cook_time")),
        "total_minutes": _minutes(raw.get("total_time")),
        "instructions": instructions,
        "processes": _split_list(raw.get("Processes")),
        "utensils": _split_list(raw.get("Utensils")),
        "diet_tags": diets,
        "source_site": _optional(raw.get("Source")),
        "source_url": url,
        "detail_url": f"{config.RECIPEDB_BASE}/search_recipeInfo/{source_id}",
        "ingredients": ingredients,
    }


def _search_form(*, region: str = "", title: str = "", page: int = 1) -> dict:
    form = {
        "autocomplete_continent": "",
        "autocomplete_region": region,
        "autocomplete_cuisine": "",
        "autocomplete_recipe": title,
        "autocomplete_ingredient": "",
        "autocomplete_noningredient": "",
        "process": "",
        "utensil": "",
    }
    form["page"] = "" if page <= 1 else str(page)
    return form


def search(*, region: str = "", title: str = "", page: int = 1, offline: bool = False,
           refresh: bool = False) -> list[dict]:
    body = fetch(
        f"{config.RECIPEDB_BASE}/search_recipe",
        "recipedb",
        form=_search_form(region=region, title=title, page=page),
        suffix=".html",
        offline=offline,
        refresh=refresh,
    )
    return parse_search_page(body.decode("utf-8", errors="replace"))


def collect(regions: Iterable[str], pages: int, *, titles: Iterable[str] = (),
            offline: bool = False, refresh: bool = False) -> list[dict]:
    """Collect recipes for each region (``pages`` pages each) and title query."""
    found: dict[str, dict] = {}
    queries = [{"region": r, "page": p} for r in regions for p in range(1, pages + 1)]
    queries += [{"title": t, "page": 1} for t in titles]
    exhausted: set[str] = set()
    for query in queries:
        label = query.get("region") or query.get("title")
        if label in exhausted:
            continue
        try:
            records = search(**query, offline=offline, refresh=refresh)
        except FetchError as error:
            log.error("RecipeDB query %s failed: %s", query, error)
            continue
        log.info("RecipeDB %s: %d recipes", query, len(records))
        if not records:
            exhausted.add(label)
        for record in records:
            found[record["source_id"]] = record
    return list(found.values())
