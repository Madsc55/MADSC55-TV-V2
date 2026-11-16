#!/usr/bin/env python3
"""Fail-closed checked-in main Actions audit. Does not verify server rulesets."""
from pathlib import Path
import hashlib
import json
import re
import yaml

ROOT=Path(__file__).resolve().parents[1]
WORKFLOWS=ROOT/".github/workflows"
EXPECTED_BLOB="165c726cd9211f9f51c31f1c718e0911bab79e1b"
ORIGINAL_FILES=frozenset("""
alphabetize-yeni-turk.yml backups-logo-audit.yml full-turkish-backups-audit.yml
ibo-real-scan.yml import-backup-candidates.yml move-turkish-backups.yml
repair-playlist-grouping.yml sort-backups-enrich-logos.yml
turkish-backup-identity-audit.yml turkish-backups-fifth-audit.yml
turkish-backups-fourth-audit.yml turkish-backups-second-pass.yml
turkish-backups-third-pass.yml turkish-category-audit.yml
v2-batched-playback.yml v2-bruksel-logo-png.yml v2-epg.yml
v2-full-decoder.yml v2-github-source-discovery.yml v2-historical-recovery.yml
v2-ibo-parity.yml v2-logo-backup.yml v2-official-sites.yml
v2-offline-inventory.yml v2-one-shot-final-contract.yml
v2-ordered-preflight.yml v2-playlist-safety.yml v2-postscan-triage.yml
v2-promote-yedekler.yml v2-public-source-audit.yml
v2-real-iptv-scan.yml v2-spoken-language-existing-snapshot.yml
v2-turkish-stream-catalog.yml v2-turkish-stream-decode.yml
v2-turkish-stream-probe.yml v2-turkish-stream-review.yml
v2-turkish-tv-health.yml v2-world-discovery.yml
v2-yedekler-logos.yml v2-youtube-discovery.yml
""".split())
WRITER_SUSPENDED=frozenset("""
alphabetize-yeni-turk.yml backups-logo-audit.yml full-turkish-backups-audit.yml
ibo-real-scan.yml import-backup-candidates.yml move-turkish-backups.yml
repair-playlist-grouping.yml sort-backups-enrich-logos.yml
turkish-backup-identity-audit.yml turkish-backups-fifth-audit.yml
turkish-backups-fourth-audit.yml turkish-backups-second-pass.yml
turkish-backups-third-pass.yml turkish-category-audit.yml
v2-bruksel-logo-png.yml v2-epg.yml v2-logo-backup.yml
v2-promote-yedekler.yml v2-yedekler-logos.yml
""".split())
GATE="v2-main-production-safety-gate.yml"
SAFETY="v2-playlist-safety.yml"
STAGING="madsc/v2-production-actions-lock-20261103"
MUTATION=re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(?:push|add|commit)\b", re.I)
PERSISTED=re.compile(r"persist-credentials\s*:\s*(?:true|yes)\b",re.I)

def mapping(v):
    return v if isinstance(v,dict) else {}

def audit_one(filename,source):
    problems=[]
    if not isinstance(source,str) or len(source)>200000:
        return ["NON_TEXT_OR_OVERSIZED"]
    try:
        doc=yaml.load(source,Loader=yaml.BaseLoader)
    except yaml.YAMLError:
        return ["UNPARSEABLE_YAML"]
    if not isinstance(doc,dict):
        return ["INVALID_WORKFLOW"]
    events=mapping(doc.get("on"))
    if filename=="ibo-authorized-500.yml":
        if set(events)!={"push","workflow_dispatch"} or mapping(events.get("push")).get("branches")!=["main"] or mapping(events.get("push")).get("paths")!=[".github/workflows/ibo-authorized-500.yml"]:
            return ["ONE_TIME_TRIGGER_CHANGED"]
        if mapping(doc.get("permissions"))!={"contents":"write","pull-requests":"write"}:
            return ["ONE_TIME_PERMISSIONS_CHANGED"]
        if set(mapping(doc.get("jobs")))!={"import"}:
            return ["ONE_TIME_JOB_CHANGED"]
        if ("14136864383" not in source or "python3 v2/import_every_archive_both_systems.py --old-repo /tmp/old-madsc-tv --scan-dir /tmp/all-scan" not in source or "python3 v2/test_playlist_invariants.py" not in source or "v2/ibo_authorized_change.json" not in source):
            return ["ONE_TIME_IMPORT_INVARIANTS_CHANGED"]
        return []
    allowed=({"push","pull_request","workflow_dispatch"} if filename==GATE else
             {"push","workflow_dispatch"} if filename==SAFETY else
             {"workflow_dispatch"})
    if set(events)!=allowed:
        problems.append("UNAPPROVED_TRIGGER")
    if any(e in events for e in ("schedule","pull_request_target","workflow_run","repository_dispatch")):
        problems.append("UNTRUSTED_AUTOMATIC_EVENT")
    if "push" in events:
        cfg=mapping(events["push"])
        if filename==GATE:
            if set(cfg.get("branches",[]))!={"main",STAGING}:
                problems.append("MAIN_GATE_WRONG_PUSH_BRANCHES")
        elif filename==SAFETY:
            if "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8" not in set(cfg.get("paths",[])):
                problems.append("PLAYLIST_SAFETY_MISSING_PATH")
        else:
            problems.append("UNAPPROVED_PUSH")
    if "pull_request" in events:
        if filename!=GATE or set(mapping(events["pull_request"]).get("branches",[]))!={"main"}:
            problems.append("UNAPPROVED_PR_TRIGGER")
    perms=mapping(doc.get("permissions"))
    if perms.get("contents")!="read":
        problems.append("DEFAULT_CONTENTS_NOT_READ_ONLY")
    if any(value=="write" for value in perms.values()):
        problems.append("WORKFLOW_HAS_WRITE_PERMISSION")
    jobs=mapping(doc.get("jobs"))
    if not jobs:
        problems.append("NO_JOBS")
    for job in jobs.values():
        if not isinstance(job,dict):
            problems.append("INVALID_JOB")
            continue
        if any(v=="write" for v in mapping(job.get("permissions")).values()):
            problems.append("JOB_HAS_WRITE_PERMISSION")
    if MUTATION.search(source):
        problems.append("GIT_MUTATION_COMMAND")
    if PERSISTED.search(source):
        problems.append("PERSISTED_CHECKOUT_WRITE_CREDENTIALS")
    if filename in WRITER_SUSPENDED:
        if set(jobs)!={"protected-read-only-check"}:
            problems.append("ORIGINAL_PRODUCTION_WRITER_REENABLED")
        if "production writer suspended" not in str(doc.get("name","")).lower():
            problems.append("PRODUCTION_WRITER_NOT_MARKED_SUSPENDED")
    return problems

