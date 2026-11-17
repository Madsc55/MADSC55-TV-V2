#!/usr/bin/env python3
"""Opt-in bounded YEDEKLER AV/ASR/subtitle evidence collection; never edits playlists.

Requires independent secure egress attestation and source authorization.
Only explicitly selected 1-based playlist ordinals are sampled.
"""
import argparse
import json
import tempfile
from pathlib import Path
try:
    from .single_channel_evidence_review import review_one
except ImportError:
    from single_channel_evidence_review import review_one

def collect(playlist, output, ordinals, *, source_authorized=False, model_dir=None):
    playlist, output = Path(playlist), Path(output)
    selected = list(ordinals)
    if not source_authorized:
        raise ValueError("Source authorization required")
    if not selected or len(selected) > 10 or len(set(selected)) != len(selected):
        raise ValueError("Select 1..10 unique ordinals per batch")
    if any(type(i) is not int or i <= 1003 for i in selected):
        raise ValueError("Protected first 1003 channels cannot be sampled here")
    if output.exists() or playlist.resolve() == output.resolve():
        raise FileExistsError("Refusing to overwrite input or evidence")
    if playlist.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Playlist exceeds bounded size")
    selected_set = set(selected)
    records = {}
    pending = None
    count = 0
    with playlist.open(encoding="utf-8-sig", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("#EXTINF:"):
                if pending is not None:
                    raise ValueError("Unpaired EXTINF")
                count += 1
                group = ""
                import re
                match = re.search(r'group-title="([^"]*)"', line)
                if match:
                    group = match.group(1)
                pending = (count, group)
            elif line and not line.startswith("#") and pending is not None:
                ordinal, group = pending
                if ordinal in selected_set:
                    if group != "YEDEKLER":
                        raise ValueError("Selected channel is not in YEDEKLER")
                    records[ordinal] = line
                pending = None
    if pending or set(records) != selected_set:
        raise ValueError("Selected channel missing or malformed")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="v2-turkish-evidence-") as tmp:
        rows = []
        for ordinal in selected:
            sample = review_one(records[ordinal], Path(tmp) / f"{ordinal}.json",
                                source_authorized=True, model_dir=model_dir)
            rows.append({"playlist_ordinal": ordinal, "sample_report": sample})
        with output.open("x", encoding="utf-8") as dest:
            for row in rows:
                dest.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"sampled": len(rows), "playlist_modified": False, "approved": 0}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ordinal", type=int, action="append", required=True)
    p.add_argument("--reviewed-sources-authorized", action="store_true")
    p.add_argument("--local-asr-model", type=Path)
    a = p.parse_args()
    print(json.dumps(collect(a.playlist, a.output, a.ordinal,
                             source_authorized=a.reviewed_sources_authorized,
                             model_dir=a.local_asr_model)))

if __name__ == "__main__":
    main()
