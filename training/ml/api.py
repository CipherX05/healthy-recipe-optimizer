"""Optional live local inference. Recorded outputs also work without this server."""
import os
os.environ.setdefault("USE_TF","0")
os.environ.setdefault("USE_FLAX","0")
import json
import threading
from contextlib import nullcontext
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from policy import ROOT, build_case, choose_teacher, parse_selection, snapshot_hash

app=FastAPI(title="CGAS LoRA Pilot")
app.add_middleware(CORSMiddleware,allow_origins=[
    f"http://{host}:{port}" for host in ["localhost","127.0.0.1"] for port in [3000,4173,5173]
],allow_methods=["GET","POST"],allow_headers=["Content-Type"])
ADAPTER=Path(os.environ.get("CGAS_ADAPTER_PATH",str(ROOT/"output"/"adapter")))
lock=threading.Lock()
runtime=None

class Request(BaseModel):
    recipe_id:str=Field(max_length=80)
    ingredient_id:str=Field(max_length=80)
    goal_id:Literal["satFat","calories","protein","fiber"]
    mode:Literal["base","lora"]="lora"

def load():
    global runtime
    if runtime is not None:return runtime
    manifest_path=ADAPTER/"training_manifest.json"
    if not manifest_path.exists():raise HTTPException(503,"Trained adapter missing. Run the notebook and copy its adapter folder to ml/output/adapter.")
    manifest=json.loads(manifest_path.read_text())
    if not manifest.get("training_completed") or manifest.get("adapter_weight_l2_change",0)<=0:
        raise HTTPException(503,"No confirmed LoRA update in the supplied training manifest.")
    if manifest.get("snapshot_sha256")!=snapshot_hash():
        raise HTTPException(409,"Ingredient snapshot differs from the training run. Use matching files or retrain.")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    from train_lora import generate
    device="cuda" if torch.cuda.is_available() else "cpu"
    dtype=torch.float16 if device=="cuda" else torch.float32
    base=AutoModelForCausalLM.from_pretrained(manifest["base_model"],revision=manifest.get("base_revision"),
                                           torch_dtype=dtype,attn_implementation="sdpa").to(device)
    model=PeftModel.from_pretrained(base,ADAPTER,is_trainable=False)
    model.eval()
    tokenizer=AutoTokenizer.from_pretrained(ADAPTER)
    runtime=(model,tokenizer,device,manifest,generate)
    return runtime

@app.get("/health")
def health():
    return {"adapter_present":(ADAPTER/"training_manifest.json").exists(),"model_loaded":runtime is not None}

@app.post("/recommend")
def recommend(request:Request):
    try:case=build_case(request.recipe_id,request.ingredient_id,request.goal_id)
    except (ValueError,StopIteration,KeyError):raise HTTPException(400,"Unknown recipe, replaceable ingredient or goal.")
    # Adapter enable/disable is model state. Serialize calls to preserve base/LoRA isolation.
    with lock:
        model,tokenizer,device,manifest,generate=load()
        context=model.disable_adapter() if request.mode=="base" else nullcontext()
        with context:raw=generate(model,tokenizer,case,device)
    status=parse_selection(raw,case["candidates"])
    accepted=status["candidate_valid"] and status["eligible"]
    return {"recorded":False,"mode":request.mode,"raw_output":raw,
            "rule_baseline":case["target"],"raw_model_candidate":status["selected"],
            "recommendation_id":status["selected"] if accepted else choose_teacher(case["candidates"]),
            "used_fallback":not accepted,"training":manifest,**status}
