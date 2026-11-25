"""Train real LoRA weights and record raw base/adapter metrics. Run on a Colab GPU."""
from __future__ import annotations
import os
os.environ.setdefault("USE_TF","0")
os.environ.setdefault("USE_FLAX","0")
import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import random
import time
from datetime import datetime, timezone
from contextlib import nullcontext
from pathlib import Path
import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup
from policy import ROOT, make_dataset, read_jsonl, parse_selection, summarize, choose_teacher, snapshot_hash

BASE_MODEL="Qwen/Qwen2.5-0.5B-Instruct"

class Examples(Dataset):
    def __init__(self,records,tokenizer,max_length):
        self.examples=[]
        for record in records:
            prefix=tokenizer.apply_chat_template(record["messages"],tokenize=False,add_generation_prompt=True)
            p=tokenizer.encode(prefix,add_special_tokens=False)
            answer=tokenizer.encode(record["completion"]+tokenizer.eos_token,add_special_tokens=False)
            if len(p)+len(answer)>max_length:
                raise ValueError(f"{record['query_id']} needs {len(p)+len(answer)} tokens. Increase max_length; do not truncate its answer.")
            self.examples.append({"input_ids":p+answer,"labels":[-100]*len(p)+answer})
    def __len__(self):return len(self.examples)
    def __getitem__(self,i):return self.examples[i]

def collator(tokenizer):
    def collate(rows):
        size=max(len(r["input_ids"]) for r in rows)
        return {"input_ids":torch.tensor([r["input_ids"]+[tokenizer.pad_token_id]*(size-len(r["input_ids"])) for r in rows]),
                "attention_mask":torch.tensor([[1]*len(r["input_ids"])+[0]*(size-len(r["input_ids"])) for r in rows]),
                "labels":torch.tensor([r["labels"]+[-100]*(size-len(r["labels"])) for r in rows])}
    return collate

def move(batch,device):return {k:v.to(device) for k,v in batch.items()}

@torch.inference_mode()
def loss_on(model,loader,device):
    model.eval()
    weighted=0.;tokens=0
    for batch in loader:
        batch=move(batch,device)
        n=int((batch["labels"]!=-100).sum())
        loss=float(model(**batch).loss)
        if not math.isfinite(loss):raise RuntimeError("Nonfinite evaluation loss")
        weighted+=loss*n;tokens+=n
    return weighted/max(tokens,1)

