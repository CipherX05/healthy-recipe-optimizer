"""Test doubles. Every nutrient value and molecule id here is made up for testing
and is never written to the real database."""
from recipe_optimizer.models import Ingredient, Line


def profile(ids):
    """Ten stand-in molecules per id: large enough to be usable, same ratios."""
    return frozenset(i * 100 + k for i in ids for k in range(10))


def ingredient(id, role="solid_fat", family="fat", *, substitutable=True, molecules=(),
               name=None, also=(), entity=None, **nutrients):
    return Ingredient(
        id=id, name=name or id.replace("_", " ").title(), role=role, family=family,
        role_label=role, family_label=family, also=tuple(also), substitutable=substitutable,
        nutrients=dict(nutrients), molecules=profile(molecules),
        flavor_entity_id=entity, flavor_entity_name=None,
    )


def pantry():
    """A toy fat family: one original and candidates with distinct trade-offs."""
    items = [
        ingredient("base", molecules={1, 2, 3, 4}, name="Butter",
                   satFat=50, calories=700, protein=1, fiber=0),
        # Same flavor as the original but worse for saturated fat.
        ingredient("twin", molecules={1, 2, 3, 4}, satFat=60, calories=900, protein=0, fiber=0),
        # Nearly identical nutrition: similar, but hardly healthier.
        ingredient("near", molecules={1, 2}, satFat=49.5, calories=699, protein=1, fiber=0),
        ingredient("lean", role="liquid_oil", molecules={5, 6},
                   satFat=5, calories=880, protein=0, fiber=0),
        ingredient("tasty", role="liquid_oil", molecules={1, 2, 3, 9},
                   satFat=25, calories=800, protein=0, fiber=0),
        # No flavor data at all.
        ingredient("mystery", satFat=10, calories=300, protein=5, fiber=5),
        ingredient("cheese", role="hard_cheese", family="cheese", molecules={1, 2, 3, 4},
                   satFat=1, calories=100, protein=30, fiber=0),
        ingredient("tomato", role="vegetable", family="other", substitutable=False,
                   satFat=0, calories=20, protein=1, fiber=1),
    ]
    return {i.id: i for i in items}


def lines():
    return [Line(1, "base", 100.0, "100 g butter"), Line(2, "tomato", 200.0, "200 g tomato")]
