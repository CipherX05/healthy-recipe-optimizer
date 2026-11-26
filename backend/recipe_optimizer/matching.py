"""Ingredient-name standardisation and conservative catalog matching.

Rule: a line is matched only when its cleaned ingredient name is *exactly* a
catalog name or synonym. There is no fuzzy or substring matching, so "peanut
butter" can never become "butter". Anything else stays unmatched and is shown
to the user as missing data.

Cleaning happens in levels, least destructive first, so a catalog entry such as
"crushed red pepper" wins before the word "crushed" would be stripped:

  level 0  remove quantity, leading measure words and notes
  level 1  also remove size / knife-work words  (confidence high)
  level 2  also remove "fresh", "raw", "frozen"  (confidence medium)

Words that change the food itself (dried, cooked, canned, smoked, ground,
sweetened...) are never removed.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import config

LEADING_MEASURES = {
    "c", "cup", "tablespoon", "tbsp", "tbs", "tb", "teaspoon", "tsp", "pound", "lb", "ounce", "oz",
    "fluid", "fl", "g", "gm", "gram", "kg", "kilogram", "ml", "milliliter", "millilitre", "liter",
    "litre", "l", "pint", "quart", "gallon", "can", "tin", "package", "pkg", "packet", "jar",
    "bottle", "container", "carton", "box", "bag", "pinch", "dash", "clove", "slice", "sprig",
    "bunch", "stick", "head", "stalk", "piece", "inch", "handful", "envelope", "drop", "splash",
    "knob", "cube", "rib", "ear", "loaf", "fillet",
}
# Words that never change what the food is.
SAFE_DESCRIPTORS = {
    "chopped", "minced", "diced", "sliced", "grated", "shredded", "crushed", "cubed", "julienned",
    "halved", "quartered", "peeled", "seeded", "deseeded", "cored", "trimmed", "rinsed", "washed",
    "drained", "pitted", "beaten", "melted", "softened", "sifted", "packed", "heaping", "level",
    "rounded", "scant", "finely", "coarsely", "thinly", "roughly", "freshly", "lightly", "firmly",
    "large", "medium", "small", "jumbo", "big", "thin", "thick", "whole", "ripe", "firm",
    "divided", "optional", "separated", "mashed", "torn", "crumbled", "warm", "cold", "hot",
    "boneless", "skinless", "lean", "good", "quality", "organic", "room", "temperature",
    "a", "an", "the", "of", "about", "approximately", "plus", "extra", "more", "and",
}
STATE_RELAXED = {"fresh", "raw", "frozen", "thawed", "uncooked"}
# Dropping these would change the food, so they are protected from descriptor removal.
PROTECTED_PAIRS = {("extra", "virgin"), ("extra", "firm"), ("extra", "lean"), ("half", "and"),
                   ("and", "half"), ("whole", "wheat"), ("whole", "milk"), ("whole", "grain"),
                   ("whole", "chicken"), ("hot", "sauce"), ("hot", "dog"), ("lean", "ground"),
                   ("frozen", "yogurt"), ("raw", "sugar")}
CAN_UNITS = {"can", "cans", "tin", "tins"}
NOTE_PHRASES = re.compile(
    r"\b(to taste|as needed|as required|for (?:garnish|serving|frying|greasing|dusting|decoration)"
    r"|or (?:to|as) .*|plus more .*|such as .*|(?:cut|torn|broken) in(?:to)? .*)$"
)
FRACTIONS = "¼½¾⅓⅔⅛⅜⅝⅞⅕⅖⅗⅘⅙⅚"
COMPOUND_TAILS = r"flavou?red|style|free|fat|purpose|sodium|salted|sweetened"


def singular(token: str) -> str:
    """Light stemmer. It only has to treat both sides of a comparison the same way."""
    if len(token) <= 3 or token.endswith(("ss", "us", "is")):
        return token
    irregular = {"leaves": "leaf", "halves": "half", "loaves": "loaf", "chiles": "chile",
                 "chilies": "chile", "chillies": "chile", "cloves": "clove", "olives": "olive",
                 "chives": "chive", "molasses": "molasses"}
    if token in irregular:
        return irregular[token]
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith(("oes", "ches", "shes", "sses", "xes")):
        return token[:-2]
    return token[:-1] if token.endswith("s") else token


SPELLING = {"yoghurt": "yogurt", "yoghourt": "yogurt", "chilli": "chili", "whisky": "whiskey",
            "flavour": "flavor", "doughnut": "donut"}


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).casefold()
    text = re.sub(r"[‐-―\-_/]", " ", text)
    text = re.sub(r"[^a-z0-9éèêîïôûñç%\s]", " ", text)
    return [SPELLING.get(t, t) for t in (singular(t) for t in text.split())]


def normalise_key(name: str) -> str:
    return " ".join(tokens(name))


def _strip_quantity_and_measures(segment: str) -> list[str]:
    segment = re.sub(rf"[{FRACTIONS}]", " ", segment)
    words = tokens(re.sub(r"(\d)\s*(?=[a-z])", r"\1 ", segment))
    while words and (words[0] in LEADING_MEASURES or re.fullmatch(r"\d+", words[0])
                     or words[0] in {"x", "to", "or", "a", "an"}):
        # "clove" is a measure in "2 cloves garlic" but a spice when nothing follows it.
        if words[0] == "clove" and len(words) == 1:
            break
        words = words[1:]
        if words and words[0] == "of":
            words = words[1:]
    return [w for w in words if not re.fullmatch(r"\d+", w)]


def _drop(words: list[str], unwanted: set[str]) -> list[str]:
    kept = []
    for index, word in enumerate(words):
        pair_next = (word, words[index + 1]) if index + 1 < len(words) else None
        pair_prev = (words[index - 1], word) if index > 0 else None
        if word in unwanted and pair_next not in PROTECTED_PAIRS and pair_prev not in PROTECTED_PAIRS:
            continue
        kept.append(word)
    # The measure may only become leading once "large" etc. are gone.
    while len(kept) > 1 and kept[0] in LEADING_MEASURES:
        kept = kept[1:]
    return kept


def candidate_names(phrase: str) -> list[tuple[int, str, bool]]:
    """Possible ingredient names for a recipe line: (level, name, from_alternative)."""
    text = phrase.casefold()
    previous = None
    while previous != text:  # remove nested parentheses
        previous, text = text, re.sub(r"\([^()]*\)", " ", text)
    text = re.sub(r"[()]", " ", text)
    # " - " usually starts a note, but not in a spaced compound such as
    # "butter - flavored shortening" or "fat - free sour cream".
    text = re.sub(rf"\s+-\s+(?=(?:{COMPOUND_TAILS})\b)", "-", text)
    segments = [NOTE_PHRASES.sub("", s.strip()).strip() for s in re.split(r"[,;]| - ", text)]

    # A comma usually introduces preparation notes, but "boneless, skinless chicken"
    # puts descriptors first: use the first segment that names something.
    primary: list[str] = []
    for index, segment in enumerate(segments):
        words = _strip_quantity_and_measures(segment)
        if _drop(words, SAFE_DESCRIPTORS | STATE_RELAXED):
            primary = words
            # "skinless, boneless chicken breast halves": later text is notes.
            del index
            break
    if not primary:
        return []

    variants: list[tuple[list[str], bool]] = []
    joined = " ".join(primary)
    if " or " in f" {joined} ":
        variants.append((primary, False))
        variants.append((joined.split(" or ")[0].split(), True))
    else:
        variants.append((primary, False))

    out: list[tuple[int, str, bool]] = []
    for words, alternative in variants:
        for level, unwanted in ((0, set()), (1, SAFE_DESCRIPTORS), (2, SAFE_DESCRIPTORS | STATE_RELAXED)):
            name = " ".join(_drop(words, unwanted))
            if name and all(name != n for _, n, _ in out):
                out.append((level, name, alternative))
    return out


@dataclass
class Match:
    ingredient_id: str | None
    standardized_name: str
    method: str
    confidence: float
    note: str = ""


class Catalog:
    """The reviewed ingredient vocabulary. It stores identities, never nutrient values."""

    def __init__(self, data: dict):
        self.families: dict[str, str] = data["families"]
        self.roles: dict[str, dict] = data["roles"]
        self.ingredients: dict[str, dict] = {}
        self.index: dict[str, str] = {}
        self.assumed: dict[str, str] = {}  # vague names -> the stated assumption
        for entry in data["ingredients"]:
            if entry["id"] in self.ingredients:
                raise ValueError(f"duplicate ingredient id {entry['id']}")
            if entry["role"] not in self.roles:
                raise ValueError(f"{entry['id']}: unknown role {entry['role']}")
            for role in entry.get("also", []):
                if role not in self.roles:
                    raise ValueError(f"{entry['id']}: unknown role {role}")
            self.ingredients[entry["id"]] = entry
            vague = entry.get("assumed", {})
            for synonym in [entry["name"], *entry.get("synonyms", []), *vague]:
                key = normalise_key(synonym)
                owner = self.index.setdefault(key, entry["id"])
                if owner != entry["id"]:
                    raise ValueError(f"synonym {synonym!r} is claimed by {owner} and {entry['id']}")
            for synonym, assumption in vague.items():
                self.assumed[normalise_key(synonym)] = assumption

    @classmethod
    def load(cls, path: Path | None = None) -> "Catalog":
        return cls(json.loads((path or config.CATALOG_PATH).read_text(encoding="utf-8")))

    def lookup(self, name: str) -> str | None:
        return self.index.get(normalise_key(name))

    def match(self, phrase: str, source_name: str = "", unit: str = "") -> Match:
        """Match one recipe line. ``source_name`` is RecipeDB's own parsed name."""
        names = candidate_names(phrase) or candidate_names(source_name)
        canned = unit.strip().lower() in CAN_UNITS
        for level, name, alternative in names:
            # "1 can chickpeas" must find the canned food, never the dry or fresh one.
            ingredient_id = self.index.get(f"canned {name}") if canned else None
            if not ingredient_id:
                ingredient_id = self.index.get(name)
                if ingredient_id and canned and not self.ingredients[ingredient_id].get("can_ok"):
                    return Match(None, f"canned {name}", "unmatched", 0.0,
                                 "the canned form of this food is not in the catalog")
            if not ingredient_id:
                continue
            notes = []
            confidence, method = 1.0, "synonym_exact"
            if level == 2:
                confidence, method = 0.8, "synonym_state_relaxed"
                notes.append("fresh/raw/frozen wording ignored")
            if name in self.assumed:
                confidence, method = min(confidence, 0.7), "assumed_variety"
                notes.append(self.assumed[name])
            if alternative:
                confidence, method = 0.6, "first_alternative"
                notes.append("line offers alternatives; the first one was used")
            source_id = self.lookup(source_name) if source_name else None
            if source_id and source_id != ingredient_id:
                confidence = min(confidence, 0.8)
                notes.append(f"RecipeDB parsed this as '{source_name}'; the full line is more specific")
            return Match(ingredient_id, self.ingredients[ingredient_id]["name"], method, confidence,
                         "; ".join(notes))
        cleaned = next((n for level, n, _ in reversed(names) if level), "")
        cleaned = cleaned or (names[-1][1] if names else normalise_key(source_name or phrase))
        return Match(None, cleaned, "unmatched", 0.0, "no exact catalog name or synonym")