@torch.inference_mode()
def generate(model,tokenizer,record,device):
    inputs=tokenizer.apply_chat_template(record["messages"],add_generation_prompt=True,tokenize=True,
                                        return_tensors="pt",return_dict=True)
    inputs={k:v.to(device) for k,v in inputs.items()}
    ids=model.generate(**inputs,max_new_tokens=40,do_sample=False,
                       pad_token_id=tokenizer.pad_token_id,eos_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(ids[0,inputs["input_ids"].shape[-1]:],skip_special_tokens=True).strip()

def prediction(model,tokenizer,record,device):
    start=time.perf_counter()
    raw=generate(model,tokenizer,record,device)
    return {"query_id":record["query_id"],"recipe_family":record["recipe_family"],
            "variant":record["variant"],"target":record["target"],"raw_output":raw,
            "latency_seconds":time.perf_counter()-start,**parse_selection(raw,record["candidates"])}

def train(args):
    if not torch.cuda.is_available() and not args.allow_cpu:
        raise RuntimeError("Select Runtime > Change runtime type > T4 GPU in Colab, reconnect and run again.")
    device="cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed);random.seed(args.seed)
    if device=="cuda":torch.cuda.manual_seed_all(args.seed)
    args.output.mkdir(parents=True,exist_ok=True)
    if not (args.data/"train.jsonl").exists():make_dataset(args.data)
    records={s:read_jsonl(args.data/f"{s}.jsonl") for s in ["train","validation","test"]}
    families={s:{x["recipe_family"] for x in rs} for s,rs in records.items()}
    assert families["train"].isdisjoint(families["validation"])
    assert families["train"].isdisjoint(families["test"])
    assert families["validation"].isdisjoint(families["test"])
    dtype=(torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16) if device=="cuda" else torch.float32
    tokenizer=AutoTokenizer.from_pretrained(args.model,revision=args.revision)
    tokenizer.pad_token=tokenizer.eos_token
    tokenizer.padding_side="right"
    base=AutoModelForCausalLM.from_pretrained(args.model,revision=args.revision,
                 torch_dtype=dtype,attn_implementation="sdpa").to(device)
    revision=getattr(base.config,"_commit_hash",None)
    config=LoraConfig(task_type=TaskType.CAUSAL_LM,r=8,lora_alpha=16,lora_dropout=.05,
                      target_modules=["q_proj","v_proj"],bias="none")
    model=get_peft_model(base,config)
    model.config.use_cache=False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant":False})
    trainable={n:p for n,p in model.named_parameters() if p.requires_grad}
    assert trainable and all("lora_" in n for n in trainable), "Only LoRA weights should train"
    start_weights={n:p.detach().float().cpu().clone() for n,p in trainable.items()}
    model.print_trainable_parameters()
    loaders={s:DataLoader(Examples(rs,tokenizer,args.max_length),batch_size=args.batch_size,
                         shuffle=(s=="train"),collate_fn=collator(tokenizer)) for s,rs in records.items()}
    initial_val=loss_on(model,loaders["validation"],device)
    optimizer=torch.optim.AdamW(trainable.values(),lr=args.lr,weight_decay=.01)
    updates=args.epochs*math.ceil(len(loaders["train"])/args.accumulation)
    scheduler=get_linear_schedule_with_warmup(optimizer,max(1,int(updates*.1)),updates)
    scaler=torch.amp.GradScaler("cuda",enabled=(device=="cuda" and dtype==torch.float16))
    logs=[];step=0;best_val=float("inf");best_weights=None;started=time.time()
    validation=[{"epoch":0,"completion_loss":initial_val}]
    for epoch in range(args.epochs):
        model.train();optimizer.zero_grad(set_to_none=True);running=0.;batches=0
        for index,batch in enumerate(loaders["train"]):
            # Last accumulation window may contain fewer batches.
            window_start=(index//args.accumulation)*args.accumulation
            window_size=min(args.accumulation,len(loaders["train"])-window_start)
            ctx=torch.autocast(device_type="cuda",dtype=dtype) if device=="cuda" else nullcontext()
            with ctx:loss=model(**move(batch,device)).loss
            if not torch.isfinite(loss):raise RuntimeError("Nonfinite training loss. Lower LR or use bf16-capable GPU.")
            scaler.scale(loss/window_size).backward()
            running+=float(loss.detach());batches+=1
            if (index+1)%args.accumulation==0 or index+1==len(loaders["train"]):
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable.values(),1.)
                previous_scale=scaler.get_scale()
                scaler.step(optimizer);scaler.update()
                updated=scaler.get_scale()>=previous_scale
                if updated:scheduler.step();step+=1
                optimizer.zero_grad(set_to_none=True)
                log={"optimizer_step":step,"epoch":epoch+1,"completion_loss":running/batches,
                     "lr":optimizer.param_groups[0]["lr"],"update_applied":updated}
                logs.append(log);print(json.dumps(log),flush=True);running=0.;batches=0
        val=loss_on(model,loaders["validation"],device)
        validation.append({"epoch":epoch+1,"completion_loss":val})
        print("VALIDATION",validation[-1],flush=True)
        if val<best_val:
            best_val=val;best_weights={n:p.detach().float().cpu().clone() for n,p in trainable.items()}
    with torch.no_grad():
        for n,p in trainable.items():p.copy_(best_weights[n].to(device=p.device,dtype=p.dtype))
    change=math.sqrt(sum(float(((p.detach().float().cpu()-start_weights[n])**2).sum()) for n,p in trainable.items()))
    if not step or not math.isfinite(change) or change<=0:raise RuntimeError("No confirmed LoRA update. Do not report a completed fine-tune.")
    adapter=args.output/"adapter"
    model.save_pretrained(adapter,safe_serialization=True);tokenizer.save_pretrained(adapter)
    model.gradient_checkpointing_disable();model.config.use_cache=True;model.eval()
    with (args.output/"training_loss.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(logs[0]));writer.writeheader();writer.writerows(logs)
    (args.output/"validation_loss.json").write_text(json.dumps(validation,indent=2))
    manifest={"training_completed":True,"base_model":args.model,"base_revision":revision,
              "completed_at_utc":datetime.now(timezone.utc).isoformat(),
              "training_code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "adapter_weights_sha256":hashlib.sha256((adapter/"adapter_model.safetensors").read_bytes()).hexdigest(),
              "seed":args.seed,"epochs":args.epochs,"optimizer_steps":step,
              "learning_rate":args.lr,"lora_rank":8,"lora_alpha":16,"target_modules":["q_proj","v_proj"],
              "trainable_parameters":sum(p.numel() for p in trainable.values()),
              "total_parameters":sum(p.numel() for p in model.parameters()),
              "adapter_weight_l2_change":change,"snapshot_sha256":snapshot_hash(),
              "data_file_sha256":{s:hashlib.sha256((args.data/f"{s}.jsonl").read_bytes()).hexdigest() for s in records},
              "split_counts":{s:{"records":len(rs),"queries":len({x['query_id'] for x in rs}),"families":sorted(families[s])} for s,rs in records.items()},
              "label_sources":sorted({x.get("label_source","unknown") for rs in records.values() for x in rs}),
              "label_review_status":sorted({x.get("review_status","unknown") for rs in records.values() for x in rs}),
              "initial_validation_completion_loss":initial_val,"best_validation_completion_loss":best_val,
              "training_seconds":time.time()-started,"device":torch.cuda.get_device_name(0) if device=="cuda" else "CPU",
              "versions":{p:importlib.metadata.version(p) for p in ["torch","transformers","peft","accelerate"]},
              "interpretation":"Weakly supervised rule imitation. No independent flavor or suitability accuracy claimed."}
    (adapter/"training_manifest.json").write_text(json.dumps(manifest,indent=2))
    if args.skip_generation:
        print("Saved trained adapter. Generation evaluation explicitly skipped.")
        return
    comparisons={};predictions={}
    for mode in ["base","lora"]:
        context=model.disable_adapter() if mode=="base" else nullcontext()
        with context:
            predictions[mode]=[prediction(model,tokenizer,r,device) for r in records["test"]]
        comparisons[mode]=summarize(predictions[mode])
    (args.output/"evaluation.json").write_text(json.dumps(comparisons,indent=2))
    (args.output/"raw_test_predictions.json").write_text(json.dumps(predictions,indent=2))
    canonical=read_jsonl(args.data/"canonical.jsonl")
    cache={"recorded":True,"training":manifest,"test_metrics":comparisons,"cases":{}}
    for record in canonical:
        entry={"split":next(s for s,fs in families.items() if record["recipe_family"] in fs),
               "rule_baseline":record["target"],"modes":{}}
        for mode in ["base","lora"]:
            ctx=model.disable_adapter() if mode=="base" else nullcontext()
            with ctx:pred=prediction(model,tokenizer,record,device)
            accepted=pred["candidate_valid"] and pred["eligible"]
            selected=pred["selected"] if accepted else choose_teacher(record["candidates"])
            entry["modes"][mode]={**pred,"recommendation_id":selected,"used_fallback":not accepted}
        cache["cases"][record["query_id"]]=entry
    (args.output/"lora-demo.json").write_text(json.dumps(cache,indent=2))
    print("ACTUAL HELD-OUT METRICS",json.dumps(comparisons,indent=2),flush=True)
    print("Copy lora-demo.json to app/public/. This is a recorded-output demo, not live inference.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--model",default=BASE_MODEL);p.add_argument("--revision",default=None)
    p.add_argument("--data",type=Path,default=ROOT/"data");p.add_argument("--output",type=Path,default=ROOT/"output")
    p.add_argument("--epochs",type=int,default=3);p.add_argument("--max-length",type=int,default=1024)
    p.add_argument("--batch-size",type=int,default=1);p.add_argument("--accumulation",type=int,default=8)
    p.add_argument("--lr",type=float,default=2e-4);p.add_argument("--seed",type=int,default=42)
    p.add_argument("--allow-cpu",action="store_true");p.add_argument("--skip-generation",action="store_true")
    args=p.parse_args()
    if min(args.epochs,args.batch_size,args.accumulation,args.max_length)<1:p.error("Epochs and sizes must be positive")
    train(args)
