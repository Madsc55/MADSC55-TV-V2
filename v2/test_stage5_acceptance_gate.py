#!/usr/bin/env python3
"""Offline Stage 5 gate regressions. No network, channel scans, or playlist edits."""
from stage5_acceptance_gate import REQUIRED, evaluate

def filled():
    tasks = {number: {field: "fixture-only" for field in fields}
             for number, fields in REQUIRED.items()}
    for number, fields in REQUIRED.items():
        for field in fields:
            if field.endswith("_url"):
                tasks[number][field] = "https://evidence.invalid/test"
    tasks["33"]["final_archive_sha256"] = "a" * 64
    tasks["31"]["discovery_batch_id"] = "new-batch-fixture"
    tasks["32"]["user_approval"] = True
    return {"tasks": tasks}

def main():
    empty = evaluate({"tasks": {}})
    assert not empty["all_accepted"]
    assert all(not item["accepted"] for item in empty["tasks"].values())
    valid_fixture = filled()
    assert evaluate(valid_fixture)["all_accepted"]
    without_av = filled()
    del without_av["tasks"]["31"]["real_av_evidence_url"]
    result = evaluate(without_av)
    assert not result["tasks"]["31"]["accepted"]
    assert not result["tasks"]["32"]["accepted"]
    assert not result["tasks"]["33"]["accepted"]
    legacy = filled()
    legacy["tasks"]["31"]["discovery_batch_id"] = "legacy"
    assert not evaluate(legacy)["all_accepted"]
    without_user = filled()
    without_user["tasks"]["32"]["user_approval"] = "fixture-only"
    assert not evaluate(without_user)["tasks"]["32"]["accepted"]
    without_restore = filled()
    del without_restore["tasks"]["33"]["final_restore_evidence_url"]
    assert not evaluate(without_restore)["tasks"]["33"]["accepted"]
    bad_url = filled()
    bad_url["tasks"]["31"]["real_av_evidence_url"] = "fixture-only"
    assert not evaluate(bad_url)["tasks"]["31"]["accepted"]
    bad_hash = filled()
    bad_hash["tasks"]["33"]["final_archive_sha256"] = "not-a-sha256"
    assert not evaluate(bad_hash)["tasks"]["33"]["accepted"]
    print("Stage 5 offline acceptance gate regressions: PASS (fixture only)")

if __name__ == "__main__":
    main()
