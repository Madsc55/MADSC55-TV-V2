#!/usr/bin/env python3
"""Merge playback shard evidence without leaking stream URLs."""
import glob
import json
from pathlib import Path

def main():
    files = sorted(glob.glob("v2/reports/shards/**/all-source-playback.json", recursive=True))
    if not files:
        raise SystemExit("No shard evidence found")
    results, source_stats, shard_ids = {}, {}, set()
    total_sampled = 0
    for path in files:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        idx = (int(doc.get("page", 0)), int(doc.get("shard_index", -1)))
        if idx[1] < 0:
            raise SystemExit("Missing shard_index in "+path)
        if idx in shard_ids:
            raise SystemExit("Duplicate shard index: "+str(idx))
        shard_ids.add(idx)
        total_sampled += doc.get("sampled", 0)
        for item in doc.get("results", []):
            key = item.get("url_sha256")
            if key:
                results.setdefault(key, item)
        for source in doc.get("sources", []):
            sid = source["source"]
            stat = source_stats.setdefault(sid, {"source":sid, "shard_candidates":0, "sampled":0, "fetch_failures":0})
            stat["shard_candidates"] += source.get("shard_candidates", 0)
            stat["sampled"] += source.get("sampled", 0)
            stat["fetch_failures"] += int(source.get("status") == "FETCH_FAILED")
    expected = {(page, shard) for page in range(2) for shard in range(4)}
    missing = expected - shard_ids
    unexpected = shard_ids - expected
    if missing or unexpected:
        raise SystemExit("Incomplete playback evidence; missing="+str(sorted(missing))+" unexpected="+str(sorted(unexpected)))
    verified = sum(x.get("status") == "VIDEO_DECODED" for x in results.values())
    report = {"policy":"READ_ONLY_SHARDED_EVIDENCE_NOT_COMPLETE_VALIDATION",
        "batches_present":[{"page":p,"shard":s} for p,s in sorted(shard_ids)], "unique_tested":len(results),
        "video_decoded":verified, "not_video_decoded":len(results)-verified,
        "reported_sampled":total_sampled,
        "source_coverage":sorted(source_stats.values(),key=lambda x:x["source"]),
        "notes":"A decoded video is not proof of correct channel identity, audio, stability, EPG or logo."}
    out = Path("v2/reports/all-source-playback-aggregate.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Shards:",len(shard_ids),"unique tested:",len(results),"video decoded:",verified)

if __name__ == "__main__":
    main()
