"""Weak supervision for a LoRA pilot. These labels are NOT expert ground truth."""
from __future__ import annotations
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "food_snapshot.json"
SYSTEM = (
    "Select one ingredient replacement from the supplied candidates. "
    "Only candidates with eligible=true may be selected. "
    "Among eligible candidates maximize 0.35*F+0.30*N+0.25*C+0.10*R. "
    "F is flavor similarity, N nutrition, C cuisine compatibility, R category compatibility. "
    "Return ONLY JSON with exactly one key candidate_id, containing a candidate id, "
    "or null when no candidate is eligible. These are illustrative rule scores."
)
EXCLUDED = {"pecorino"}  # Supplied per100g entry encodes a half portion. Await source audit.
CATEGORY = {
    "fat · dairy": {"fat · dairy": 1, "fat · plant": .75, "fat · fruit": .65, "dairy": .7},
    "dairy": {"dairy": 1, "plant cream": .8, "dairy · fermented": .85},
    "dairy · fermented": {"dairy · fermented": 1, "dairy": .85, "plant cream": .7},
    "cured meat": {"cured meat": 1, "vegetable · fungi": .55, "meat": .7},
    "meat": {"meat": 1, "meat · poultry": .85, "plant protein": .6, "legume": .55},
    "cheese · aged": {"cheese · aged": 1, "seasoning": .55},
    "sauce · emulsion": {"sauce · emulsion": 1},
    "grain · baked": {"grain · baked": 1, "legume": .6},
    "fat · infused": {"fat · infused": 1, "fat · plant": .7},
}

def read_snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))

def snapshot_hash():
    return hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()

def cosine(a, b):
    denom = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b)) / denom if denom else 0.0

def choose_teacher(candidates):
    eligible = [c for c in candidates if c["eligible"]]
    # Deterministic tie-breaking avoids order-dependent labels.
    return min(eligible, key=lambda c: (-c["score"], c["id"]))["id"] if eligible else None

def build_case(recipe_id, ingredient_id, goal_id, variant=0, seed=42):
    data = read_snapshot()
    recipe = next(r for r in data["recipes"] if r["id"] == recipe_id)
    item = next(i for i in recipe["items"] if i["ingredientId"] == ingredient_id and i.get("replaceable"))
    goal = next(g for g in data["goals"] if g["id"] == goal_id)
    orig = data["ingredients"][ingredient_id]
    original = orig["per100g"][goal_id]
    out = []
    for cid in item["replaceable"]:
        if cid in EXCLUDED:
            continue
        cand = data["ingredients"][cid]
        value = cand["per100g"][goal_id]
        change = (original-value) if goal["direction"] == "min" else (value-original)
        eligible = change > (original*.02 if original > 0 else 1e-9)
        # Explicit 1 g/kcal normalization floor avoids 1e-6 blow-ups for zero nutrients.
        raw = max(-20., min(20., change/max(abs(original),1.)))
        features = {
            "F": round(cosine(orig["flavor"],cand["flavor"]),4),
            "N": round(1/(1+math.exp(-3*raw)),4),
            "C": round(cand["cuisine"].get(recipe["cuisine"],.1),4),
            "R": round(CATEGORY.get(orig["category"],{}).get(cand["category"],.45),4),
        }
        score = sum(features[k]*w for k,w in {"F":.35,"N":.30,"C":.25,"R":.10}.items())
        out.append({"id":cid,"name":cand["name"],**features,"eligible":eligible,"score":score})
    target = choose_teacher(out)
    rng = random.Random(f"{seed}:{recipe_id}:{ingredient_id}:{goal_id}:{variant}")
    if variant:
        rng.shuffle(out)
    # Variants shuffle ordering only. They are NOT independent new recipes.
    payload = {"recipe":recipe["name"],"cuisine":recipe["cuisine"],
               "original":orig["name"],"grams":item["grams"],"goal":goal["label"],
               "candidates":[{k:v for k,v in c.items() if k!="score"} for c in out]}
    completion = json.dumps({"candidate_id":target},separators=(",",":"))
    return {"query_id":f"{recipe_id}/{ingredient_id}/{goal_id}","recipe_family":recipe_id,
            "recipe_id":recipe_id,"ingredient_id":ingredient_id,"goal_id":goal_id,
            "variant":variant,"messages":[{"role":"system","content":SYSTEM},
            {"role":"user","content":json.dumps(payload,separators=(",",":"))}],
            "completion":completion,"target":target,"candidates":out,
            "label_source":"fixed_rule_teacher_v2","review_status":"unreviewed",
            "teacher_policy":"fixed_weights_eligible_first_floor_1"}

def make_dataset(directory):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    family_split={"butter-chicken":"train","mapo-tofu":"train","caesar":"train",
                  "stroganoff":"validation","carbonara":"test"}
    rows={k:[] for k in ["train","validation","test"]}
    canonical=[]
    data=read_snapshot()
    for recipe in data["recipes"]:
        split=family_split[recipe["id"]]
        for item in recipe["items"]:
            if not item.get("replaceable"):continue
            for goal in data["goals"]:
                canonical.append(build_case(recipe["id"],item["ingredientId"],goal["id"]))
                for variant in range(8 if split=="train" else 3):
                    rows[split].append(build_case(recipe["id"],item["ingredientId"],goal["id"],variant))
    for split, records in rows.items():
        (directory/f"{split}.jsonl").write_text("".join(json.dumps(x)+"\n" for x in records),encoding="utf-8")
    (directory/"canonical.jsonl").write_text("".join(json.dumps(x)+"\n" for x in canonical),encoding="utf-8")
    manifest={"snapshot_sha256":snapshot_hash(),"label_source":"fixed_rule_teacher_v2",
              "review_status":"unreviewed","excluded_ingredients":sorted(EXCLUDED),
              "warning":"Rule agreement measures imitation, not taste quality or clinical benefit.",
              "splits":{s:{"records":len(rs),"independent_queries":len({x['query_id'] for x in rs}),
                            "recipe_families":sorted({x['recipe_family'] for x in rs})} for s,rs in rows.items()}}
    (directory/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def parse_selection(raw, candidates):
    """Strict output validation, with no silent 'repair' in reported model metrics."""
    try:
        obj=json.loads(raw.strip())
    except (ValueError,TypeError):
        return {"json_valid":False,"candidate_valid":False,"eligible":False,"selected":None}
    exact=isinstance(obj,dict) and set(obj)=={"candidate_id"}
    value=obj.get("candidate_id") if isinstance(obj,dict) else None
    allowed={c["id"]:c for c in candidates}
    valid=exact and (value is None or (isinstance(value,str) and value in allowed))
    eligible=valid and (choose_teacher(candidates) is None if value is None else allowed[value]["eligible"])
    return {"json_valid":exact,"candidate_valid":valid,"eligible":eligible,"selected":value}

def summarize(predictions):
    n=len(predictions)
    return {"records":n,"independent_queries":len({p["query_id"] for p in predictions}),
            "recipe_families":sorted({p["recipe_family"] for p in predictions}),
            "json_valid_rate":sum(p["json_valid"] for p in predictions)/n if n else None,
            "candidate_valid_rate":sum(p["candidate_valid"] for p in predictions)/n if n else None,
            "eligible_rate":sum(p["eligible"] for p in predictions)/n if n else None,
            "rule_agreement":sum(p["candidate_valid"] and p["selected"]==p["target"] for p in predictions)/n if n else None,
            "interpretation":"Agreement with unreviewed rules, not independently validated suitability."}

if __name__=="__main__":
    print(json.dumps(make_dataset(ROOT/"data"),indent=2))
