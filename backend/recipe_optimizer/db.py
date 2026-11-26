"""SQLite access (standard library only)."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config
from .models import Ingredient, Line
from .network import MIN_PROFILE_MOLECULES

SCHEMA = Path(__file__).with_name("schema.sql")
RESET_ORDER = (
    "substitutions", "cuisine_associations", "recipe_ingredients", "recipes", "portions",
    "nutrients", "ingredient_synonyms", "ingredients", "entity_molecules", "flavor_molecules",
    "flavor_entities", "categories", "sources",
)


class DatabaseNotReady(RuntimeError):
    pass


@contextmanager
def connect(path: Path | str | None = None, *, must_exist: bool = False):
    """Yield a connection; commit on success, roll back on error."""
    path = Path(path or config.DB_PATH)
    if must_exist and not path.exists():
        raise DatabaseNotReady(
            f"No database at {path}. Build it with: python -m recipe_optimizer build"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(connection: sqlite3.Connection, *, reset: bool = False) -> None:
    if reset:
        for table in RESET_ORDER:
            connection.execute(f"DROP TABLE IF EXISTS {table}")
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))


def load_ingredients(connection: sqlite3.Connection) -> dict[str, Ingredient]:
    nutrients: dict[str, dict[str, float]] = {}
    for row in connection.execute("SELECT ingredient_id, nutrient, amount FROM nutrients"):
        nutrients.setdefault(row["ingredient_id"], {})[row["nutrient"]] = row["amount"]
    molecules: dict[int, set[int]] = {}
    for row in connection.execute("SELECT entity_id, pubchem_id FROM entity_molecules"):
        molecules.setdefault(row["entity_id"], set()).add(row["pubchem_id"])
    query = """
        SELECT i.*, c.role_label, c.family, c.family_label, c.substitutable,
               f.name AS flavor_entity_name
        FROM ingredients i
        JOIN categories c ON c.role = i.role
        LEFT JOIN flavor_entities f ON f.entity_id = i.flavor_entity_id
    """
    return {
        row["id"]: Ingredient(
            id=row["id"], name=row["name"], role=row["role"], family=row["family"],
            role_label=row["role_label"], family_label=row["family_label"],
            also=tuple(json.loads(row["also_roles"])), substitutable=bool(row["substitutable"]),
            nutrients=nutrients.get(row["id"], {}), nutrition_source=row["nutrition_source"],
            nutrition_match=row["nutrition_match"], nutrition_note=row["nutrition_note"],
            source_food_id=row["source_food_id"], source_food_name=row["source_food_name"],
            flavor_entity_id=row["flavor_entity_id"],
            flavor_entity_name=row["flavor_entity_name"], flavor_match=row["flavor_match"],
            molecules=frozenset(molecules.get(row["flavor_entity_id"], ())),
        )
        for row in connection.execute(query)
    }


def regions(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT region, COUNT(*) AS recipes FROM recipes WHERE region IS NOT NULL "
        "GROUP BY region ORDER BY recipes DESC, region"
    )
    return [dict(row) for row in rows]


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search_recipes(
    connection: sqlite3.Connection,
    *,
    query: str = "",
    region: str = "",
    ingredient: str = "",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Title words (all must appear), cuisine and ingredient filters."""
    where, params = [], []
    for word in query.split()[:8]:
        where.append("r.title LIKE ? ESCAPE '\\'")
        params.append(_like(word))
    if region:
        where.append("r.region = ?")
        params.append(region)
    if ingredient.strip():
        where.append(
            "EXISTS (SELECT 1 FROM recipe_ingredients x WHERE x.recipe_id = r.id "
            "AND (x.original_phrase LIKE ? ESCAPE '\\' OR x.standardized_name LIKE ? ESCAPE '\\'))"
        )
        params += [_like(ingredient.strip())] * 2
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = connection.execute(f"SELECT COUNT(*) FROM recipes r {clause}", params).fetchone()[0]
    rows = connection.execute(
        f"""
        SELECT r.id, r.title, r.region, r.sub_region, r.servings, r.total_minutes,
               COUNT(l.id) AS ingredient_lines,
               SUM(l.missing_status = 'ok') AS counted_lines
        FROM recipes r LEFT JOIN recipe_ingredients l ON l.recipe_id = r.id
        {clause}
        GROUP BY r.id
        -- Best data coverage first, so the most analysable recipes are easy to find.
        ORDER BY CAST(SUM(l.missing_status = 'ok') AS REAL) / COUNT(l.id) DESC,
                 r.title COLLATE NOCASE, r.id
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    )
    return {"total": total, "limit": limit, "offset": offset, "results": [dict(r) for r in rows]}


def get_recipe(connection: sqlite3.Connection, recipe_id: int) -> dict | None:
    row = connection.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        return None
    recipe = dict(row)
    for key in ("processes", "utensils", "diet_tags"):
        recipe[key] = json.loads(recipe[key])
    recipe["servings_estimated"] = bool(recipe["servings_estimated"])
    recipe["ingredients"] = [
        {**dict(line), "grams_is_estimate": bool(line["grams_is_estimate"])}
        for line in connection.execute(
            "SELECT * FROM recipe_ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
        )
    ]
    return recipe


def recipe_lines(recipe: dict) -> list[Line]:
    return [
        Line(id=r["id"], ingredient_id=r["ingredient_id"], grams=r["grams"],
             original_phrase=r["original_phrase"], grams_is_estimate=r["grams_is_estimate"])
        for r in recipe["ingredients"]
    ]


def cuisine_counts(connection: sqlite3.Connection, region: str | None) -> tuple[int, dict[str, int]]:
    if not region:
        return 0, {}
    total = connection.execute("SELECT COUNT(*) FROM recipes WHERE region = ?", (region,)).fetchone()[0]
    rows = connection.execute(
        "SELECT ingredient_id, recipe_count FROM cuisine_associations WHERE region = ?", (region,)
    )
    return total, {r["ingredient_id"]: r["recipe_count"] for r in rows}


def source_rows(connection: sqlite3.Connection) -> list[dict]:
    return [dict(r) for r in connection.execute("SELECT * FROM sources ORDER BY id")]


def stats(connection: sqlite3.Connection) -> dict:
    def one(sql: str):
        return connection.execute(sql).fetchone()[0] or 0

    return {
        "recipes": one("SELECT COUNT(*) FROM recipes"),
        "recipes_with_instructions": one("SELECT COUNT(*) FROM recipes WHERE instructions IS NOT NULL"),
        "ingredient_lines": one("SELECT COUNT(*) FROM recipe_ingredients"),
        "matched_lines": one("SELECT COUNT(*) FROM recipe_ingredients WHERE ingredient_id IS NOT NULL"),
        "lines_with_nutrition": one("SELECT COUNT(*) FROM recipe_ingredients WHERE missing_status='ok'"),
        "ingredients": one("SELECT COUNT(*) FROM ingredients"),
        "ingredients_with_nutrition": one("SELECT COUNT(DISTINCT ingredient_id) FROM nutrients"),
        "ingredients_with_flavor": one("SELECT COUNT(*) FROM ingredients WHERE flavor_entity_id IS NOT NULL"),
        "ingredients_with_usable_flavor": one(
            "SELECT COUNT(*) FROM ingredients i WHERE (SELECT COUNT(*) FROM entity_molecules m "
            f"WHERE m.entity_id = i.flavor_entity_id) >= {int(MIN_PROFILE_MOLECULES)}"
        ),
        "flavor_molecules": one("SELECT COUNT(*) FROM flavor_molecules"),
        "substitution_edges": one("SELECT COUNT(*) FROM substitutions"),
    }
