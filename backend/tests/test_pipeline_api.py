"""Source parsers, database import and API, with no network and made-up data."""
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from recipe_optimizer import db, pipeline
from recipe_optimizer.api import create_app
from recipe_optimizer.matching import Catalog
from recipe_optimizer.sources import flavordb, indb, recipedb, usda

CATALOG = Catalog({
    "families": {"fat": "Fats", "other": "Other"},
    "roles": {"solid_fat": {"family": "fat", "label": "Solid fat", "substitutable": True},
              "vegetable": {"family": "other", "label": "Vegetable", "substitutable": False}},
    "ingredients": [
        {"id": "butter", "name": "Butter", "role": "solid_fat", "usda": "TEST butter", "flavordb": "Butter"},
        {"id": "spread", "name": "Test spread", "role": "solid_fat", "usda": "TEST spread", "flavordb": "Margarine"},
        {"id": "onion", "name": "Onion", "role": "vegetable", "usda": "TEST onion", "flavordb": None},
        {"id": "ghee", "name": "Ghee", "role": "solid_fat", "usda": None, "flavordb": None},
    ],
})


class FakeUSDA:
    values = {"TEST butter": {"satFat": 40.0, "calories": 700.0, "protein": 1.0},
              "TEST spread": {"satFat": 10.0, "calories": 500.0, "protein": 1.0},
              "TEST onion": {"satFat": 0.0, "calories": 40.0, "protein": 1.0}}

    def find(self, description):
        if description not in self.values:
            return None
        food = usda.Food(len(description), description, "test", "1", dict(self.values[description]))
        food.portions = [{"amount": 1, "description": "tbsp", "gram_weight": 14.0},
                         {"amount": 1, "description": "medium", "gram_weight": 110.0}]
        return food


FLAVORS = {name: {"entity_id": number, "name": name, "category": "test",
                  "molecules": [{"pubchem_id": m * 100 + k, "common_name": "", "flavor_profile": ""}
                        for m in ids for k in range(10)]}
           for number, (name, ids) in enumerate({"Butter": [1, 2, 3], "Margarine": [2, 3, 4]}.items(), 1)}


def raw_record(recipe_id="7", title="Test Toast", **extra):
    return {"Recipe_id": recipe_id, "Recipe_title": title, "Region": "Italian", "Sub_region": "Italian",
            "Servings": "2", "Source": "Test", "url": "http://example.org/x", "Processes": "heat||serve",
            "Ingredients": [
                {"ingredient_Phrase": "2 tablespoons butter", "ingredient_name": "butter",
                 "quantity": "2", "unit": "tablespoons", "ndb_id": "1"},
                {"ingredient_Phrase": "1 onion, chopped", "ingredient_name": "onion",
                 "quantity": "1", "unit": ""},
                {"ingredient_Phrase": "1 cup moon dust", "ingredient_name": "dust",
                 "quantity": "1", "unit": "cup"}],
            **extra}


def search_page(*records):
    buttons = "".join(f"<button onclick='handleInfoClick({json.dumps(r)})'>more</button>" for r in records)
    return f"<html><body>{buttons}<script>function handleInfoClick(data){{}}</script></body></html>"


class ParserTests(unittest.TestCase):
    def test_recipedb_records_are_validated_and_normalised(self):
        page = search_page(raw_record(), raw_record("8", "No ingredients") | {"Ingredients": []},
                           raw_record("9", "Range", Servings="4-6", url="javascript:alert(1)"))
        records = recipedb.parse_search_page(page + "handleInfoClick({broken")
        self.assertEqual([r["source_id"] for r in records], ["7", "9"])
        self.assertIsNone(records[0]["instructions"])
        self.assertEqual(records[0]["processes"], ["heat", "serve"])
        self.assertEqual((records[1]["servings"], records[1]["servings_estimated"]), (5.0, True))
        self.assertIsNone(records[1]["source_url"])  # only http(s) links are kept

    def test_instructions_are_kept_when_the_source_has_them(self):
        record = recipedb.normalise_record(raw_record(instructions="Toast the bread."))
        self.assertEqual(record["instructions"], "Toast the bread.")
        none = recipedb.normalise_record(raw_record(instructions="Recipe Steps are not available."))
        self.assertIsNone(none["instructions"])

    def test_flavordb_double_encoded_json(self):
        listing = json.dumps(json.dumps([{"entity_id": 60, "entity_alias_readable": "Butter"}]))
        self.assertEqual(flavordb.parse_index([listing.encode()]), {"butter": 60})
        entity = flavordb.parse_entity(json.dumps({
            "entity_id": 60, "entity_alias_readable": "Butter", "category_readable": "Dairy",
            "molecules": [{"pubchem_id": "5", "flavor_profile": "sweet@None"},
                          {"pubchem_id": "5"}, {"pubchem_id": "n/a"}]}).encode())
        self.assertEqual([m["pubchem_id"] for m in entity["molecules"]], [5])

    def test_indb_saturated_fat_is_converted_from_milligrams(self):
        header = ["food_code", "food_name", *indb.COLUMNS]
        row = ["X1", "Chutney"] + [None] * len(indb.COLUMNS)
        row[header.index("sfa_mg")] = 2500.0
        food = indb.parse_rows(header, [row])["chutney"]
        self.assertEqual(food["nutrients"], {"satFat": 2.5})


class DatabaseAndApiTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "test.db"
        records = recipedb.parse_search_page(search_page(raw_record()))
        with db.connect(self.path) as connection:
            db.init_db(connection)
            pipeline.load_ingredients(connection, CATALOG, FakeUSDA(), FLAVORS)
            pipeline.import_recipes(connection, CATALOG, records)
            pipeline.import_recipes(connection, CATALOG, records)  # must not duplicate
            pipeline.rebuild_derived(connection)
        self.client = TestClient(create_app(self.path))
        self.recipe_id = self.client.get("/api/recipes").json()["results"][0]["id"]

    def recommend(self, **body):
        return self.client.post(f"/api/recipes/{self.recipe_id}/recommend",
                                json={"goal": "satFat", **body})

    def test_import_is_idempotent_and_keeps_provenance(self):
        with db.connect(self.path) as connection:
            self.assertEqual(db.stats(connection)["recipes"], 1)
            rows = connection.execute(
                "SELECT * FROM recipe_ingredients ORDER BY position").fetchall()
            statuses = [r["missing_status"] for r in rows]
            self.assertEqual(statuses, ["ok", "ok", "unmatched"])
            self.assertEqual(rows[0]["original_phrase"], "2 tablespoons butter")
            self.assertEqual((rows[0]["grams"], rows[0]["source_ndb_id"]), (28.0, "1"))
            sources = {r["id"]: r["status"] for r in db.source_rows(connection)}
            self.assertEqual(sources["recipedb"], "loaded")
            ghee = connection.execute("SELECT data_status FROM ingredients WHERE id='ghee'").fetchone()
            self.assertEqual(ghee[0], "missing_both")
            self.assertEqual(connection.execute(
                "SELECT COUNT(*) FROM nutrients WHERE ingredient_id='ghee'").fetchone()[0], 0)

    def test_a_catalog_name_missing_from_usda_stops_the_build(self):
        broken = Catalog({"families": {"fat": "F"},
                          "roles": {"solid_fat": {"family": "fat", "label": "S", "substitutable": True}},
                          "ingredients": [{"id": "x", "name": "X", "role": "solid_fat", "usda": "typo"}]})
        with db.connect(Path(self.folder.name) / "other.db") as connection:
            db.init_db(connection)
            with self.assertRaisesRegex(ValueError, "do not exist"):
                pipeline.load_ingredients(connection, broken, FakeUSDA(), {})

    def test_build_still_works_without_flavor_data(self):
        with db.connect(Path(self.folder.name) / "noflavor.db") as connection:
            db.init_db(connection)
            pipeline.load_ingredients(connection, CATALOG, FakeUSDA(), {})
            pipeline.rebuild_derived(connection)
            self.assertEqual(db.stats(connection)["ingredients_with_flavor"], 0)
            self.assertEqual(db.stats(connection)["substitution_edges"], 1)

    def test_complete_workflow(self):
        detail = self.client.get(f"/api/recipes/{self.recipe_id}").json()
        self.assertEqual(detail["coverage"]["counted_lines"], 2)
        self.assertIsNone(detail["instructions"])
        result = self.recommend().json()
        self.assertEqual([(s["from_id"], s["to_id"]) for s in result["applied"]], [("butter", "spread")])
        self.assertAlmostEqual(result["goal_result"]["original"], 40 * 0.28)
        self.assertAlmostEqual(result["goal_result"]["modified"], 10 * 0.28)
        self.assertAlmostEqual(result["goal_result"]["gain_percent"], 75)
        self.assertAlmostEqual(result["similarity"]["flavor"], 0.5)
        self.assertIn("assumed 1:1", result["applied"][0]["ratio_basis"])
        self.assertIsNone(result["similarity"]["cuisine"])  # too few recipes

    def test_user_selection_and_ratio(self):
        line = self.recommend().json()["applied"][0]["line_id"]
        kept = self.recommend(selections={str(line): None}).json()
        self.assertEqual(kept["applied"], [])
        self.assertFalse(kept["goal_result"]["improved"])
        half = self.recommend(ratios={str(line): 0.5}).json()
        self.assertEqual(half["applied"][0]["new_grams"], 14)
        self.assertIn("chosen by you", half["applied"][0]["ratio_basis"])

    def test_invalid_requests(self):
        line = self.recommend().json()["applied"][0]["line_id"]
        self.assertEqual(self.recommend(selections={str(line): "onion"}).status_code, 400)
        self.assertEqual(self.recommend(ratios={str(line): 50}).status_code, 400)
        self.assertEqual(self.recommend(goal="taste").status_code, 422)
        zero = {"health": 0, "flavor": 0, "cuisine": 0, "role": 0}
        self.assertEqual(self.recommend(weights=zero).status_code, 400)
        self.assertEqual(self.client.get("/api/recipes/999999").status_code, 404)
        self.assertEqual(self.client.get("/api/ingredients/nope/network").status_code, 404)
        self.assertEqual(self.client.get("/api/recipes?limit=1000").status_code, 422)

    def test_search_filters_and_wildcards_are_literal(self):
        def total(query):
            return self.client.get(f"/api/recipes?{query}").json()["total"]

        self.assertEqual(total("q=toast"), 1)
        self.assertEqual(total("ingredient=moon"), 1)
        self.assertEqual(total("region=Thai"), 0)
        self.assertEqual(total("q=%25"), 0)
        self.assertEqual(total("q=%27%3B%20DROP%20TABLE%20recipes%3B--"), 0)
        self.assertEqual(total(""), 1)

    def test_health_and_network(self):
        health = self.client.get("/api/health").json()
        self.assertEqual(health["stats"]["recipes"], 1)
        graph = self.client.get("/api/ingredients/butter/network").json()
        self.assertEqual([e["target"] for e in graph["edges"]], ["spread"])

    def test_missing_database_is_reported_not_crashed(self):
        client = TestClient(create_app(Path(self.folder.name) / "absent.db"))
        for url in ("/api/health", "/api/recipes", "/api/regions"):
            response = client.get(url)
            self.assertEqual(response.status_code, 503, url)
            self.assertIn("build", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