def audit(root=ROOT):
    root=Path(root)
    folder=root/".github/workflows"
    found={p.name for p in folder.iterdir() if p.is_file() and p.suffix in (".yml",".yaml")}
    expected=ORIGINAL_FILES|{GATE,"v2-stage6-grouped-acceptance.yml","ibo-authorized-500.yml"}
    errors={}
    if found!=expected:
        errors["WORKFLOW_INVENTORY"]={"missing":sorted(expected-found),
                                      "unexpected":sorted(found-expected)}
    for name in sorted(found&expected):
        issues=audit_one(name,(folder/name).read_text(encoding="utf-8"))
        if issues:
            errors[name]=issues
    path=root/"MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
    if not path.is_file():
        errors["PLAYLIST"]=["MISSING"]
    else:
        b=path.read_bytes()
        blob=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
        if blob!=EXPECTED_BLOB:
            # Compare with approved main; only YEDEKLER order may change.
            import subprocess
            from collections import Counter
            try:
                base=subprocess.check_output(
                    ["git","show","origin/main:MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"],cwd=root)
            except (OSError,subprocess.CalledProcessError):
                errors["PLAYLIST"]=["APPROVED_BASELINE_UNAVAILABLE"]
            else:
                def parse(data):
                    chunks=data.splitlines(keepends=True)
                    header=[]
                    records=[]
                    for line in chunks:
                        if line.startswith(b"#EXTINF:"):
                            records.append([line])
                        elif records:
                            records[-1].append(line)
                        else:
                            header.append(line)
                    return b"".join(header),[b"".join(r) for r in records]
                h0,r0=parse(base)
                h1,r1=parse(b)
                # An unchanged playlist is always safe relative to the reviewed
                # main branch, even when the historical fixed blob and the
                # former 1087-entry YEDEKLER layout are no longer current.
                # This does NOT authorize any playlist modifications.
                if b == base:
                    continue_playlist_audit = False
                else:
                    continue_playlist_audit = True
                def backup(record):
                    return "YEDEKLER (1087)" in record.splitlines()[0].decode("utf-8")
                old=[r for r in r0 if backup(r)]
                new=[r for r in r1 if backup(r)]
                reorder_ok=(h0==h1 and len(old)==1087 and len(new)==1087 and
                    Counter(r0)==Counter(r1) and
                    [r for r in r0 if not backup(r)]==[r for r in r1 if not backup(r)] and
                    old[:2]==new[:2] and
                    [backup(r) for r in r0]==[backup(r) for r in r1])
                if continue_playlist_audit and not reorder_ok:
                    # An explicitly requested category operation must carry a
                    # one-change, exact-hash manifest in the same reviewed PR.
                    # No workflow or discovery job receives write permission.
                    manifest=root/"v2/ibo_authorized_change.json"
                    try:
                        spec=json.loads(manifest.read_text(encoding="utf-8"))
                        allowed={"reorder","copy","move","add","remove","rename","category"}
                        valid=(isinstance(spec,dict) and
                            set(spec)=={"base_sha256","result_sha256","operation","request","channels"} and
                            spec["base_sha256"]==hashlib.sha256(base).hexdigest() and
                            spec["result_sha256"]==hashlib.sha256(b).hexdigest() and
                            spec["operation"] in allowed and
                            isinstance(spec["request"],str) and len(spec["request"].strip())>=12 and
                            isinstance(spec["channels"],list) and 0<len(spec["channels"])<=2000 and
                            all(isinstance(x,str) and x.strip() for x in spec["channels"]) and
                            h0==h1 and len(r1)>0 and
                            all(x.startswith(b"#EXTINF:") and
                                any(line.startswith((b"http://",b"https://")) for line in x.splitlines()[1:])
                                for x in r1) and
                            all(x in Counter(r1) for x in Counter(r0) if spec["operation"] not in {"remove","move","rename","category"}))
                    except (OSError,ValueError,TypeError,KeyError):
                        valid=False
                    if not valid:
                        errors["PLAYLIST"]=["USER_AUTHORIZED_CHANGE_MANIFEST_REQUIRED"]


    return {"schema":1,"status":"MAIN_WORKFLOW_FILE_LOCK_PASS" if not errors
             else "MAIN_WORKFLOW_FILE_LOCK_FAIL",
            "checked_workflows":len(found),
            "suspended_writers":len(WRITER_SUSPENDED),
            "scheduled_triggers":0 if not errors else None,
            "unexpected_writes":0 if not errors else None,
            "server_side_branch_protection_verified":False,
            "main_playlist_modified":False,
            "errors":errors}

if __name__=="__main__":
    result=audit()
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    raise SystemExit(0 if result["status"]=="MAIN_WORKFLOW_FILE_LOCK_PASS" else 1)
