"""Plan the next bounded group from exact-revision checkpoints."""
import argparse,json
from pathlib import Path
from foreign_archive_batch import EXPECTED,BATCH_SIZE,digest
from yedekler_deep_review import PLAYLIST

def pending_batches(root, revision):
    total=(EXPECTED+BATCH_SIZE-1)//BATCH_SIZE
    missing=[]
    for i in range(total):
        p=root/f"batch-{i}.json"
        if p.exists():
            x=json.loads(p.read_text())
            if x.get("playlist_sha256")!=revision or x.get("batch")!=i or x.get("scope")!="foreign":
                raise ValueError("Stale checkpoint")
            if x.get("complete") is True and len(x.get("results",[]))==min(BATCH_SIZE,EXPECTED-i*BATCH_SIZE):
                continue
        missing.append(i)
    return missing

def next_group(root, revision):
    return pending_batches(root, revision)[:20]

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--queue-output",type=Path)
    a=p.parse_args()
    revision=digest(PLAYLIST.read_bytes())
    pending=pending_batches(a.root,revision)
    if a.queue_output:
        from full_playlist_url_audit import write_json_atomic
        write_json_atomic(a.queue_output, {
            "playlist_sha256":revision,"records":EXPECTED,"batch_size":BATCH_SIZE,
            "total_batches":(EXPECTED+BATCH_SIZE-1)//BATCH_SIZE,
            "pending_batches":pending,"current_wave":pending[:20],"max_parallel":4})
    print(json.dumps(pending[:20]))
