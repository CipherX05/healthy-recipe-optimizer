"""Load the external sources into the unified SQLite database."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone

from . import config, db, network, quantities
from .matching import Catalog
from .sources import flavordb, indb, recipedb, usda

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record_source(connection, source_id: str, status: str, records: int = 0) -> None:
    info = config.SOURCES[source_id]
    connection.execute(
        """INSERT INTO sources(id, name, url, license, notes, status, records, retrieved_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET status=excluded.status, records=excluded.records,
               retrieved_at=excluded.retrieved_at""",
        (source_id, info["name"], info["url"], info["license"], info["notes"], status, records,
         _now() if status == "loaded" else None),
    )


def load_ingredients(
    connection: sqlite3.Connection,
    catalog: Catalog,
    foods: "usda.SRLegacy | None",
    flavor_entities: dict[str, dict],
    indb_foods: dict[str, dict] | None = None,
) -> None:
    """Write catalog ingredients with whatever source data is actually available."""
    for source_id in config.SOURCES:
        connection.execute(
            "INSERT OR IGNORE INTO sources(id,name,url,license,notes,status) VALUES (?,?,?,?,?,'skipped')",
            (source_id, *(config.SOURCES[source_id][k] for k in ("name", "url", "license", "notes"))),
        )
    for role, info in catalog.roles.items():
        connection.execute(
            "INSERT INTO categories VALUES (?,?,?,?,?)",
            (role, info["label"], info["family"], catalog.families[info["family"]],
             int(info["substitutable"])),
        )
    for entity in {e["entity_id"]: e for e in flavor_entities.values()}.values():
        connection.execute("INSERT INTO flavor_entities VALUES (?,?,?)",
                           (entity["entity_id"], entity["name"], entity["category"]))
        for molecule in entity["molecules"]:
            connection.execute(
                "INSERT OR IGNORE INTO flavor_molecules VALUES (?,?,?)",
                (molecule["pubchem_id"], molecule["common_name"], molecule["flavor_profile"]),
            )
            connection.execute("INSERT OR IGNORE INTO entity_molecules VALUES (?,?)",
                               (entity["entity_id"], molecule["pubchem_id"]))

    used = {"usda_sr_legacy": 0, "indb": 0}
    flavor_used = 0
    missing_foods = []
    for entry in catalog.ingredients.values():
        source = match = food_id = food_name = ndb = None
        note = ""
        nutrients: dict[str, float] = {}
        portions: list[dict] = []
        if entry.get("usda") and foods is not None:
            food = foods.find(entry["usda"])
            if food is None:
                missing_foods.append(f"{entry['id']}: {entry['usda']}")
            else:
                source, match = "usda_sr_legacy", entry.get("usda_match", "exact")
                note = entry.get("usda_note", "")
                food_id, food_name, ndb = str(food.fdc_id), food.description, food.ndb_number
                nutrients, portions = food.nutrients, food.portions
        if source is None and entry.get("indb") and indb_foods:
            dish = indb_foods.get(entry["indb"].casefold())
            if dish is None:
                log.warning("INDB has no dish named %r", entry["indb"])
            else:
                source, match = "indb", "proxy"
                note = "INDB value for one published version of this prepared dish"
                food_id, food_name = dish["food_code"], dish["name"]
                nutrients = dish["nutrients"]

        entity = flavor_entities.get(entry.get("flavordb") or "")
        if entity is not None and not entity["molecules"]:
            entity = None
        status = {(True, True): "complete", (False, True): "missing_nutrition",
                  (True, False): "missing_flavor", (False, False): "missing_both"}[
            (bool(nutrients), entity is not None)]
        connection.execute(
            "INSERT INTO ingredients VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (entry["id"], entry["name"], entry["role"], json.dumps(entry.get("also", [])),
             source, match, note, food_id, food_name, ndb,
             entity["entity_id"] if entity else None,
             entry.get("flavordb_match", "exact") if entity else None, status),
        )
        for key, amount in nutrients.items():
            connection.execute(
                "INSERT INTO nutrients VALUES (?,?,?,?,?,?)",
                (entry["id"], key, amount, usda.NUTRIENTS[key][1], source, food_id),
            )
        for portion in portions:
            connection.execute(
                "INSERT INTO portions VALUES (?,?,?,?,?)",
                (entry["id"], portion["description"], portion["amount"], portion["gram_weight"], source),
            )
        if source:
            used[source] += 1
        if entity:
            flavor_used += 1

    if missing_foods:
        # A renamed or mistyped record must never silently become "no data".
        raise ValueError("catalog names USDA records that do not exist:\n  " + "\n  ".join(missing_foods))

    for key, ingredient_id in catalog.index.items():
        connection.execute("INSERT INTO ingredient_synonyms VALUES (?,?,?)",
                           (key, ingredient_id, catalog.assumed.get(key, "")))

    _record_source(connection, "usda_sr_legacy",
                   "loaded" if foods is not None else "unavailable", used["usda_sr_legacy"])
    _record_source(connection, "flavordb2",
                   "loaded" if flavor_entities else "unavailable", flavor_used)
    if indb_foods is not None:
        _record_source(connection, "indb", "loaded" if indb_foods else "unavailable", used["indb"])


def usable_portions(portions: list[dict], entry: dict) -> list[dict]:
    """Drop volume measures when the catalog says they describe a different shape."""
    if not entry.get("no_volume"):
        return portions
    return [p for p in portions if quantities.portion_unit(p["description"]) not in quantities.VOLUME_ML]


def import_recipes(connection: sqlite3.Connection, catalog: Catalog, recipes: list[dict],
                   source_id: str = "recipedb") -> int:
    """Validate, match, convert and upsert recipes. Safe to run repeatedly."""
    portions: dict[str, list[dict]] = {}
    for row in connection.execute("SELECT * FROM portions"):
        portions.setdefault(row["ingredient_id"], []).append(
            {"amount": row["amount"], "description": row["description"], "gram_weight": row["gram_weight"]}
        )
    with_nutrition = {r[0] for r in connection.execute("SELECT DISTINCT ingredient_id FROM nutrients")}
    _record_source(connection, source_id, "loaded", 0)

    imported = 0
    for recipe in recipes:
        if not recipe.get("title") or not recipe.get("source_id") or not recipe.get("ingredients"):
            log.warning("skipping an incomplete recipe record: %r", recipe.get("title"))
            continue
        connection.execute("DELETE FROM recipes WHERE source=? AND source_id=?",
                           (source_id, recipe["source_id"]))
        cursor = connection.execute(
            """INSERT INTO recipes(source, source_id, title, region, sub_region, continent,
                   servings, servings_raw, servings_estimated, prep_minutes, cook_minutes,
                   total_minutes, instructions, processes, utensils, diet_tags, source_site,
                   source_url, detail_url, imported_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id, recipe["source_id"], recipe["title"], recipe.get("region"),
             recipe.get("sub_region"), recipe.get("continent"), recipe.get("servings"),
             recipe.get("servings_raw"), int(bool(recipe.get("servings_estimated"))),
             recipe.get("prep_minutes"), recipe.get("cook_minutes"), recipe.get("total_minutes"),
             recipe.get("instructions"), json.dumps(recipe.get("processes", [])),
             json.dumps(recipe.get("utensils", [])), json.dumps(recipe.get("diet_tags", [])),
             recipe.get("source_site"), recipe.get("source_url"), recipe.get("detail_url"), _now()),
        )
        for position, line in enumerate(recipe["ingredients"]):
            match = catalog.match(line["original_phrase"], line.get("source_name", ""),
                                  line.get("unit_raw", ""))
            ingredient_id = match.ingredient_id
            amount = quantities.Grams(None, "unresolved", "ingredient not matched")
            if ingredient_id:
                amount = quantities.to_grams(
                    line.get("quantity_raw", ""), line.get("unit_raw", ""), line["original_phrase"],
                    usable_portions(portions.get(ingredient_id, []), catalog.ingredients[ingredient_id]),
                    size=line.get("size", ""),
                    count_hint=catalog.ingredients[ingredient_id].get("count_hint", ""),
                    cup_form=catalog.ingredients[ingredient_id].get("cup_form", ""),
                )
            if not ingredient_id:
                missing = "unmatched"
            elif ingredient_id not in with_nutrition:
                missing = "no_nutrition_data"
            else:
                missing = "ok" if amount.grams is not None else "unknown_quantity"
            connection.execute(
                """INSERT INTO recipe_ingredients(recipe_id, position, original_phrase, source_name,
                       standardized_name, ingredient_id, quantity_raw, unit_raw, state, size, grams,
                       grams_method, grams_note, grams_is_estimate, match_method, match_confidence,
                       match_note, source_ndb_id, missing_status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cursor.lastrowid, position, line["original_phrase"], line.get("source_name", ""),
                 match.standardized_name, ingredient_id, line.get("quantity_raw", ""),
                 line.get("unit_raw", ""), line.get("state", ""), line.get("size", ""),
                 amount.grams, amount.method, amount.note, int(amount.is_estimate),
                 match.method, match.confidence, match.note, line.get("source_ndb_id"), missing),
            )
        imported += 1

    total = connection.execute("SELECT COUNT(*) FROM recipes WHERE source=?", (source_id,)).fetchone()[0]
    _record_source(connection, source_id, "loaded" if total else "unavailable", total)
    return imported


def rebuild_derived(connection: sqlite3.Connection) -> None:
    """Recompute cuisine associations and substitution edges from the stored data."""
    connection.execute("DELETE FROM cuisine_associations")
    connection.execute(
        """
        INSERT INTO cuisine_associations(ingredient_id, region, recipe_count, region_recipes)
        SELECT l.ingredient_id, r.region, COUNT(DISTINCT r.id),
               (SELECT COUNT(*) FROM recipes t WHERE t.region = r.region)
        FROM recipe_ingredients l JOIN recipes r ON r.id = l.recipe_id
        WHERE l.ingredient_id IS NOT NULL AND r.region IS NOT NULL
        GROUP BY l.ingredient_id, r.region
        """
    )
    connection.execute("DELETE FROM substitutions")
    graph = network.build_graph(db.load_ingredients(connection))
    connection.executemany(
        "INSERT INTO substitutions VALUES (?,?,?,?,?,?,?)",
        [
            (*sorted((a, b)), d["role_score"], d["flavor_jaccard"], d["shared_molecules"],
             int(d["same_flavor_entity"]), d["weight"])
            for a, b, d in graph.edges(data=True)
        ],
    )


def build(
    *,
    regions: list[str] | None = None,
    pages: int = 5,
    titles: list[str] | None = None,
    with_indb: bool = False,
    with_flavor: bool = True,
    offline: bool = False,
    refresh: bool = False,
    db_path=None,
) -> dict:
    """Rebuild the whole database. Downloads are reused from the cache."""
    catalog = Catalog.load()

    log.info("1/4 USDA SR Legacy")
    foods = usda.SRLegacy(usda.download(offline=offline, refresh=refresh))

    flavor_entities: dict[str, dict] = {}
    if with_flavor:
        log.info("2/4 FlavorDB2")
        names = [e["flavordb"] for e in catalog.ingredients.values() if e.get("flavordb")]
        flavor_entities = flavordb.load_named(names, offline=offline, refresh=refresh)
    indb_foods = None
    if with_indb:
        log.info("INDB (optional)")
        try:
            indb_foods = indb.load(indb.download(offline=offline, refresh=refresh))
        except Exception as error:  # optional source: never block the build
            log.error("INDB could not be loaded: %s", error)
            indb_foods = {}

    log.info("3/4 RecipeDB")
    records = recipedb.collect(
        regions if regions is not None else recipedb.DEFAULT_REGIONS, pages,
        titles=titles or [], offline=offline, refresh=refresh,
    )

    log.info("4/4 building the database")
    target = db_path or config.DB_PATH
    # Build beside the live file and swap at the end, so a failure keeps the old one.
    temporary = target.with_name(target.name + ".building")
    temporary.unlink(missing_ok=True)
    try:
        with db.connect(temporary) as connection:
            db.init_db(connection)
            load_ingredients(connection, catalog, foods, flavor_entities, indb_foods)
            if records:
                import_recipes(connection, catalog, records)
            else:
                log.error("no RecipeDB recipes were obtained; the database will have none")
                _record_source(connection, "recipedb", "unavailable")
            rebuild_derived(connection)
            summary = db.stats(connection)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return summary
