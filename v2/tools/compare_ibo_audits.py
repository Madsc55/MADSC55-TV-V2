#!/usr/bin/env python3
"""Compare two completed read-only IBO channel audits, preserving every record."""
import csv,json,pathlib,collections
first=pathlib.Path("v2/archives/first_audit/channel_results.csv")
second=pathlib.Path("v2/archives/second_audit/channel_results.csv")
out=pathlib.Path("v2/archives/compared_audits_20261117")
out.mkdir(parents=True,exist_ok=True)
def load(path):
    with path.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
a,b=load(first),load(second)
assert len(a)==len(b)==18960,(len(a),len(b))
counts=collections.Counter()
with (out/"channel_comparison.csv").open("w",encoding="utf-8",newline="") as f:
    w=csv.writer(f)
    w.writerow(["position","category","name","url","first_result","first_evidence","second_result","second_evidence","assessment"])
    for old,new in zip(a,b):
        assert (old["position"],old["url"])==(new["position"],new["url"]),"Playlist changed between audits; aborting"
        x,y=old["result"],new["result"]
        assessment=("verified_twice" if x=="verified" and y=="verified" else
                    "recovered_second" if x!="verified" and y=="verified" else
                    "needs_retest_both" if x!="verified" and y!="verified" else
                    "temporarily_unverified_second")
        counts[assessment]+=1
        w.writerow([new["position"],new["category"],new["name"],new["url"],x,old["evidence"],y,new["evidence"],assessment])
summary={"total":len(a),"counts":dict(counts),"important":"Two unsuccessful network checks do not prove permanent stream failure. No playlist or main archive modified."}
(out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
