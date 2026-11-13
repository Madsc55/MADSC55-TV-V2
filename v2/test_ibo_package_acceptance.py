#!/usr/bin/env python3
"""Synthetic offline regression only; not production channel acceptance."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from ibo_package_acceptance import parse,validate,package

def fixture(n):
    rows=[(f'#EXTINF:-1 tvg-id="id{i}",Channel {i}',f'https://example.org/{i}.m3u8') for i in range(n)]
    text="#EXTM3U\n"+"".join(a+"\n"+b+"\n" for a,b in rows)
    proofs={hashlib.sha256((a+"\n"+b).encode()).hexdigest():{"status":"AV_VERIFIED","video":"h264","audio":"aac"} for a,b in rows}
    return text,proofs

class PackageTests(unittest.TestCase):
    def test_both_targets(self):
        text,proof=fixture(2000)
        for target in (1000,2000):
            out,report=package(text,target,proof)
            self.assertEqual(len(parse(out)),target)
            self.assertEqual(report["records"],target)
    def test_rejects_invalid_targets_at_api_boundary(self):
        text, proof = fixture(2000)
        for target in (0, -1, 1, 999, 1001, 2001, True, "1000"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                package(text, target, proof)

    def test_rejects_invalid_evidence_mapping(self):
        text, _ = fixture(1000)
        for evidence in (None, [], "AV_VERIFIED"):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                package(text, 1000, evidence)

    def test_shortage(self):
        text,proof=fixture(2)
        with self.assertRaises(ValueError):
            package(text,1000,proof)
    def test_missing_av(self):
        text,proof=fixture(1000)
        proof.pop(next(iter(proof)))
        with self.assertRaises(ValueError):
            package(text,1000,proof)
    def test_malformed(self):
        for text in ("#EXTM3U\n#EXTINF:-1,Name\n", "#EXTM3U\nhttps://x.org/a", "#EXTM3U\n#EXTINF:-1,Name\nfile:///tmp/x"):
            with self.assertRaises(ValueError):
                parse(text)
    def test_rejects_spoofed_m3u_header(self):
        for text in ("#EXTM3U-FAKE\n#EXTINF:-1,Name\nhttps://example.org/live",
                     "#EXTM3U garbage\n#EXTINF:-1,Name\nhttps://example.org/live"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse(text)

    def test_accepts_utf8_bom_only_at_start(self):
        playlist = "\ufeff#EXTM3U\n#EXTINF:-1,Name\nhttps://example.org/live.m3u8\n"
        self.assertEqual(len(parse(playlist)), 1)
        with self.assertRaises(ValueError):
            parse("#EXTM3U\n\ufeff#EXTM3U\n")

    def test_rejects_nested_m3u_headers(self):
        for body in ("#EXTM3U\n", "#EXTINF:-1,Name\n#EXTM3U\nhttps://example.org/live\n"):
            with self.subTest(body=body), self.assertRaises(ValueError):
                parse("#EXTM3U\n" + body)

    def test_rejects_credentials_in_stream_url(self):
        for url in ("https://user:password@example.org/live.m3u8",
                    "https://user@example.org/live.m3u8"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse("#EXTM3U\n#EXTINF:-1,Name\n" + url + "\n")

    def test_same_url_under_different_names_is_not_two_channels(self):
        records = [
            ('#EXTINF:-1 tvg-id="one",First', 'https://example.org/shared.m3u8'),
            ('#EXTINF:-1 tvg-id="two",Second', 'https://example.org/shared.m3u8'),
        ]
        with self.assertRaises(ValueError):
            validate(records)

    def test_cli_refuses_existing_output_without_overwrite(self):
        text, proof = fixture(1000)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            playlist, evidence, output = (root / name for name in ("input.m3u", "proof.json", "existing.m3u"))
            playlist.write_text(text, encoding="utf-8")
            evidence.write_text(json.dumps(proof), encoding="utf-8")
            output.write_text("DO_NOT_OVERWRITE", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("ibo_package_acceptance.py")),
                 "--playlist", str(playlist), "--evidence", str(evidence),
                 "--target", "1000", "--output", str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "DO_NOT_OVERWRITE")

    def test_duplicate(self):
        text,_=fixture(1)
        with self.assertRaises(ValueError):
            validate(parse(text+text.splitlines()[1]+"\n"+text.splitlines()[2]+"\n"))
if __name__=="__main__":
    unittest.main()
