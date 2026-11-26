"""Plain data objects shared by the nutrition, scoring and API layers."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ingredient:
    id: str
    name: str
    role: str
    family: str
    role_label: str = ""
    family_label: str = ""
    also: tuple[str, ...] = ()
    substitutable: bool = False
    nutrients: dict[str, float] = field(default_factory=dict)  # per 100 g
    nutrition_source: str | None = None
    nutrition_match: str | None = None  # "exact" | "proxy"
    nutrition_note: str = ""
    source_food_id: str | None = None
    source_food_name: str | None = None
    flavor_entity_id: int | None = None
    flavor_entity_name: str | None = None
    flavor_match: str | None = None  # "exact" | "proxy"
    molecules: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Line:
    """One recipe ingredient line after matching and quantity conversion."""

    id: int
    ingredient_id: str | None
    grams: float | None
    original_phrase: str = ""
    grams_is_estimate: bool = True


@dataclass(frozen=True)
class Swap:
    line_id: int
    ingredient_id: str
    ratio: float = 1.0  # grams of substitute per gram of original
