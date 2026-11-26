import unittest

from recipe_optimizer.matching import Catalog, candidate_names, normalise_key

CATALOG = Catalog.load()


class MatchingTests(unittest.TestCase):
    def assertMatches(self, phrase, expected, source="", unit=""):
        found = CATALOG.match(phrase, source, unit)
        self.assertEqual(found.ingredient_id, expected, f"{phrase!r} -> {found}")
        return found

    def test_quantities_units_and_preparation_words_are_ignored(self):
        self.assertMatches("1 1/2 cups finely chopped onions", "onion", "onion")
        self.assertMatches("2 tablespoons butter, melted and divided", "butter", "butter")
        self.assertMatches("1/2 teaspoon ground turmeric", "turmeric")
        self.assertMatches("boneless, skinless chicken breast halves", "chicken_breast")

    def test_similar_names_are_not_confused(self):
        self.assertMatches("1/4 cup peanut butter", "peanut_butter", "butter")
        self.assertMatches("1 cup coconut milk", "coconut_milk", "milk")
        self.assertMatches("2 large sweet potatoes, peeled", "sweet_potato", "potato")
        self.assertMatches("1/2 teaspoon ground cloves", "cloves", "clove")
        self.assertMatches("2 cloves garlic, minced", "garlic", "garlic")

    def test_unknown_foods_stay_unmatched_even_if_recipedb_suggests_a_name(self):
        # Neither may fall back to the shorter name RecipeDB extracted.
        self.assertMatches("2 tablespoons apple butter", None, "butter")
        self.assertMatches("1 cup frozen yogurt", None, "yogurt")
        self.assertMatches("1 whole chicken", None, "chicken")
        self.assertMatches("salt and pepper to taste", None, "salt")

    def test_a_spaced_compound_is_not_split_into_a_note(self):
        self.assertMatches("1 cup butter - flavored shortening", None, "butter")
        self.assertMatches("1 cup all - purpose flour", "flour_all_purpose", "flour")
        self.assertMatches("2 avocados - peeled , pitted , and chopped", "avocado", "avocado")

    def test_words_that_change_the_food_are_preserved(self):
        self.assertMatches("1 teaspoon dried basil", "basil_dried")
        self.assertMatches("1/4 cup fresh basil", "basil_fresh")
        self.assertMatches("1 teaspoon basil", None, "basil")  # fresh or dried is unknown
        self.assertMatches("2 cups cooked rice", "white_rice_cooked", "rice")
        self.assertMatches("1 cup uncooked white rice", "white_rice_dry", "rice")

    def test_canned_lines_use_canned_records_or_nothing(self):
        self.assertMatches("1 can chickpeas, drained", "chickpeas_canned", "chickpea", "can")
        self.assertMatches("1 (4 ounce) can mushrooms", "mushroom_canned", "mushroom", "can")
        found = self.assertMatches("1 can spinach", None, "spinach", "can")
        self.assertIn("canned", found.note)

    def test_confidence_and_assumptions_are_recorded(self):
        self.assertEqual(self.assertMatches("1 cup heavy cream", "heavy_cream").confidence, 1.0)
        assumed = self.assertMatches("1 cup milk", "milk_whole", "milk")
        self.assertEqual((assumed.method, assumed.confidence), ("assumed_variety", 0.7))
        self.assertIn("whole milk assumed", assumed.note)
        either = self.assertMatches("1 tablespoon olive oil or butter", "olive_oil")
        self.assertEqual((either.method, either.confidence), ("first_alternative", 0.6))

    def test_spelling_plurals_and_synonyms(self):
        self.assertEqual(normalise_key("Chillies"), normalise_key("chile"))
        self.assertMatches("1 cup plain yoghurt", "yogurt_whole")
        self.assertMatches("4 spring onions", "scallion")
        self.assertMatches("2 aubergines", "eggplant")

    def test_empty_input_is_safe(self):
        self.assertEqual(candidate_names(""), [])
        self.assertMatches("", None)

    def test_catalog_rejects_a_synonym_claimed_twice(self):
        data = {"families": {"f": "F"}, "roles": {"r": {"family": "f", "label": "R"}},
                "ingredients": [{"id": "a", "name": "Thing", "role": "r"},
                                {"id": "b", "name": "Other", "role": "r", "synonyms": ["things"]}]}
        with self.assertRaises(ValueError):
            Catalog(data)

    def test_catalog_holds_no_nutrient_or_flavor_values(self):
        forbidden = {"calories", "protein", "satFat", "fiber", "per100g", "nutrients", "flavor",
                     "molecules"}
        for entry in CATALOG.ingredients.values():
            self.assertFalse(forbidden & set(entry), entry["id"])


if __name__ == "__main__":
    unittest.main()
