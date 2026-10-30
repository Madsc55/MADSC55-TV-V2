#!/usr/bin/env python3
"""Fast, offline contract checks before the expensive unified scan."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def source(name):
    path = ROOT / name
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return path.read_text(encoding="utf-8")

language = source("turkish_language_evidence.py")
queue = source("postscan_unified_action_queue.py")
summary = source("final_validation_summary.py")
workflow = (ROOT.parent / ".github/workflows/v2-turkish-stream-review.yml").read_text(encoding="utf-8")
assert '"spoken_turkish_verified": False' in language
assert '"approved": False' in language
assert 'Duplicate playback hashes' in language and 'Duplicate candidate hashes' in language
assert 'coverage_complete' in language and 'hashes != set(tested)' in language
assert 'AUDIO_EVIDENCE_UNCONFIRMED_LANGUAGE_UNVERIFIED' in language
assert 'SPOKEN_TURKISH_UNVERIFIED' in queue
assert 'language.get("approved") != 0' in queue
assert 'action_queue.get("approved") != 0' in summary
assert 'review_pending = bool(' in summary
assert 'test_playlist_invariants.py' in workflow
assert '4b1c3cea4b5107a425abab60f62d41f9f81e05a7' in workflow
assert 'python v2/turkish_language_evidence.py' in workflow
assert 'python v2/postscan_unified_action_queue.py' in workflow
assert 'python v2/final_validation_summary.py' in workflow
# Scanning must remain manual until infrastructure and archive restore are approved.
assert '  workflow_dispatch:' in workflow
assert '  push:' not in workflow and '  schedule:' not in workflow
# New candidate sources must not silently disappear from the preparation config.
import json
sources = json.loads((ROOT / 'config/sources.json').read_text(encoding='utf-8'))['sources']
urls = [item['url'] for item in sources]
ids = [item['id'] for item in sources]
assert len(urls) == len(set(urls)) and len(ids) == len(set(ids))
assert all(url.startswith('https://') for url in urls)
assert all(item.get('scope') in ('TR', 'AZ', 'SE', 'world', 'candidate') for item in sources)
for required in ('turktv-itasli-archive', 'onureroz-turk-index', 'onureroz-turk-all', 'onureroz-turk-karma', 'onureroz-world-index', 'dearbulut-best-ranked'):
    assert required in ids, required
# Execute network-free discovery behavior fixtures before allowing an expensive scan.
import subprocess
import sys
subprocess.run([sys.executable, str(ROOT / "test_discovery_offline_regressions.py")], check=True)
print("Offline unified safety contract: PASS")
