"""Plan the next bounded group from exact-revision checkpoints."""
import argparse,json
from pathlib import Path
from foreign_archive_batch import EXPECTED,BATCH_SIZE,digest
from yedekler_deep_review import PLAYLIST

def next_group(root, revision):
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
    return missing[:20]

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(next_group(a.root,digest(PLAYLIST.read_bytes()))))
