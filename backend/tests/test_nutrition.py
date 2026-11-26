import unittest

from recipe_optimizer import nutrition, quantities
from recipe_optimizer.models import Line, Swap

from .fixtures import ingredient, lines, pantry

PORTIONS = [
    {"amount": 1, "description": "cup, chopped", "gram_weight": 160},
    {"amount": 1, "description": "cup, sliced", "gram_weight": 115},
    {"amount": 1, "description": "large", "gram_weight": 150},
    {"amount": 1, "description": 'medium (2-1/2" dia)', "gram_weight": 110},
    {"amount": 3, "description": "cloves", "gram_weight": 9},
]


class QuantityTests(unittest.TestCase):
    def grams(self, quantity, unit, phrase="", portions=PORTIONS, **kwargs):
        return quantities.to_grams(quantity, unit, phrase, portions, **kwargs)

    def test_parse_quantity(self):
        self.assertEqual(quantities.parse_quantity("1 1/2"), (1.5, False))
        self.assertEqual(quantities.parse_quantity("½"), (0.5, False))
        self.assertEqual(quantities.parse_quantity("2 -3"), (2.5, True))
        for bad in ("", "some", "1/0", "0"):
            self.assertIsNone(quantities.parse_quantity(bad)[0], bad)

    def test_recipedb_field_splitting_errors_are_repaired(self):
        repair = quantities.repair_fields
        self.assertEqual(repair("1", "1/2 teaspoons", "1 1/2 teaspoons salt"), ("1 1/2", "teaspoons"))
        self.assertEqual(repair("1/3", "", "1/3 lb feta cheese"), ("1/3", "lb"))
        self.assertEqual(repair("2", "boneless", "2 boneless chicken breasts"), ("2", ""))
        self.assertEqual(repair("2", "", "2 large eggs"), ("2", ""))
        self.assertAlmostEqual(self.grams("1", "1/2 pounds").grams, 1.5 * 453.59237, places=3)

    def test_mass_units_are_exact(self):
        result = self.grams("2", "pounds")
        self.assertAlmostEqual(result.grams, 907.185, places=2)
        self.assertEqual((result.method, result.is_estimate), ("mass_unit", False))

    def test_printed_package_size_is_used(self):
        result = self.grams("2", "cans", "2 (14.5 ounce) cans tomatoes", portions=[])
        self.assertAlmostEqual(result.grams, 2 * 14.5 * 28.349523, places=3)
        self.assertEqual(result.method, "package_size")

    def test_usda_measure_matches_the_wording(self):
        self.assertEqual(self.grams("2", "cups", "2 cups sliced onion").grams, 230)
        self.assertEqual(self.grams("1", "cup", "1 cup chopped onion").grams, 160)

    def test_unusual_states_are_not_chosen_by_accident(self):
        cream = [{"amount": 1, "description": "cup, whipped", "gram_weight": 120},
                 {"amount": 1, "description": "cup, fluid (yields 2 cups whipped)", "gram_weight": 238}]
        self.assertEqual(self.grams("1", "cup", "1 cup heavy whipping cream", cream).grams, 238)
        self.assertEqual(self.grams("1", "cup", "1 cup whipped cream", cream).grams, 120)
        nuts = [{"amount": 1, "description": "cup, in shell, edible yield (7 nuts)", "gram_weight": 28},
                {"amount": 1, "description": "cup, chopped", "gram_weight": 117},
                {"amount": 1, "description": "cup pieces or chips", "gram_weight": 120}]
        self.assertEqual(self.grams("1", "cup", "1 cup walnuts", nuts, cup_form="chopped").grams, 117)

    def test_usual_form_yields_to_the_recipe_wording(self):
        self.assertEqual(self.grams("1", "cup", "1 cup onion", cup_form="chopped").grams, 160)
        self.assertEqual(self.grams("1", "cup", "1 cup sliced onion", cup_form="chopped").grams, 115)

    def test_volume_is_converted_only_from_that_foods_own_measure(self):
        result = self.grams("2", "tablespoons", "2 tablespoons chopped onion")
        self.assertAlmostEqual(result.grams, 20, places=3)
        self.assertEqual(result.method, "usda_volume_converted")

    def test_no_density_is_assumed(self):
        result = self.grams("1", "cup", "1 cup mystery", portions=[])
        self.assertIsNone(result.grams)
        self.assertEqual(result.method, "unresolved")

    def test_counted_items(self):
        self.assertEqual(self.grams("2", "", "2 onions").grams, 220)  # medium assumed
        self.assertIn("assumed", self.grams("2", "", "2 onions").note)
        self.assertEqual(self.grams("1", "", "1 large onion").grams, 150)
        self.assertEqual(self.grams("2", "cloves", "2 cloves garlic").grams, 6)
        self.assertIsNone(self.grams("2", "sprigs", "2 sprigs thyme").grams)

    def test_a_part_of_an_item_is_not_mistaken_for_its_size(self):
        carrot = [{"amount": 1, "description": 'large (7" long)', "gram_weight": 72},
                  {"amount": 1, "description": "medium", "gram_weight": 61},
                  {"amount": 1, "description": 'strip large (3" long)', "gram_weight": 7}]
        self.assertEqual(self.grams("1", "", "1 large carrot", carrot).grams, 72)
        tomato = [{"amount": 1, "description": "slice, thin/small", "gram_weight": 15},
                  {"amount": 1, "description": 'small whole (2" dia)', "gram_weight": 91}]
        self.assertEqual(self.grams("1", "", "1 small tomato", tomato).grams, 91)

    def test_counted_nouns_use_the_stated_or_medium_size(self):
        celery = [{"amount": 1, "description": "stalk, large", "gram_weight": 64},
                  {"amount": 1, "description": "stalk, medium", "gram_weight": 40},
                  {"amount": 1, "description": "stalk, small", "gram_weight": 17}]
        self.assertEqual(self.grams("3", "stalks", "3 stalks celery", celery).grams, 120)
        self.assertEqual(self.grams("2", "", "2 ribs celery", celery).grams, 80)
        self.assertEqual(self.grams("1", "stalk", "1 large stalk celery", celery).grams, 64)
        cabbage = [{"amount": 1, "description": "leaf, medium", "gram_weight": 23},
                   {"amount": 1, "description": "head, medium", "gram_weight": 908}]
        self.assertEqual(self.grams("1", "", "1 head cabbage, cored", cabbage).grams, 908)

    def test_an_unstated_can_size_is_not_borrowed(self):
        portions = [{"amount": 1, "description": "can", "gram_weight": 190}]
        self.assertIsNone(self.grams("2", "cans", "2 cans diced tomatoes", portions).grams)

    def test_unmeasurable_lines_stay_unknown(self):
        for quantity, unit, phrase in (("1", "pinch", "1 pinch salt"), ("", "", "salt to taste"),
                                       ("1", "can", "1 can soup"), ("", "", "oil")):
            self.assertIsNone(self.grams(quantity, unit, phrase, portions=[]).grams, phrase)


