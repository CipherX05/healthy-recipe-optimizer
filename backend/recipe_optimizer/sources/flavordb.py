"""FlavorDB2 importer.

FlavorDB2 documents no API or bulk download. The website itself is served by two
JSON addresses, which this module uses sparingly with caching:

  /entities?entity=<text>&category=   name search (returns a JSON-encoded string)
  /entities_json?id=<n>               one ingredient with its flavor molecules

They are undocumented, so they may change without notice.
"""
from __future__ import annotations

import json
import logging
import urllib.parse

from .. import config
from ..fetch import FetchError, fetch

log = logging.getLogger(__name__)

# Names are searched by substring, so four vowels reach practically every entity.
INDEX_QUERIES = ("a", "e", "i", "o")


def _decode(body: bytes):
    data = json.loads(body.decode("utf-8"))
    return json.loads(data) if isinstance(data, str) else data


def parse_index(bodies: list[bytes]) -> dict[str, int]:
    """Map case-folded entity name -> entity id."""
    index: dict[str, int] = {}
    for body in bodies:
        for entity in _decode(body):
            name = entity.get("entity_alias_readable")
            if name and entity.get("entity_id") is not None:
                index.setdefault(str(name).strip().casefold(), int(entity["entity_id"]))
    return index


def parse_entity(body: bytes) -> dict:
    data = _decode(body)
    molecules = {}
    for molecule in data.get("molecules", []):
        try:
            pubchem_id = int(molecule["pubchem_id"])
        except (KeyError, TypeError, ValueError):
            continue  # no identifier means it cannot take part in set similarity
        profile = str(molecule.get("flavor_profile") or "")
        molecules[pubchem_id] = {
            "pubchem_id": pubchem_id,
            "common_name": molecule.get("common_name") or "",
            "flavor_profile": "@".join(p for p in profile.split("@") if p and p != "None"),
        }
    return {
        "entity_id": int(data["entity_id"]),
        "name": str(data.get("entity_alias_readable") or ""),
        "category": str(data.get("category_readable") or ""),
        "molecules": list(molecules.values()),
    }


def load_index(*, offline: bool = False, refresh: bool = False) -> dict[str, int]:
    bodies = []
    for letter in INDEX_QUERIES:
        query = urllib.parse.urlencode({"entity": letter, "category": ""})
        bodies.append(fetch(f"{config.FLAVORDB_BASE}/entities?{query}", "flavordb",
                            suffix=".json", offline=offline, refresh=refresh))
    return parse_index(bodies)


def load_entity(entity_id: int, *, offline: bool = False, refresh: bool = False) -> dict:
    body = fetch(f"{config.FLAVORDB_BASE}/entities_json?id={int(entity_id)}", "flavordb",
                 suffix=".json", offline=offline, refresh=refresh)
    return parse_entity(body)


def load_named(names: list[str], *, offline: bool = False, refresh: bool = False) -> dict[str, dict]:
    """Fetch the entities with exactly these names. Missing ones are simply absent."""
    try:
        index = load_index(offline=offline, refresh=refresh)
    except (FetchError, ValueError) as error:
        log.error("FlavorDB2 is unavailable, so flavor scores will be missing: %s", error)
        return {}
    found: dict[str, dict] = {}
    failures = 0
    for name in sorted(set(names)):
        entity_id = index.get(name.casefold())
        if entity_id is None:
            log.warning("FlavorDB2 has no entity named %r", name)
            continue
        try:
            entity = load_entity(entity_id, offline=offline, refresh=refresh)
        except (FetchError, ValueError, KeyError) as error:
            log.error("FlavorDB2 entity %r failed: %s", name, error)
            failures += 1
            if failures >= 5:
                log.error("stopping FlavorDB2 requests after 5 failures")
                break
            continue
        if entity["name"].casefold() != name.casefold():
            log.warning("FlavorDB2 id %d returned %r, expected %r; skipped",
                        entity_id, entity["name"], name)
            continue
        if not entity["molecules"]:
            log.warning("FlavorDB2 entity %r lists no molecules", name)
        found[name] = entity
    return found
