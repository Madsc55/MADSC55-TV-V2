#!/usr/bin/env python3
"""Convert existing aggregate playback results to smart-archive evidence maps.

Fail closed: matching identity set required, no URL or metadata promoted to AV proof.
"""
import json
import hashlib
from pathlib import Path

def convert(inventory, aggregate):
    candidates=inventory.get("channels") if isinstance(inventory,dict) else None
    rows=aggregate.get("channel_results") if isinstance(aggregate,dict) else None
    if not isinstance(candidates,list) or not isinstance(rows,list):
        raise ValueError("Expected inventory channels and playback channel_results")
    if aggregate.get("coverage_complete") is not True:
        raise ValueError("Playback coverage incomplete")
    ids=[r.get("url_sha256") for r in candidates if isinstance(r,dict)]
    if len(ids)!=len(candidates) or any(not isinstance(k,str) or len(k)!=64 or any(ch not in "0123456789abcdef" for ch in k) for k in ids):
        raise ValueError("Invalid inventory identity")
    if len(ids)!=len(set(ids)):
        raise ValueError("Invalid or duplicate inventory IDs")
    results={}
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Invalid playback row")
        key=row.get("url_sha256")
        if not isinstance(key,str) or len(key)!=64 or any(ch not in "0123456789abcdef" for ch in key) or key in results:
            raise ValueError("Invalid or duplicate playback identity")
        # Existing aggregate reports alone do not attest decoded AV; require
        # an explicit independently verified decode flag to promote status.
        results[key]={
            "playback":row.get("playback"),
            "status":row.get("status"),
            "decode_status":row.get("decode_status"),
            "audio":row.get("audio"),
            "decoded_av_verified":row.get("decoded_av_verified") is True,
            "retries_exhausted":row.get("retries_exhausted") is True,
            "terminal_failure_verified":row.get("terminal_failure_verified") is True,
        }
    if set(ids)!=set(results):
        raise ValueError("Inventory and playback identity sets differ")
    return {"policy":"READ_ONLY_NO_AUTO_PROMOTION","by_url_sha256":results}

def run(inventory_path, aggregate_path, output_path):
    if output_path.exists() or output_path.resolve() in (inventory_path.resolve(),aggregate_path.resolve()):
        raise ValueError("Refusing to overwrite evidence")
    inventory=json.loads(inventory_path.read_text(encoding="utf-8"))
    aggregate=json.loads(aggregate_path.read_text(encoding="utf-8"))
    report=convert(inventory,aggregate)
    report["provenance"] = {"inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
                            "aggregate_sha256": hashlib.sha256(aggregate_path.read_bytes()).hexdigest()}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    return {"total":len(report["by_url_sha256"])}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--inventory",required=True,type=Path)
    p.add_argument("--aggregate",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(run(a.inventory,a.aggregate,a.output)))
if __name__=="__main__":
    main()