class NutritionTests(unittest.TestCase):
    def row(self, rows, key):
        return next(r for r in rows if r["key"] == key)

    def test_totals_scale_with_grams_and_servings(self):
        rows = nutrition.compare(lines(), pantry(), [Swap(1, "lean")], servings=4)
        fat = self.row(rows, "satFat")
        self.assertAlmostEqual(fat["original"], 50)
        self.assertAlmostEqual(fat["modified"], 5)
        self.assertAlmostEqual(fat["change"], -45)
        self.assertAlmostEqual(fat["percent_change"], -90)
        self.assertAlmostEqual(fat["per_serving"]["original"], 12.5)
        self.assertAlmostEqual(self.row(rows, "calories")["original"], 700 + 40)

    def test_quantity_ratio_is_applied_to_the_substitute_only(self):
        rows = nutrition.compare(lines(), pantry(), [Swap(1, "lean", ratio=0.5)])
        self.assertAlmostEqual(self.row(rows, "satFat")["modified"], 2.5)
        self.assertAlmostEqual(self.row(rows, "satFat")["original"], 50)

    def test_percent_change_from_zero_is_undefined(self):
        fiber = self.row(nutrition.compare([Line(1, "base", 100)], pantry(), [Swap(1, "mystery")]), "fiber")
        self.assertEqual((fiber["original"], fiber["modified"]), (0, 5))
        self.assertIsNone(fiber["percent_change"])

    def test_a_missing_value_removes_the_line_from_both_sides(self):
        items = pantry()
        items["nofiber"] = ingredient("nofiber", satFat=1, calories=100)
        rows = nutrition.compare(lines(), items, [Swap(1, "nofiber")])
        fiber = self.row(rows, "fiber")
        # Only the tomato counts: the butter line is dropped, not treated as zero.
        self.assertEqual((fiber["original"], fiber["modified"]), (2, 2))
        self.assertEqual(fiber["lines_missing_value"], [1])
        self.assertAlmostEqual(self.row(rows, "satFat")["modified"], 1)

    def test_nutrient_nobody_reports_is_unknown_not_zero(self):
        sodium = self.row(nutrition.compare(lines(), pantry()), "sodium")
        self.assertIsNone(sodium["original"])

    def test_coverage_lists_every_excluded_line(self):
        recipe = lines() + [Line(3, None, None, "1 mystery"), Line(4, "base", None, "butter to taste")]
        report = nutrition.coverage(recipe, pantry())
        self.assertEqual((report["counted_lines"], report["total_lines"]), (2, 4))
        self.assertEqual([e["reason"] for e in report["excluded"]], ["unmatched", "unknown_quantity"])


if __name__ == "__main__":
    unittest.main()
