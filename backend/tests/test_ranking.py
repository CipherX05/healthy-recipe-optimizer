import math
import unittest

from recipe_optimizer import network, scoring
from recipe_optimizer.models import Line, Swap

from .fixtures import ingredient, lines, pantry

SAT = scoring.GOALS["satFat"]
STATS = scoring.CuisineStats("Testland", 40, {"base": 30, "tasty": 20, "lean": 1, "twin": 30})


def rank(goal=SAT, weights=None, stats=STATS, title="", **kwargs):
    items = pantry()
    result = scoring.recommend(lines(), items, network.build_graph(items), goal, stats,
                               title=title, weights=weights, **kwargs)
    return result


def names(entries):
    return [e["ingredient_id"] for e in entries]


class ScoreTests(unittest.TestCase):
    def test_health_score_is_bounded_and_directional(self):
        self.assertAlmostEqual(scoring.health_score(50, 5, "min"), 0.9)
        self.assertEqual(scoring.health_score(50, 60, "min"), 0)
        self.assertAlmostEqual(scoring.health_score(5, 20, "max"), 0.75)
        self.assertEqual(scoring.health_score(0, 5, "max"), 1)  # zero baseline
        self.assertEqual(scoring.health_score(0, 0, "min"), 0)

    def test_jaccard(self):
        self.assertAlmostEqual(network.jaccard({1, 2, 3}, {2, 3, 4}), 0.5)
        self.assertIsNone(network.jaccard(set(), {1}))

    def test_cuisine_score_needs_enough_recipes(self):
        self.assertEqual(STATS.score("base"), 1.0)
        self.assertEqual(STATS.score("never_seen"), 0.0)
        self.assertAlmostEqual(STATS.score("lean"), math.log(2) / math.log(31))
        self.assertIsNone(scoring.CuisineStats("Tiny", 3, {"base": 3}).score("base"))
        self.assertIsNone(scoring.CuisineStats(None, 0, {}).score("base"))

    def test_weights_are_normalised_and_validated(self):
        result = scoring.normalise_weights({"health": 2, "flavor": 2, "cuisine": 0, "role": 0})
        self.assertEqual(result, {"health": 0.5, "flavor": 0.5, "cuisine": 0, "role": 0})
        for bad in ({"health": -1}, {"health": 0}, {"taste": 1}, {"health": float("nan")}):
            with self.assertRaises(ValueError):
                scoring.normalise_weights(bad)


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.entry = rank()[0]

    def test_flavor_alone_never_makes_a_recommendation(self):
        self.assertNotIn("twin", names(self.entry["candidates"]))
        twin = next(c for c in self.entry["rejected"] if c["ingredient_id"] == "twin")
        self.assertEqual(twin["scores"]["flavor"], 1.0)
        self.assertIn("does not improve", twin["reasons"][0])
        # Even when flavor is the only weight, it still cannot be recommended.
        flavor_only = rank(weights={"health": 0, "flavor": 1, "cuisine": 0, "role": 0})[0]
        self.assertNotIn("twin", names(flavor_only["candidates"]))

    def test_nutritionally_similar_is_not_treated_as_healthier(self):
        self.assertNotIn("near", names(self.entry["candidates"]))

    def test_only_role_compatible_ingredients_are_considered(self):
        everything = names(self.entry["candidates"] + self.entry["rejected"])
        self.assertNotIn("cheese", everything)  # another family despite the best numbers
        self.assertNotIn("tomato", everything)

    def test_overall_is_the_weighted_sum_and_orders_the_list(self):
        overall = [c["overall"] for c in self.entry["candidates"]]
        self.assertEqual(overall, sorted(overall, reverse=True))
        weights = scoring.DEFAULT_WEIGHTS
        for item in self.entry["candidates"]:
            expected = sum(weights[k] * (item["scores"][k] or 0) for k in scoring.COMPONENTS)
            self.assertAlmostEqual(item["overall"], expected)

    def test_missing_flavor_earns_nothing_and_is_reported(self):
        mystery = next(c for c in self.entry["candidates"] if c["ingredient_id"] == "mystery")
        self.assertIsNone(mystery["scores"]["flavor"])
        self.assertIsNone(mystery["flavor_detail"])
        self.assertAlmostEqual(mystery["weight_with_data"], 1 - scoring.DEFAULT_WEIGHTS["flavor"])

    def test_a_trivial_gain_is_not_recommended(self):
        items = pantry()
        # 0 -> 0.2 g fiber is a "100%" relative gain but means nothing.
        items["trace"] = ingredient("trace", satFat=1, calories=100, protein=1.5, fiber=0.2)
        for goal in ("fiber", "protein"):
            entry = scoring.recommend(lines(), items, network.build_graph(items), scoring.GOALS[goal], STATS)[0]
            trace = next(c for c in entry["rejected"] if c["ingredient_id"] == "trace")
            self.assertIn("too small to matter", trace["reasons"][0])

    def test_guardrail_blocks_fewer_calories_via_much_more_saturated_fat(self):
        items = pantry()
        items["base"] = ingredient("base", satFat=14, calories=880, sodium=0)
        items["greasy"] = ingredient("greasy", satFat=51, calories=717, sodium=0)
        items["salty"] = ingredient("salty", satFat=10, calories=500, sodium=900)

        def result(**kwargs):
            graph = network.build_graph(items)
            return scoring.recommend(lines(), items, graph, scoring.GOALS["calories"], STATS, **kwargs)[0]

        guarded = result()
        reasons = {c["ingredient_id"]: " ".join(c["reasons"]) for c in guarded["rejected"]}
        self.assertIn("saturated fat", reasons["greasy"])
        self.assertIn("sodium", reasons["salty"])
        self.assertIn("greasy", names(result(guardrails=False)["candidates"]))

    def test_related_roles_have_limits(self):
        cultured = ingredient("sour", role="cultured_dairy", family="dairy")
        milk = ingredient("milk", role="milk", family="dairy")
        cream = ingredient("cream", role="cooking_cream", family="dairy")
        buttermilk = ingredient("buttermilk", role="cultured_dairy", family="dairy", also=("milk",))
        self.assertEqual(network.role_score(cultured, milk), 0)
        self.assertEqual(network.role_score(cultured, cream), 0.6)
        self.assertEqual(network.role_score(milk, cream), 0.6)
        self.assertEqual(network.role_score(buttermilk, milk), 0.6)
        self.assertEqual(network.role_score(cultured, cultured), 1.0)

    def test_guardrail_never_applies_to_the_goal_itself(self):
        items = pantry()
        self.assertEqual(scoring.broken_guardrails(items["base"], items["twin"], 100, 1, SAT), [])

    def test_a_thin_flavor_profile_counts_as_no_data(self):
        items = pantry()
        thin = items["tasty"].__class__(**{**vars(items["tasty"]), "molecules": frozenset({100, 101})})
        self.assertIsNone(network.flavor_similarity(items["base"], thin))
        items["tasty"] = thin
        entry = scoring.recommend(lines(), items, network.build_graph(items), SAT, STATS)[0]
        tasty = next(c for c in entry["candidates"] if c["ingredient_id"] == "tasty")
        self.assertIsNone(tasty["scores"]["flavor"])
        self.assertIn("only 2 molecules", tasty["flavor_gap"])

    def test_user_weights_change_the_ranking(self):
        health = rank(weights={"health": 1, "flavor": 0, "cuisine": 0, "role": 0})[0]
        flavor = rank(weights={"health": 0, "flavor": 1, "cuisine": 0, "role": 0})[0]
        self.assertEqual(health["candidates"][0]["ingredient_id"], "lean")
        self.assertEqual(flavor["candidates"][0]["ingredient_id"], "tasty")

    def test_minimum_flavor_filter(self):
        filtered = rank(min_flavor=0.5)[0]
        self.assertEqual(names(filtered["candidates"]), ["tasty"])

    def test_recipe_gain_and_tradeoffs_are_reported(self):
        lean = next(c for c in self.entry["candidates"] if c["ingredient_id"] == "lean")
        self.assertAlmostEqual(lean["recipe_gain_percent"], 90)
        self.assertIn("calories", [t["key"] for t in lean["tradeoffs"]])

    def test_goal_direction_changes_eligibility(self):
        protein = rank(goal=scoring.GOALS["protein"])[0]
        self.assertEqual(names(protein["candidates"]), ["mystery"])
        self.assertEqual(rank(goal=scoring.GOALS["fiber"])[0]["candidates"][0]["ingredient_id"], "mystery")

    def test_candidate_without_the_goal_value_is_rejected(self):
        items = pantry()
        items["blank"] = ingredient("blank", calories=1)
        entry = scoring.recommend(lines(), items, network.build_graph(items), SAT, STATS)[0]
        blank = next(c for c in entry["rejected"] if c["ingredient_id"] == "blank")
        self.assertIsNone(blank["scores"]["health"])

    def test_whole_recipe_keeps_the_ingredient_named_in_the_title(self):
        results = rank(title="Butter Toast")
        self.assertTrue(results[0]["in_title"])
        self.assertEqual(scoring.choose_swaps(results, "recipe"), [])
        self.assertEqual(len(scoring.choose_swaps(results, "recipe", keep_title_ingredients=False)), 1)
        self.assertEqual(len(scoring.choose_swaps(results, "ingredient", 1)), 1)

    def test_unknown_quantity_gets_no_recommendation(self):
        items = pantry()
        recipe = [Line(1, "base", None), Line(2, None, 50)]
        self.assertEqual(scoring.recommend(recipe, items, network.build_graph(items), SAT, STATS), [])

    def test_a_shared_flavor_record_is_flagged_in_the_summary(self):
        items = pantry()
        items["base"] = ingredient("base", molecules={1, 2}, entity=5, satFat=50)
        items["lean"] = ingredient("lean", role="liquid_oil", molecules={1, 2}, entity=5, satFat=5)
        summary = scoring.similarity_summary(lines(), items, [Swap(1, "lean")], STATS)
        self.assertEqual((summary["flavor"], summary["flavor_same_record_swaps"]), (1.0, 1))

    def test_similarity_ignores_unchanged_ingredients(self):
        items = pantry()
        results = rank()
        swaps = scoring.choose_swaps(results, "ingredient", 1)
        summary = scoring.similarity_summary(lines(), items, swaps, STATS)
        expected = network.jaccard(items["base"].molecules, items[swaps[0].ingredient_id].molecules)
        self.assertEqual(summary["flavor"], expected)
        self.assertIsNone(scoring.similarity_summary(lines(), items, [], STATS)["flavor"])


if __name__ == "__main__":
    unittest.main()
