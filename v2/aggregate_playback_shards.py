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
    per_source_shard = {}
    per_source_fingerprint = {}
    total_sampled = 0
    page_source_sets = {}
    for path in files:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        idx = (int(doc.get("page", 0)), int(doc.get("shard_index", -1)))
        if idx[1] < 0:
            raise SystemExit("Missing shard_index in "+path)
        if idx in shard_ids:
            raise SystemExit("Duplicate shard index: "+str(idx))
        shard_ids.add(idx)
        total_sampled += doc.get("sampled", 0)
        page_source_sets[idx] = {item["source"] for item in doc.get("sources", [])}
        if len(page_source_sets[idx]) != len(doc.get("sources", [])):
            raise SystemExit("Duplicate source IDs in batch: " + str(idx))
        for item in doc.get("results", []):
            key = item.get("url_sha256")
            if key:
                results.setdefault(key, item)
        for source in doc.get("sources", []):
            sid = source["source"]
            stat = source_stats.setdefault(sid, {"source":sid, "shard_candidates":0, "sampled":0, "fetch_failures":0})
            # Every page repeats the same shard candidate count; count it only once.
            shard_key = (sid, idx[1])
            previous = per_source_shard.get(shard_key)
            count = source.get("shard_candidates", 0)
            fingerprint = source.get("shard_fingerprint")
            if not fingerprint and source.get("status") != "FETCH_FAILED":
                raise SystemExit("Missing source inventory fingerprint: " + sid)
            if shard_key in per_source_fingerprint and per_source_fingerprint[shard_key] != fingerprint:
                raise SystemExit("Source content drift between pages: " + sid + " shard " + str(idx[1]))
            per_source_fingerprint[shard_key] = fingerprint
            if previous is not None and previous != count:
                raise SystemExit("Source snapshot drift between pages: " + sid + " shard " + str(idx[1]))
            if previous is None:
                per_source_shard[shard_key] = count
                stat["shard_candidates"] += count
            stat["sampled"] += source.get("sampled", 0)
            stat["fetch_failures"] += int(source.get("status") == "FETCH_FAILED")
    expected = {(page, shard) for page in range(2) for shard in range(4)}
    missing = expected - shard_ids
    unexpected = shard_ids - expected
    if missing or unexpected:
        raise SystemExit("Incomplete playback evidence; missing="+str(sorted(missing))+" unexpected="+str(sorted(unexpected)))
    for shard in range(4):
        if page_source_sets[(0, shard)] != page_source_sets[(1, shard)]:
            raise SystemExit("Source set changed between pages for shard " + str(shard))
    incomplete_sources = [x["source"] for x in source_stats.values() if x["fetch_failures"] or x["sampled"] != x["shard_candidates"]]
    # Each sampled stream must have exactly one distinct URL hash and a probe result.
    if total_sampled != len(results):
        raise SystemExit("Duplicate or missing playback evidence: sampled=" + str(total_sampled) + " unique=" + str(len(results)))
    if any(not item.get("status") or not item.get("attempts") for item in results.values()):
        raise SystemExit("Playback result missing status or attempt evidence")
    verified = sum(x.get("status") == "VIDEO_DECODED" for x in results.values())
    report = {"policy":"READ_ONLY_SHARDED_EVIDENCE_NOT_COMPLETE_VALIDATION",
        "batches_present":[{"page":p,"shard":s} for p,s in sorted(shard_ids)], "unique_tested":len(results),
        "video_decoded":verified, "not_video_decoded":len(results)-verified,
        "reported_sampled":total_sampled,
        "coverage_complete":not incomplete_sources,
        "incomplete_sources":sorted(incomplete_sources),
        "channel_results":[{"name":item.get("name"),"source":item.get("source"),"url_sha256":item.get("url_sha256"),"playback":item.get("status"),"audio":item.get("audio"),"video_width":item.get("width"),"video_height":item.get("height"),"attempts":item.get("attempts"),"classification":"PENDING_REVIEW" if item.get("status") == "VIDEO_DECODED" else "REJECTED_PLAYBACK"} for item in sorted(results.values(),key=lambda item:(item.get("source",""),item.get("name",""),item.get("url_sha256","")))],
        "source_coverage":sorted(source_stats.values(),key=lambda x:x["source"]),
        "notes":"A decoded video is not proof of correct channel identity, audio, stability, EPG or logo."}
    out = Path("v2/reports/all-source-playback-aggregate.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Shards:",len(shard_ids),"unique tested:",len(results),"video decoded:",verified,"incomplete sources:",len(incomplete_sources))

if __name__ == "__main__":
    main()
