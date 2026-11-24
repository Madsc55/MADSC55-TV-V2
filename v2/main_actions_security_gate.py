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
v2-yedekler-logos.yml v2-youtube-discovery.yml v2-yedekler-av-audit.yml v2-yedekler-result-reconcile.yml
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
OFFLINE="ibo-single-playlist-transfer-offline.yml"
HISTORICAL_AUDIT="issue-489-historical-audit.yml"
OFFLINE_CI="ci.yml"
PASS1="run_pass1_cleanup.yml"
HEALTH_REPORT="update_main_playlist.yml"
PARTS_BUILD="build_playlist_from_parts.yml"
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
    if filename==PARTS_BUILD:
        if set(events)!={"push","workflow_dispatch"} or mapping(events["push"]).get("branches")!=["main","command/ibo-*"]:
            return ["PARTS_BUILD_UNAPPROVED_TRIGGER"]
        paths=set(mapping(events["push"]).get("paths",[]))
        if paths!={"v2/playlist_parts_manager.py","v2/playlists/parts/**",".github/workflows/build_playlist_from_parts.yml"}:
            return ["PARTS_BUILD_UNAPPROVED_PATHS"]
        if mapping(doc.get("permissions"))!={"contents":"read"}:
            return ["PARTS_BUILD_EXCESSIVE_DEFAULT_PERMISSIONS"]
        jobs=mapping(doc.get("jobs"))
        if set(jobs)!={"build","command-branch"} or mapping(jobs["build"].get("permissions"))!={"contents":"write"}:
            return ["PARTS_BUILD_JOB_PERMISSIONS_CHANGED"]
        if jobs["build"].get("if")!="github.ref == 'refs/heads/main' && !contains(github.event.head_commit.message, '[skip ci]')":
            return ["PARTS_BUILD_MAIN_ONLY_REQUIRED"]
        command_job = mapping(jobs.get("command-branch"))
        if (command_job.get("if") !=
                "startsWith(github.ref, 'refs/heads/command/ibo-') && github.actor == 'Madsc55'"
                or mapping(command_job.get("permissions")) != {"contents":"write"}):
            return ["PARTS_BUILD_COMMAND_BRANCH_GUARD_CHANGED"]
        command_required = (
            "git diff --name-status origin/main...HEAD",
            "git merge-base origin/main HEAD",
            "A\\tv2/playlists/parts/pending_command.json",
            "expected_git_blob_sha",
            "python v2/channel_command_engine.py --request v2/playlists/parts/pending_command.json --apply",
            "rm -- v2/playlists/parts/pending_command.json",
            "python v2/playlist_parts_manager.py auto",
            "python v2/test_playlist_invariants.py",
            'git push origin "HEAD:refs/heads/${GITHUB_REF_NAME}"',
            "git diff --cached --name-only",
        )
        if not all(fragment in source for fragment in command_required):
            return ["PARTS_BUILD_COMMAND_BRANCH_VALIDATION_CHANGED"]
        required=("python v2/channel_command_engine.py --request v2/playlists/parts/pending_command.json --apply",
                  "rm -- v2/playlists/parts/pending_command.json",
                  "python v2/playlist_parts_manager.py auto",
                  "python v2/test_playlist_invariants.py",
                  "git add -- MADSC55_TV_IBO_CALISANLAR_TEST.m3u8 v2/playlists/parts/",
                  'branch="automation/ibo-parts-',
                  'git switch -c "$branch"',
                  "gh auth setup-git",
                  'git push origin "HEAD:refs/heads/$branch"',
                  'echo "Validated proposal branch: $branch" >> "$GITHUB_STEP_SUMMARY"')
        if not all(fragment in source for fragment in required):
            return ["PARTS_BUILD_VALIDATION_OR_WRITE_SCOPE_CHANGED"]
        if "push origin HEAD:main" in source or "push origin main" in source:
            return ["PARTS_BUILD_DIRECT_MAIN_PUSH_FORBIDDEN"]
        if "gh pr create" in source or "gh workflow run" in source:
            return ["PARTS_BUILD_BOT_PR_OR_DISPATCH_FORBIDDEN"]
        if "pull_request_target" in source or "schedule:" in source:
            return ["PARTS_BUILD_UNTRUSTED_TRIGGER"]
        return []
    if filename==PASS1:
        if set(mapping(doc.get("on")))!={"workflow_dispatch"}:
            return ["PASS1_MANUAL_ONLY_REQUIRED"]
        if mapping(doc.get("permissions"))!={"contents":"read"}:
            return ["PASS1_READ_ONLY_REQUIRED"]
        if set(mapping(doc.get("jobs")))!={"cleanup"}:
            return ["PASS1_JOB_CHANGED"]
        if ("v2/cleanup_epg_logo_pass1.py" not in source or "pass1-cleanup-results" not in source or "actions/upload-artifact@v4" not in source):
            return ["PASS1_ARTIFACT_INVARIANTS_CHANGED"]
        if MUTATION.search(source) or PERSISTED.search(source):
            return ["PASS1_WRITE_FORBIDDEN"]
        return []
    if filename=="ibo-authorized-500.yml":
        if set(events)!={"workflow_dispatch"}:
            return ["ONE_TIME_TRIGGER_CHANGED"]
        if mapping(doc.get("permissions"))!={"contents":"write","pull-requests":"write"}:
            return ["ONE_TIME_PERMISSIONS_CHANGED"]
        if set(mapping(doc.get("jobs")))!={"import"}:
            return ["ONE_TIME_JOB_CHANGED"]
        if ("14136864383" not in source or "python3 v2/import_every_archive_both_systems.py --old-repo /tmp/old-madsc-tv --scan-dir /tmp/all-scan" not in source or "python3 v2/test_playlist_invariants.py" not in source or "v2/ibo_authorized_change.json" not in source):
            return ["ONE_TIME_IMPORT_INVARIANTS_CHANGED"]
        return []
    if filename=="run_move_685.yml":
        # One explicitly authorized manual-only writer. Never run on push/PR.
        if set(events)!={"workflow_dispatch"}:
            return ["685_UNAPPROVED_TRIGGER"]
        if mapping(doc.get("permissions"))!={"contents":"write","pull-requests":"write","actions":"read"}:
            return ["685_WRONG_PERMISSIONS"]
        if set(mapping(doc.get("jobs")))!={"preview-685"}:
            return ["685_UNEXPECTED_JOB"]
        required=("v2/unlock_and_move_685.py", "44842556117",
                  "git switch -c", "gh pr create --base main",
                  "git push origin", "git diff --exit-code",
                  "actions/upload-artifact@v4")
        if not all(fragment in source for fragment in required):
            return ["685_PUBLISHER_INVARIANTS_CHANGED"]
        if "refs/heads/main" in source or "git push origin main" in source:
            return ["685_DIRECT_MAIN_WRITE_FORBIDDEN"]
        return []
    allowed=({"push","pull_request","workflow_dispatch"} if filename==GATE else
             {"push","pull_request","workflow_dispatch"} if filename==OFFLINE_CI else
             {"push","workflow_dispatch"} if filename==SAFETY else
             {"pull_request"} if filename==OFFLINE else
             {"pull_request","workflow_dispatch"} if filename==HISTORICAL_AUDIT else
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
        elif filename==OFFLINE_CI:
            pass  # Offline test-only CI is allowed on pushes.
        elif filename==SAFETY:
            if "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8" not in set(cfg.get("paths",[])):
                problems.append("PLAYLIST_SAFETY_MISSING_PATH")
        else:
            problems.append("UNAPPROVED_PUSH")
    if "pull_request" in events:
        if filename==OFFLINE:
            if set(mapping(events["pull_request"]).get("paths",[]))!={
                "v2/ibo_single_playlist_transfer.py",
                "v2/ibo_archive_operation_ledger.py",
                "v2/test_ibo_archive_operation_ledger.py",
                "v2/test_ibo_single_playlist_transfer.py",
                "v2/test_ibo_single_playlist_real_data.py",
                ".github/workflows/ibo-single-playlist-transfer-offline.yml",
            }:
                problems.append("OFFLINE_TEST_PATHS_CHANGED")
        elif filename==HISTORICAL_AUDIT:
            if set(mapping(events["pull_request"]).get("paths",[]))!={
                "v2/audit_489_historical_inventory.py",
                ".github/workflows/issue-489-historical-audit.yml",
            }:
                problems.append("HISTORICAL_AUDIT_PATHS_CHANGED")
        elif filename==OFFLINE_CI:
            pass  # Offline CI tests every pull request.
        elif filename!=GATE or set(mapping(events["pull_request"]).get("branches",[]))!={"main"}:
            problems.append("UNAPPROVED_PR_TRIGGER")
    perms=mapping(doc.get("permissions"))
    if perms.get("contents")!="read":
        problems.append("DEFAULT_CONTENTS_NOT_READ_ONLY")
    if any(value=="write" for value in perms.values()):
        problems.append("WORKFLOW_HAS_WRITE_PERMISSION")
    jobs=mapping(doc.get("jobs"))
    if not jobs:
        problems.append("NO_JOBS")
    # #497: the historical 685-entry retry accepts untrusted remote URLs.
    # Do not let any workflow run ffprobe/FFmpeg until DNS/IP/redirect/HLS
    # egress restrictions have passed explicit offline security acceptance.
    # Fail closed on newly added jobs as well as removal of the hold.
    if filename=="full_autonomous_pipeline.yml":
        if set(jobs)!={"acceptance"} or mapping(jobs.get("acceptance")).get("if")!="${{ false }}":
            problems.append("AUTONOMOUS_PIPELINE_SECURITY_HOLD_REQUIRED")
    if filename=="v2-yedekler-av-audit.yml":
        retry=jobs.get("retry")
        if (set(jobs)!={"retry"} or not isinstance(retry,dict)
                or retry.get("if")!="${{ false }}"):
            problems.append("UNSAFE_685_LIVE_RETRY_NOT_SUSPENDED")
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

def preserves_record_multiplicity(original, candidate):
    """Ensure an authorized non-removal edit cannot silently lose repeated records."""
    from collections import Counter
    before, after = Counter(original), Counter(candidate)
    return all(after[record] >= count for record, count in before.items())

def category_count_normalized(record):
    """Normalize only the visible numeric suffix; preserve every other byte."""
    head, sep, rest = record.partition(b"\n")
    pattern = re.compile(rb'(group-title\s*=\s*")([^"]*)(")', re.I)
    match = pattern.search(head)
    if match is None:
        raise ValueError("Missing group title")
    label = re.sub(rb'\s*\(\d+\)\s*\Z', b'', match.group(2))
    return head[:match.start(2)] + label + head[match.end(2):] + sep + rest


def safe_favorite_copy(original, candidate):
    """No missing channels; additions may only copy existing streams to FAVORİLER."""
    from collections import Counter
    try:
        old = Counter(map(category_count_normalized, original))
        new = Counter(map(category_count_normalized, candidate))
        if any(new[record] < n for record, n in old.items()):
            return False
        extras = new - old
        if sum(extras.values()) > 2000:
            return False

        def without_group(rec):
            return re.sub(rb'group-title\s*=\s*"[^"]*"', b'group-title="<EXISTING>"',
                          rec, count=1, flags=re.I)

        known = {without_group(rec) for rec in old}
        for rec in extras:
            head = rec.splitlines()[0].decode("utf-8")
            matched = re.search(r'group-title\s*=\s*"([^"]+)"', head, re.I)
            if matched is None or "FAVORİLER" not in matched.group(1).upper():
                return False
            if without_group(rec) not in known:
                return False
        return True
    except (ValueError, UnicodeError, TypeError):
        return False


def safe_channel_move(original, candidate):
    """Owner-approved category moves/recounts must preserve every underlying record."""
    from collections import Counter
    try:
        def without_group(record):
            return re.sub(rb'group-title\s*=\s*"[^"]*"',
                          b'group-title="<PRESERVED>"', record, count=1, flags=re.I)
        return Counter(map(without_group, original)) == Counter(
            map(without_group, candidate))
    except (ValueError, UnicodeError, TypeError):
        return False



def safe_single_ana_removal(original, candidate, record_sha256):
    """Verify exactly one named record removal; preserve all other records and order."""
    if len(original) != len(candidate) + 1:
        return False
    try:
        matching = [i for i, rec in enumerate(original)
                    if hashlib.sha256(rec).hexdigest() == record_sha256
                    and b'group-title="ANA AR' in rec.splitlines()[0]
                    and rec.splitlines()[0].endswith(b",GEM Sport")]
        if len(matching) != 1:
            return False
        i = matching[0]
        expected = original[:i] + original[i+1:]
        return [category_count_normalized(r) for r in expected] == [
            category_count_normalized(r) for r in candidate]
    except (ValueError, TypeError, IndexError):
        return False

def safe_backup_display_rename(original, candidate):
    """Only deterministic YEDEKLER display-name edits; every other byte stable."""
    try:
        from channel_command_engine import format_backup_display
        from playlist_parts_manager import category, logical
        if len(original) != len(candidate) or not original:
            return False
        changed = 0
        for before, after in zip(original, candidate):
            bhead, bsep, btail = before.partition(b"\n")
            ahead, asep, atail = after.partition(b"\n")
            if bsep != asep or btail != atail:
                return False
            if b"," not in bhead or b"," not in ahead:
                return False
            bmeta, _, bname = bhead.rpartition(b",")
            ameta, _, aname = ahead.rpartition(b",")
            if bmeta != ameta or category(before) != category(after):
                return False
            if logical(category(before)) == "YEDEKLER":
                wanted = format_backup_display(bname.decode("utf-8").strip()).encode("utf-8")
                if aname != wanted:
                    return False
            elif before != after:
                return False
            if before != after:
                changed += 1
        return changed > 0
    except (ValueError, UnicodeError, TypeError, KeyError):
        return False


def safe_category_reorder(original, candidate):
    """Reorder and counter changes cannot mutate or delete existing records."""
    from collections import Counter
    try:
        return Counter(map(category_count_normalized, original)) == Counter(
            map(category_count_normalized, candidate))
    except (ValueError, UnicodeError, TypeError):
        return False


def audit(root=ROOT):
    root=Path(root)
    folder=root/".github/workflows"
    found={p.name for p in folder.iterdir() if p.is_file() and p.suffix in (".yml",".yaml")}
    expected=ORIGINAL_FILES|{PASS1,GATE,OFFLINE,HISTORICAL_AUDIT,HEALTH_REPORT,OFFLINE_CI,PARTS_BUILD,"full_autonomous_pipeline.yml","autonomous_discovery_readonly.yml","v2-stage6-grouped-acceptance.yml","ibo-authorized-500.yml","v2-offline-import-15.yml","run_move_685.yml"}
    errors={}
    if found!=expected:
        errors["WORKFLOW_INVENTORY"]={"missing":sorted(expected-found),
                                      "unexpected":sorted(found-expected)}
    for name in sorted(found&expected):
        workflow_path = folder/name
        if workflow_path.is_symlink():
            errors[name]=["SYMLINK_WORKFLOW_FORBIDDEN"]
            continue
        issues=audit_one(name,workflow_path.read_text(encoding="utf-8"))
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
                # Exact, user-authorized 2500/15574 batch migration. This is not
                # a general exemption: verify the immutable source, preserved
                # non-backup records, ordered first batch and queued remainder.
                def batch_migration_ok():
                    try:
                        source=(root/"v2/yedekler_batch/YEDEKLER_ARCHIVE.m3u8").read_bytes()
                        archive=(root/"v2/yedekler_batch/ANA_ARSIV.m3u8").read_bytes()
                        state=json.loads((root/"v2/yedekler_batch/state.json").read_text(encoding="utf-8"))
                        hs,rs=parse(source)
                        ha,ra=parse(archive)
                        def is_backup(rec):
                            return b'group-title="\\xf0\\x9f\\x97\\x82\\xef\\xb8\\x8f YEDEKLER (18074)"' in rec.splitlines()[0]
                        def relabel(rec, old_label, new_label):
                            return rec.replace(old_label, new_label, 1)
                        old_label='🗂️ YEDEKLER (18074)'.encode()
                        new_label='🗂️ YEDEKLER (2500)'.encode()
                        archive_label='🗄️ ANA ARŞİV (15574)'.encode()
                        originals=[rec for rec in r0 if old_label in rec.splitlines()[0]]
                        expected_first=[relabel(rec,old_label,new_label) for rec in rs[:2500]]
                        expected_archive=[relabel(rec,old_label,archive_label) for rec in rs[2500:]]
                        return (hashlib.sha1(b"blob "+str(len(base)).encode()+b"\0"+base).hexdigest()=="710070b4bc93c74eb9a753849449c03a0b40d9d0"
                            and hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()=="7e2b996e2c7eb286d196750f28e0e6ec155f89fc"
                            and hashlib.sha256(source).hexdigest()=="d72ac1e6bf27982862e23e06957222a9abaf7b03f0fab01edc2147144b50be5c"
                            and state.get("source_sha256")==hashlib.sha256(source).hexdigest()
                            and state.get("total")==18074
                            and len(rs)==18074 and len(originals)==18074 and originals==rs
                            and len(ra)==15574 and ra==expected_archive
                            and h0==h1 and hs==ha==h0
                            and len(r1)==3338
                            and [rec for rec in r1 if new_label in rec.splitlines()[0]]==expected_first
                            and [rec for rec in r1 if new_label not in rec.splitlines()[0]]==[rec for rec in r0 if old_label not in rec.splitlines()[0]]
                            and len(state.get("status",{}))==2500
                            and all(state["status"].get(str(i))=="TEST" for i in range(1,2501)))
                    except (OSError,ValueError,TypeError,KeyError):
                        return False
                # One-time, exact-baseline confirmed-404 removal. Never permit
                # arbitrary additions, reordering, or changes to YEDEKLER.
                def confirmed_404_cleanup_ok():
                    from ibo_single_playlist_transfer import inventory, category
                    # Bind to the reviewed main inventory rather than a stale
                    # blob SHA from an earlier version of main.
                    from ibo_single_playlist_transfer import inventory
                    if inventory(base) != {
                        "YEDEKLER": 1792, "ANA": 15574, "TURK": 424,
                        "YABANCI": 284, "OTHER": 838, "TOTAL": 18912,
                    }:
                        return False
                    if h0 != h1 or len(r0) - len(r1) != 575:
                        return False
                    old_yedekler = [r for r in r0 if category(r.splitlines()[0].decode("utf-8")) == "YEDEKLER"]
                    new_yedekler = [r for r in r1 if category(r.splitlines()[0].decode("utf-8")) == "YEDEKLER"]
                    if old_yedekler != new_yedekler or len(old_yedekler) != 1792:
                        return False
                    ordered = iter(r0)
                    if not all(any(old == record for old in ordered) for record in r1):
                        return False
                    return inventory(b) == {
                        "YEDEKLER": 1792, "ANA": 15018, "TURK": 422,
                        "YABANCI": 279, "OTHER": 826, "TOTAL": 18337,
                    }
                # Exact previously generated 685-entry migration, with immutable
                # input/output digests and record-count preservation.
                def authorized_685_migration_ok():
                    if hashlib.sha256(base).hexdigest()!="6c4c06e4c5188f0868552a15fe0e2a78beee30bd6eb86b7b7d666338e29f29fc":
                        return False
                    if hashlib.sha256(b).hexdigest()!="203274453ef09bf5a87c25374275127367eb79e75c351ce738fa788be6c52da4":
                        return False
                    if h0!=h1 or len(r0)!=18337 or len(r1)!=18337:
                        return False
                    from ibo_single_playlist_transfer import inventory
                    before=inventory(base)
                    after=inventory(b)
                    return (before.get("YEDEKLER")==1792 and
                            before.get("TOTAL")==18337 and
                            after.get("YEDEKLER")==1107 and
                            after.get("ANA")==before.get("ANA")+685 and
                            after.get("TOTAL")==18337 and
                            all(after.get(k)==before.get(k) for k in ("TURK","YABANCI","OTHER")))
                # Owner-requested category-counter correction only. Require the
                # entire playlist to match byte-for-byte after exactly these
                # three label substitutions; no URL, ordering or record edits.
                def category_counter_correction_ok():
                    if h0 != h1 or len(r0) != 18337 or len(r1) != 18337:
                        return False
                    replacements = (
                        ('group-title="🗂️ YEDEKLER (1792)"', 'group-title="🗂️ YEDEKLER (1107)"'),
                        ('group-title="ANA ARŞİV (15574)"', 'group-title="ANA ARŞİV (15703)"'),
                        ('group-title="ANA ARŞİV"', 'group-title="ANA ARŞİV (15703)"'),
                    )
                    normalized = base
                    for old_label, new_label in replacements:
                        normalized = normalized.replace(old_label.encode("utf-8"), new_label.encode("utf-8"))
                    return (normalized != base and b == normalized
                            and base.count('group-title="🗂️ YEDEKLER (1792)"'.encode()) == 1107
                            and b.count('group-title="🗂️ YEDEKLER (1107)"'.encode()) == 1107
                            and b.count('group-title="ANA ARŞİV (15703)"'.encode()) == 15703)
                # Owner-authorized alphabetical reorder of ANA ARŞİV only.
                # Every record must be byte-identical and non-archive slots unchanged.
                def ana_archive_alphabetical_sort_ok():
                    from collections import Counter
                    import unicodedata
                    from ibo_single_playlist_transfer import category
                    if h0 != h1 or len(r0) != 18337 or len(r1) != 18337:
                        return False
                    def archive_indices(records):
                        return [i for i, record in enumerate(records)
                                if category(record.splitlines()[0].decode("utf-8")) == "ANA"]
                    indices = archive_indices(r0)
                    if len(indices) != 15703 or archive_indices(r1) != indices:
                        return False
                    if Counter(r0) != Counter(r1):
                        return False
                    slots = set(indices)
                    if any(r0[i] != r1[i] for i in range(len(r0)) if i not in slots):
                        return False
                    def key(record):
                        name = record.splitlines()[0].decode("utf-8").rsplit(",", 1)[-1].strip()
                        lower = name.casefold()
                        normalized = unicodedata.normalize("NFKD", lower)
                        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
                        normalized = normalized.translate(str.maketrans({"ı": "i", "æ": "ae", "œ": "oe"}))
                        return normalized, lower
                    # Exact reviewed sorted artifact, in addition to the
                    # byte-preservation and category-slot checks above.
                    git_blob = hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()
                    return git_blob == "aaeb2bc9d7bc1a109068e76df513416e609d9e3f"
                # Authorized lossless parts migration: one reviewed PR reorders
                # the whole ANA ARŞİV block after YEDEKLER, retaining all bytes,
                # multiplicities and internal order. The manifest binds the exact
                # original main SHA and hashes of every generated part.
                def canonical_parts_move_ok():
                    try:
                        from playlist_parts_manager import category as part_category, logical
                        import re
                        if h0 != h1 or len(r0) != len(r1) or len(r0) != 18337:
                            return False
                        def group(record):
                            return logical(part_category(record))
                        from collections import Counter
                        if Counter(r0) != Counter(r1):
                            return False
                        if Counter(map(group, r0)) != Counter(map(group, r1)):
                            return False
                        if Counter(map(group, r1))["YEDEKLER"] != 1107 or Counter(map(group, r1))["ANA ARŞİV"] != 15703:
                            return False
                        archive = [x for x in r0 if group(x) == "ANA ARŞİV"]
                        remaining = [x for x in r0 if group(x) != "ANA ARŞİV"]
                        insertion = max(i for i, x in enumerate(remaining) if group(x) == "YEDEKLER") + 1
                        if r1 != remaining[:insertion] + archive + remaining[insertion:]:
                            return False
                        parts_dir = root / "v2/playlists/parts"
                        manifest = json.loads((parts_dir / "manifest.json").read_text(encoding="utf-8"))
                        if (manifest.get("version") != 1
                                or manifest.get("total_records") != 18337
                                or manifest.get("source_sha256") != hashlib.sha256(base).hexdigest()
                                or manifest.get("header_hex") != h0.hex()):
                            return False
                        parts = []
                        names = []
                        for entry in manifest["entries"]:
                            name = entry["file"]
                            # Strict four-digit basename only; reject separators and traversal.
                            if not re.fullmatch(r"[0-9]{4}\.m3u", name):
                                return False
                            payload = (parts_dir / name).read_bytes()
                            if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                                return False
                            if len([line for line in payload.splitlines() if line.startswith(b"#EXTINF:")]) != entry["records"]:
                                return False
                            if any(group(x) != entry["group"] for x in parse(payload)[1]):
                                return False
                            names.append(name)
                            parts.append(payload)
                        if len(names) != len(set(names)) or set(names) != {p.name for p in parts_dir.glob("*.m3u")}:
                            return False
                        return b == h1 + b"".join(parts)
                    except (OSError,ValueError,TypeError,KeyError,UnicodeError,IndexError,AttributeError):
                        return False
                parts_move_ok = continue_playlist_audit and canonical_parts_move_ok()
                archive_sort_ok = continue_playlist_audit and ana_archive_alphabetical_sort_ok()
                counter_correction_ok = continue_playlist_audit and category_counter_correction_ok()
                move_685_ok = continue_playlist_audit and authorized_685_migration_ok()
                cleanup_ok = continue_playlist_audit and confirmed_404_cleanup_ok()
                batch_ok=continue_playlist_audit and batch_migration_ok()
                if continue_playlist_audit and not reorder_ok and not batch_ok and not cleanup_ok and not move_685_ok and not counter_correction_ok and not archive_sort_ok and not parts_move_ok:
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
                            isinstance(spec["channels"],list) and 0<len(spec["channels"])<=2500 and
                            all(isinstance(x,str) and x.strip() for x in spec["channels"]) and
                            h0==h1 and len(r1)>0 and
                            all(x.startswith(b"#EXTINF:") and
                                any(line.startswith((b"http://",b"https://")) for line in x.splitlines()[1:])
                                for x in r1) and
                            ((spec["operation"] in {"move","category"} and safe_channel_move(r0, r1)) or
                             (spec["operation"]=="copy" and safe_favorite_copy(r0, r1)) or
                             (spec["operation"]=="reorder" and safe_category_reorder(r0, r1)) or
                             (spec["operation"]=="rename" and safe_backup_display_rename(r0, r1)) or
                             # One-time explicit owner removal: original ANA #151, GEM Sport.
                             (spec["operation"]=="remove" and spec["channels"]==["GEM Sport"] and
                              spec["base_sha256"]=="9eba8a6fb34d69d3150dde76efa39ca403b490bad8770ba09151088e9567873c" and
                              spec["result_sha256"]=="b0e3061aeae62835894de40c2a2ca23249a0a833b13411950bf3840e5e75083c" and
                              safe_single_ana_removal(r0, r1, "74331fff013b25b76d35b754e0b55671f7c387239bf6f6f5f7056e177e8f7572"))))
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
