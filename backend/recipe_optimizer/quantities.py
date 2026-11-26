"""Turn recipe quantities into grams, only where there is evidence.

Conversions, from most to least reliable:
  mass_unit              g / kg / oz / lb (exact arithmetic)
  package_size           "2 (14.5 ounce) cans" -> the printed package weight
  usda_portion           a USDA SR Legacy household measure for that very food
  usda_volume_converted  another USDA volume measure of that food, rescaled
  usda_count_portion     USDA weight of one item (a "medium" onion, a clove)

If none applies, grams stay unknown. In particular, no water-like density is
ever assumed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MASS_GRAMS = {"g": 1.0, "kg": 1000.0, "oz": 28.349523, "lb": 453.59237}
VOLUME_ML = {
    "tsp": 4.928922, "tbsp": 14.786765, "floz": 29.57353, "cup": 236.58824, "pint": 473.17647,
    "quart": 946.35295, "gallon": 3785.4118, "ml": 1.0, "l": 1000.0,
}
UNIT_ALIASES = {
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "tsp": "tsp", "tsps": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "tbsp": "tbsp", "tbsps": "tbsp", "tbs": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "c": "cup", "cup": "cup", "cups": "cup",
    "fl oz": "floz", "fluid ounce": "floz", "fluid ounces": "floz",
    "pint": "pint", "pints": "pint", "pt": "pint", "quart": "quart", "quarts": "quart", "qt": "quart",
    "gallon": "gallon", "gallons": "gallon",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
}
PACKAGE_UNITS = {"can", "cans", "tin", "tins", "package", "packages", "pkg", "packet", "packets",
                 "jar", "jars", "bottle", "bottles", "container", "containers", "carton",
                 "cartons", "box", "boxes", "bag", "bags", "envelope", "envelopes"}
UNMEASURABLE = {"pinch", "pinches", "dash", "dashes", "handful", "handfuls", "splash", "drop",
                "drops", "sprinkle", "taste"}
UNICODE_FRACTIONS = {"¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8",
                     "⅜": "3/8", "⅝": "5/8", "⅞": "7/8", "⅕": "1/5", "⅖": "2/5",
                     "⅗": "3/5", "⅘": "4/5", "⅙": "1/6", "⅚": "5/6"}
# Words in a recipe line that select between USDA measures of the same unit.
FORM_WORDS = ("chopped", "diced", "sliced", "minced", "grated", "shredded", "crumbled", "cubed",
              "mashed", "packed", "whipped", "melted", "ground", "whole", "halves", "crushed",
              "julienne", "strips", "pieces", "unpacked", "sifted", "spaghetti", "elbow", "penne",
             "farfalle", "rotini", "shells", "lasagna", "slivered")
# Measures of a food in an unusual state; used only when the recipe line says so.
UNUSUAL_FORMS = ("whipped", "in shell", "hulls", "melted", "pureed", "cherry", "crumbs", "ground")
SIZE_WORDS = ("extra large", "jumbo", "large", "medium", "small")
# USDA measures for a piece of an item; "strip large" is not a large carrot.
PART_WORDS = ("strip", "slice", "ring", "wedge", "leaf", "pat", "yield")
_LEADING_NOUN = re.compile(
    r"^\s*[\d/ .\u00bc-\u00be\u2150-\u215e-]+\s*(?:\([^)]*\)\s*)?(?:(?:large|medium|small)\s+)?"
    r"(heads?|stalks?|ribs?|leaf|leaves|bunch(?:es)?|sprigs?|ears?)\b")
_NUMBER = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d*\.\d+|\d+)"


@dataclass
class Grams:
    grams: float | None
    method: str
    note: str
    is_estimate: bool = True


def _to_float(text: str) -> float | None:
    total = 0.0
    for part in text.split():
        if "/" in part:
            top, bottom = part.split("/", 1)
            if float(bottom) == 0:
                return None
            total += float(top) / float(bottom)
        else:
            total += float(part)
    return total


def parse_quantity(raw: str) -> tuple[float | None, bool]:
    """Return (value, was_range). Ranges such as "2 -3" give their midpoint."""
    text = raw or ""
    for symbol, replacement in UNICODE_FRACTIONS.items():
        text = text.replace(symbol, f" {replacement} ")
    text = re.sub(r"\s+", " ", text).strip().lower()
    if not text:
        return None, False
    span = re.fullmatch(rf"({_NUMBER})\s*(?:-|to|or|–)\s*({_NUMBER})", text)
    if span:
        low, high = _to_float(span.group(1)), _to_float(span.group(2))
        if low is None or high is None:
            return None, False
        if high < low:  # "1 -1/2" is a mis-split mixed number, not a range
            return low + high, False
        return (low + high) / 2, True
    if re.fullmatch(_NUMBER, text):
        value = _to_float(text)
        return (value, False) if value and value > 0 else (None, False)
    return None, False


def normalise_unit(raw: str) -> str:
    unit = re.sub(r"[.\s]+", " ", (raw or "").lower()).strip()
    return UNIT_ALIASES.get(unit, unit)


def _singular_unit(unit: str) -> str:
    if unit.endswith("ves") and unit != "cloves":
        return unit[:-3] + "f"
    if unit == "cloves":
        return "clove"
    if unit.endswith(("ches", "shes")):
        return unit[:-2]
    return unit[:-1] if unit.endswith("s") and len(unit) > 2 else unit


def portion_unit(description: str) -> str:
    """The unit a USDA portion description starts with: "cup, chopped" -> "cup"."""
    text = description.lower().strip()
    if text.startswith("fl oz"):
        return "floz"
    head = re.split(r"[\s,(]+", text, maxsplit=1)[0].rstrip(".")
    return UNIT_ALIASES.get(head, _singular_unit(head))


def _says(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}", text) is not None


def _choose(portions: list[dict], phrase: str, form: str = "") -> dict:
    """Pick among several measures of one food.

    In order: avoid unusual states the line does not mention, follow the line's
    own wording, then the catalog's usual form, then take the plainest measure.
    Bracketed remarks are ignored: "cup, fluid (yields 2 cups whipped)" is fluid.
    """
    text = phrase.lower()

    def rank(portion: dict) -> tuple:
        description = re.sub(r"\([^)]*\)", " ", portion["description"].lower()).strip()
        unusual = any(_says(description, w) and not _says(text, w) for w in UNUSUAL_FORMS)
        matched = sum(1 for w in FORM_WORDS if _says(description, w) and _says(text, w))
        unrequested = sum(1 for w in FORM_WORDS if _says(description, w) and not _says(text, w))
        usual = bool(form) and _says(description, form)
        return (unusual, -matched, not usual, unrequested, len(description))

    return min(portions, key=rank)


def _per_unit(portion: dict) -> float:
    return portion["gram_weight"] / portion["amount"]


# Preparation words that RecipeDB sometimes stores as a "unit".
NOT_UNITS = {"halved", "boneless", "skinless", "chopped", "diced", "sliced", "minced", "peeled",
             "whole", "trimmed", "seeded", "quartered", "crushed", "grated", "shredded"}


def repair_fields(quantity_raw: str, unit_raw: str, phrase: str) -> tuple[str, str]:
    """Undo known RecipeDB field-splitting errors, using only the line's own text.

    "1 1/2 teaspoons" arrives as quantity "1", unit "1/2 teaspoons"; "1/3 lb feta"
    can arrive with an empty unit.
    """
    quantity, unit = (quantity_raw or "").strip(), (unit_raw or "").strip()
    mixed = re.fullmatch(r"(\d+/\d+)(?:\s+(.*))?", unit)
    if mixed and re.fullmatch(r"\d+", quantity):
        quantity, unit = f"{quantity} {mixed.group(1)}", (mixed.group(2) or "").strip()
    if unit.lower() in NOT_UNITS:
        unit = ""
    if not unit and quantity:
        stated = re.match(rf"\s*{re.escape(quantity)}\s*(lbs?|pounds?|oz|ounces?|kg|grams?|g)\b\.?",
                          phrase.lower())
        if stated:
            unit = stated.group(1)
    return quantity, unit


def to_grams(quantity_raw: str, unit_raw: str, phrase: str, portions: list[dict],
             *, size: str = "", count_hint: str = "", cup_form: str = "") -> Grams:
    """Convert one recipe line to grams using the matched food's USDA measures."""
    quantity_raw, unit_raw = repair_fields(quantity_raw, unit_raw, phrase)
    quantity, was_range = parse_quantity(quantity_raw)
    unit = normalise_unit(unit_raw)
    range_note = f"midpoint of the range {quantity_raw.strip()}; " if was_range else ""

    if unit in UNMEASURABLE or re.search(r"\bto taste\b", phrase.lower()) and quantity is None:
        return Grams(None, "unresolved", f"'{unit or 'to taste'}' has no defined weight")
    if quantity is None:
        return Grams(None, "unresolved", "no usable quantity on the recipe line")

    # A printed package size is better than any generic can or packet weight.
    package = re.search(rf"\(\s*({_NUMBER})\s*[- ]?\s*(fl\.? oz|fluid ounces?|ounces?|oz|pounds?|lbs?|grams?|g|ml|kg)\.?\s*\)",
                        phrase.lower())
    if package and (unit in PACKAGE_UNITS or unit == ""):
        size_value = _to_float(package.group(1))
        size_unit = normalise_unit(package.group(2))
        if size_value and size_unit in MASS_GRAMS:
            return Grams(quantity * size_value * MASS_GRAMS[size_unit], "package_size",
                         f"{range_note}{quantity:g} x {size_value:g} {size_unit} package")

    if unit in MASS_GRAMS:
        return Grams(quantity * MASS_GRAMS[unit], "mass_unit",
                     f"{range_note}{quantity:g} {unit}", is_estimate=was_range)

    if unit in VOLUME_ML:
        volume = [p for p in portions if portion_unit(p["description"]) in VOLUME_ML]
        if not volume:
            return Grams(None, "unresolved", f"USDA gives no volume measure for this food ({unit})")
        same = [p for p in volume if portion_unit(p["description"]) == unit]
        if same:
            best = _choose(same, phrase, cup_form)
            return Grams(quantity * _per_unit(best), "usda_portion",
                         f"{range_note}USDA: {best['amount']:g} {best['description']} = {best['gram_weight']:g} g")
        best = _choose(volume, phrase, cup_form)
        other = portion_unit(best["description"])
        grams = quantity * _per_unit(best) * VOLUME_ML[unit] / VOLUME_ML[other]
        return Grams(grams, "usda_volume_converted",
                     f"{range_note}from USDA: {best['amount']:g} {best['description']} = {best['gram_weight']:g} g")

    if unit in PACKAGE_UNITS:
        # Can and packet sizes vary too much to borrow a "typical" one.
        return Grams(None, "unresolved", f"size of the {_singular_unit(unit)} is not stated")

    # Counted items: "2 cloves garlic", "1 large onion", "3 eggs".
    wanted_size = next((s for s in SIZE_WORDS if s in f"{size} {phrase}".lower()), "")
    noun = _singular_unit(unit) if unit else ""
    if noun in {"large", "medium", "small", "jumbo", "whole"}:
        wanted_size, noun = ("" if noun == "whole" else noun), ""
    if not noun:  # "1 head cabbage" often arrives without a unit
        leading = _LEADING_NOUN.match(phrase.lower())
        if leading:
            noun = _singular_unit(leading.group(1))
    if noun == "rib":
        noun = "stalk"

    def describes(portion: dict, word: str) -> bool:
        return re.search(rf"\b{re.escape(word)}s?\b", portion["description"].lower()) is not None

    def is_part(portion: dict) -> bool:
        return any(describes(portion, w) for w in PART_WORDS)

    def pick(hits: list[dict], size_word: str) -> dict:
        """Among several measures of one noun: the stated size, else medium, else plainest."""
        if size_word != "extra large":
            hits = [p for p in hits if not describes(p, "extra large")] or hits
        for preferred in (size_word, "medium"):
            sized = [p for p in hits if preferred and describes(p, preferred)]
            if sized:
                hits = sized
                break
        return min(hits, key=lambda p: len(p["description"]))

    countable = [p for p in portions if portion_unit(p["description"]) not in VOLUME_ML
                 and portion_unit(p["description"]) not in MASS_GRAMS]
    if noun:
        hits = [p for p in countable if portion_unit(p["description"]) == noun]
        if hits:
            best = pick(hits, wanted_size)
            return Grams(quantity * _per_unit(best), "usda_count_portion",
                         f"{range_note}one {noun}; USDA: {best['amount']:g} {best['description']} = {best['gram_weight']:g} g")
        return Grams(None, "unresolved", f"USDA gives no weight for a counted '{noun}'")

    attempts: list[tuple[str, str]] = []
    if count_hint:
        attempts.append((count_hint, f"one {count_hint}"))
    if wanted_size:
        attempts.append((wanted_size, f"one {wanted_size} item"))
    else:
        attempts.append(("medium", "no size given, so USDA 'medium' is assumed"))
    for word, explanation in attempts:
        hits = [p for p in countable if describes(p, word)]
        if word != count_hint:
            hits = [p for p in hits if not is_part(p)]
        if hits:
            # A hint such as "large" for eggs still yields to a stated size.
            best = pick(hits, wanted_size)
            if wanted_size and not describes(best, wanted_size):
                sized = [p for p in countable if describes(p, wanted_size) and not is_part(p)]
                if sized:
                    best = pick(sized, wanted_size)
                    explanation = f"one {wanted_size} item"
            return Grams(quantity * _per_unit(best), "usda_count_portion",
                         f"{range_note}{explanation}; USDA: {best['amount']:g} {best['description']} = {best['gram_weight']:g} g")
    return Grams(None, "unresolved", f"USDA gives no weight for a counted '{wanted_size or 'item'}'")
