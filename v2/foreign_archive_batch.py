"""Foreign archive bounded batches; never writes the canonical playlist."""
import argparse
import hashlib
import json
from pathlib import Path
from nonforeign_fresh_full import inventory, review, history_index
from yedekler_quality_review import get_quality_decoder
from yedekler_deep_review import PLAYLIST
from full_playlist_url_audit import write_json_atomic

BATCH_SIZE = 25
EXPECTED = 15940
def digest(data):
    return hashlib.sha256(data).hexdigest()

def identity(row):
    return tuple(row.get(k) for k in ("position", "record_sha256", "url_sha256"))

def batch(raw, number, path, probe, resume=None, expected=EXPECTED):
    rows = inventory(raw, "foreign")
    if len(rows) != expected or not 0 <= number < (len(rows)+BATCH_SIZE-1)//BATCH_SIZE:
        raise ValueError("Unexpected archive inventory or batch")
    selected = rows[number*BATCH_SIZE:(number+1)*BATCH_SIZE]
    doc = {"schema":1,"scope":"foreign","playlist_sha256":digest(raw),
           "batch":number,"expected":len(selected),"complete":False,"results":[]}
    if resume:
        old=json.loads(Path(resume).read_text())
        if any(old.get(k)!=doc[k] for k in ("schema","scope","playlist_sha256","batch","expected")):
            raise ValueError("Stale checkpoint")
        prior=old["results"]
        if len(prior)>len(selected) or [identity(x) for x in prior]!=[identity(x) for x in selected[:len(prior)]]:
            raise ValueError("Checkpoint coverage mismatch")
        if any(len(x.get("rounds",[]))!=3 for x in prior):
            raise ValueError("Incomplete checkpoint observation")
        doc["results"]=prior
    write_json_atomic(path,doc)
    for row in selected[len(doc["results"]):]:
        result=probe(row)
        if identity(result)!=identity(row) or len(result.get("rounds",[]))!=3 or "url" in result:
            raise ValueError("Invalid probe result")
        # No identity or language evidence is fabricated from metadata.
        result.update(language_review=[e["language_review"] for rnd in result["rounds"] for e in rnd.get("evidence",[]) if "language_review" in e], reorder_eligible=False)
        doc["results"].append(result)
        write_json_atomic(path,doc)
    doc["complete"]=True
    write_json_atomic(path,doc)
    return doc

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model-dir",type=Path,help="Verified local Whisper model directory")
    p.add_argument("--batch",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--resume",type=Path)
    p.add_argument("--history",type=Path,action="append",default=[])
    a=p.parse_args()
    raw=PLAYLIST.read_bytes()
    exe=get_quality_decoder()
    if not exe:
        raise RuntimeError("System FFmpeg required")
    history=history_index(a.history)
    from faster_whisper import WhisperModel
    from foreign_language_sample import sample
    model=WhisperModel(str(a.model_dir) if a.model_dir else "tiny",device="cpu",compute_type="int8",local_files_only=True)
    language_probe=lambda data,fmt:sample(data,fmt,exe,model)
    def probe(row):
        result=review(row,exe,history,language_probe)
        # Historical archive evidence may not cover this URL. Do not authorize red.
        result["red_eligible"]=False
        if result["classification"]=="CONFIRMED_UNAVAILABLE":
            result["classification"]="RECHECK_REQUIRED"
        return result
    batch(raw,a.batch,a.output,probe,a.resume)
    if PLAYLIST.read_bytes()!=raw:
        raise ValueError("Playlist changed")

if __name__=="__main__":
    main()
