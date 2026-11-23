"""Offline, no-network acceptance for the narrowly scoped move-only CI fast path."""
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from channel_command_engine import operate, record_name
from fast_channel_move_scope import eligible_pr, safe_move_bytes
from playlist_parts_manager import checksum, parts_for
from test_channel_command_engine import SAMPLE

PLAYLIST = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"


class FastMoveScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.parts = self.root / "v2/playlists/parts"
        self.parts.mkdir(parents=True)
        self.original = SAMPLE
        command = {"action": "move", "expected_sha256": checksum(SAMPLE),
                   "source": "YEDEKLER", "target": "YABANCI ARŞİVİ",
                   "range": {"start": 2, "end": 3}}
        self.candidate, _, report = operate(SAMPLE, command)
        payloads, manifest = parts_for(self.candidate, checksum(SAMPLE))
        for name, data in payloads.items():
            (self.parts / name).write_bytes(data)
        (self.parts / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
        )
        self.spec = {"base_sha256": checksum(SAMPLE),
                     "result_sha256": checksum(self.candidate), "operation": "move",
                     "request": "Move the requested two source channels to target archive",
                     "channels": report["selected"]}
        (self.root / PLAYLIST).write_bytes(self.candidate)
        (self.root / "v2/ibo_authorized_change.json").write_text(
            json.dumps(self.spec, ensure_ascii=False), encoding="utf-8"
        )

    def test_one_move_passes_and_labels_are_consistent(self):
        self.assertTrue(safe_move_bytes(
            self.original, self.candidate, self.spec, self.parts))
        self.assertEqual(len(self.spec["channels"]), 2)

    def test_denies_missing_record_or_modified_url(self):
        lost = self.candidate.replace(
            b"https://sample.test/3", b"https://sample.test/missing", 1)
        self.assertFalse(safe_move_bytes(
            self.original, lost, {**self.spec, "result_sha256": checksum(lost)}, self.parts))
        changed = self.candidate.replace(b"https://sample.test/4", b"https://sample.test/5")
        self.assertFalse(safe_move_bytes(
            self.original, changed, {**self.spec, "result_sha256": checksum(changed)}, self.parts))

    def test_denies_missing_or_stale_manifest_and_false_authorization(self):
        self.assertFalse(safe_move_bytes(
            self.original, self.candidate,
            {**self.spec, "channels": ["Only One"]}, self.parts))
        self.assertFalse(safe_move_bytes(
            self.original, self.candidate,
            {**self.spec, "operation": "copy"}, self.parts))
        (self.parts / "manifest.json").unlink()
        with self.assertRaises(OSError):
            safe_move_bytes(self.original, self.candidate, self.spec, self.parts)

    def test_owner_only_allowed_files(self):
        base = "a" * 40
        allowed = (PLAYLIST + "\0v2/ibo_authorized_change.json\0"
                   "v2/playlists/parts/manifest.json\0"
                   "v2/playlists/parts/0000.m3u\0").encode()
        def git(args, **_kwargs):
            if args[1] == "diff":
                return allowed
            if args[1] == "show":
                return self.original
            raise AssertionError(args)
        with patch("fast_channel_move_scope.subprocess.check_output", side_effect=git):
            self.assertTrue(eligible_pr(base, "Madsc55/MADSC55-TV-V2",
                "Madsc55/MADSC55-TV-V2", "Madsc55", "command/ibo-checked", self.root))
            self.assertFalse(eligible_pr(base, "Madsc55/MADSC55-TV-V2",
                "Madsc55/MADSC55-TV-V2", "Untrusted", "command/ibo-checked", self.root))
            self.assertFalse(eligible_pr(base, "Madsc55/MADSC55-TV-V2",
                "fork/MADSC55-TV-V2", "Madsc55", "command/ibo-checked", self.root))
            self.assertFalse(eligible_pr(base, "Madsc55/MADSC55-TV-V2",
                "Madsc55/MADSC55-TV-V2", "Madsc55", "fix/workflow", self.root))

    def test_code_or_workflow_changes_must_run_full_suite(self):
        base = "a" * 40
        paths = (PLAYLIST + "\0v2/ibo_authorized_change.json\0"
                 "v2/playlists/parts/manifest.json\0"
                 ".github/workflows/v2-main-production-safety-gate.yml\0").encode()
        with patch("fast_channel_move_scope.subprocess.check_output", return_value=paths):
            self.assertFalse(eligible_pr(base, "Madsc55/MADSC55-TV-V2",
                "Madsc55/MADSC55-TV-V2", "Madsc55", "command/ibo-owner", self.root))


if __name__ == "__main__":
    unittest.main()
