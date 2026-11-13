#!/usr/bin/env python3
"""Offline Stage 5 gate regressions. No network, channel scans, or playlist edits."""
from stage5_acceptance_gate import REQUIRED, evaluate
import json
import subprocess
import sys
import tempfile
from pathlib import Path

def filled():
    tasks = {number: {field: "fixture-only" for field in fields}
             for number, fields in REQUIRED.items()}
    for number, fields in REQUIRED.items():
        for field in fields:
            if field.endswith("_url"):
                tasks[number][field] = "https://github.com/example/fixture-only"
    tasks["33"]["final_archive_sha256"] = "a" * 64
    tasks["31"]["discovery_batch_id"] = "new-batch-fixture"
    tasks["32"]["user_approval"] = True
    tasks["31"]["real_world_checks_passed"] = True
    tasks["32"]["device_test_confirmed_by_user"] = True
    tasks["33"]["archive_restore_verified"] = True
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
    reserved_domain = filled()
    reserved_domain["tasks"]["31"]["real_av_evidence_url"] = "https://evidence.invalid/test"
    assert not evaluate(reserved_domain)["tasks"]["31"]["accepted"]
    bad_hash = filled()
    bad_hash["tasks"]["33"]["final_archive_sha256"] = "not-a-sha256"
    assert not evaluate(bad_hash)["tasks"]["33"]["accepted"]
    for number, flag in (("31", "real_world_checks_passed"),
                         ("32", "device_test_confirmed_by_user"),
                         ("33", "archive_restore_verified")):
        no_proof = filled()
        no_proof["tasks"][number][flag] = False
        assert not evaluate(no_proof)["tasks"][number]["accepted"]
    # External evidence links must not target private, reserved or malformed hosts.
    for url in ("https://127.0.0.1/proof", "https://192.168.1.1/proof",
                "https://169.254.169.254/latest/meta-data", "https://[::1]/proof",
                "https://host.internal/proof", "https://host.local/proof",
                "https://github.com:bad/proof", "https://github.com:99999/proof",
                "https://user:password@github.com/proof",
                "https://github.com/proof\\nforged"):
        invalid = filled()
        invalid["tasks"]["31"]["real_av_evidence_url"] = url
        assert not evaluate(invalid)["tasks"]["31"]["accepted"], url
    # Malformed JSON schemas must fail closed rather than being treated as accepted.
    for invalid_report in (None, [], {"tasks": []},
                           {"tasks": {"31": []}}, {"tasks": {"32": True}},
                           {"tasks": {"33": "invalid"}}):
        try:
            evaluate(invalid_report)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid acceptance JSON structure accepted")
    # CLI must preserve an existing acceptance artifact, even for valid fixtures.
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        evidence = root / "fixture.json"
        output = root / "protected-report.json"
        evidence.write_text(json.dumps(filled()), encoding="utf-8")
        output.write_bytes(b"DO_NOT_OVERWRITE_STAGE5_ACCEPTANCE")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("stage5_acceptance_gate.py")),
             "--evidence", str(evidence), "--output", str(output)],
            capture_output=True, text=True, timeout=30)
        assert result.returncode != 0
        assert output.read_bytes() == b"DO_NOT_OVERWRITE_STAGE5_ACCEPTANCE"
    print("Stage 5 offline acceptance gate regressions: PASS (fixture only)")

if __name__ == "__main__":
    main()
