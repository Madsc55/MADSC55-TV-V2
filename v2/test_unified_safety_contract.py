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
print("Offline unified safety contract: PASS")
