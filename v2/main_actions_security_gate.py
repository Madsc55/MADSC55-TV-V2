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
        if set(events)!={"push"} or mapping(events.get("push")).get("branches")!=["main"] or mapping(events.get("push")).get("paths")!=[".github/workflows/ibo-authorized-500.yml"]:
            return ["ONE_TIME_TRIGGER_CHANGED"]
        if mapping(doc.get("permissions"))!={"contents":"write","pull-requests":"write"}:
            return ["ONE_TIME_PERMISSIONS_CHANGED"]
        if set(mapping(doc.get("jobs")))!={"import"}:
            return ["ONE_TIME_JOB_CHANGED"]
        if "14136864383" not in source or "165c726cd9211f9f51c31f1c718e0911bab79e1b" not in source or "len(added)==1000" not in source:
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
            # Only allow stable partition: 58 existing sports entries moved to backup tail.
            original_positions=[3,12,197,254,255,256,260,261,338,343,344,371,405,454,499,529,530,531,543,544,545,546,547,548,549,550,551,552,553,573,576,577,578,579,580,581,582,583,584,585,606,614,618,629,645,646,740,810,848,852,853,854,898,903,1036,1045,1046,1047]
            lines=b.decode("utf-8").splitlines(keepends=True)
            backup_indices=[i for i,line in enumerate(lines) if line.startswith("#EXTINF:") and "YEDEKLER" in line]
            entries=[(lines[i],lines[i+1]) for i in backup_indices]
            count=len(original_positions)
            if len(entries)!=1087 or len(set(original_positions))!=count or count!=58:
                errors["PLAYLIST"]=["INVALID_SPORTS_PARTITION"]
            else:
                ordinary=iter(entries[:-count])
                sports=iter(entries[-count:])
                sports_positions=set(original_positions)
                restored=[next(sports) if i in sports_positions else next(ordinary) for i in range(1,len(entries)+1)]
                for index,entry in zip(backup_indices,restored):
                    lines[index],lines[index+1]=entry
                previous="".join(lines).encode("utf-8")
                old_sha=hashlib.sha1(b"blob "+str(len(previous)).encode()+b"\0"+previous).hexdigest()
                if old_sha!="eedef5764389a37563ce1a693e92c6d5e4d9f798":
                    errors["PLAYLIST"]=["ONLY_STABLE_SPORTS_REORDER_ALLOWED"]
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
