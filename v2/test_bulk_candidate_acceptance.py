#!/usr/bin/env python3
"""Real RSA/AES archive roundtrips with offline synthetic AV-evidence fixtures."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import bulk_candidate_acceptance as bulk
from stage3_sealed_export import open_rows, seal_rows
from traz_api_av_batch import summarize


def fixture(count=1):
    unique, checks, rows = {}, {}, []
    for i in range(count):
        url = f"https://cdn.example.org/{i}.m3u8?token=DO_NOT_PRINT_SECRET"
        digest, cid = bulk.sha(url.encode()), f"Fixture{i:04d}.tr"
        unique[digest] = {"url": url, "channel_ids": {cid}, "custom_headers": False}
        check = {"url_sha256": digest, "status": "VIDEO_AUDIO_DECODED",
                 "video": True, "audio": True, "decoded": True}
        checks[digest] = check
        rows.append(dict(check, url=url, channel_ids=[cid], probe_status=check["status"], source_ids=["fixture-api"]))
    return summarize(unique, checks), rows


class BulkArchiveAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=3072)

    def evidence_files(self, root, report=None, rows=None, count=1):
        if report is None:
            report, rows = fixture(count)
        private, public, sealed, report_path = (root / name for name in
            ("private.pem", "public.pem", "input.sealed", "report.json"))
        private.write_bytes(self.key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public.write_bytes(self.key.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo))
        seal_rows(rows, public, sealed)
        report["encrypted_evidence"] = {"sha256": bulk.sha(sealed.read_bytes()), "records": len(rows)}
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report_path, sealed, private

    def test_1000_2000_real_crypto_packages_have_exact_counts_and_no_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = self.evidence_files(root, count=2004)
            before = [path.read_bytes() for path in inputs]
            with patch("socket.getaddrinfo", side_effect=AssertionError("No network allowed")), \
                    patch("subprocess.run", side_effect=AssertionError("No rescan allowed")):
                result = bulk.export_batches(*inputs, root / "private-packages")
            counts = {}
            for package in result["packages"]:
                counts.setdefault(package["batch_size"], []).append(package["records"])
                rows = open_rows(root / "private-packages" / package["name"], inputs[2])
                content = bulk.render(rows)
                self.assertEqual(content.count("#EXTINF:"), package["records"])
                self.assertEqual(bulk.sha(content.encode()), package["plaintext_m3u_sha256"])
                self.assertEqual(len({row["url_sha256"] for row in rows}), len(rows))
                self.assertTrue(all(row["decoded"] is True and row["source_ids"] == ["fixture-api"] for row in rows))
            self.assertEqual(counts, {1000: [1000, 1000, 4], 2000: [2000, 4]})
            self.assertEqual(result["eligible_unique_av_urls"], 2004)
            self.assertFalse(result["metadata_acceptance_complete"])
            self.assertEqual([path.read_bytes() for path in inputs], before)
            self.assertEqual((root / "private-packages/all-original-candidates.sealed").read_bytes(), before[1])
            self.assertFalse(any(path.suffix in (".m3u", ".m3u8") for path in (root / "private-packages").iterdir()))
            public_text = (root / "private-packages/acceptance.json").read_text()
            self.assertNotIn("DO_NOT_PRINT_SECRET", public_text)
            self.assertNotIn("https://", public_text)
            self.assertEqual(result["network_requests"], 0)

    def test_lossless_partition_preserves_unverified_and_ambiguous_archived_rows(self):
        report, rows = fixture(3)
        lookup = {row["url_sha256"]: row for row in report["streams"]}
        lookup[rows[0]["url_sha256"]]["channel_ids"] = ["One.tr", "Two.az"]
        rows[0]["channel_ids"] = ["One.tr", "Two.az"]
        for item in (lookup[rows[1]["url_sha256"]], rows[1]):
            item.update(status="VIDEO_AUDIO_STREAMS_ONLY", decoded=False)
        rows[1]["probe_status"] = "VIDEO_AUDIO_STREAMS_ONLY"
        report.update(video_audio_decoded=2, status_counts={"VIDEO_AUDIO_DECODED": 2, "VIDEO_AUDIO_STREAMS_ONLY": 1})
        selected, audit = bulk.accept(report, rows)
        self.assertEqual(len(selected), 1)
        self.assertEqual(audit["classification_counts"], {
            "PENDING_AMBIGUOUS_IDENTITY": 1, "PENDING_AV": 1, "ELIGIBLE_PRIVATE_AV_TEST": 1})
        self.assertEqual(len(audit["candidates"]), 3)
        self.assertEqual(audit["pending_counts"]["INDEPENDENT_BROADCASTER_IDENTITY_UNVERIFIED"], 3)

    def test_legacy_archive_quality_is_pending_never_derived_from_channel_name(self):
        report, rows = fixture()
        report["streams"][0]["name"] = "2160P ULTRA HD"
        _, audit = bulk.accept(report, rows)
        self.assertIsNone(audit["candidates"][0]["measured_video"])
        self.assertEqual(audit["pending_counts"]["MEASURED_VIDEO_QUALITY_UNAVAILABLE"], 1)

    def test_api_summary_carries_actual_measurements_without_manufacturing_legacy_data(self):
        url = "https://cdn.example.org/measurement"
        digest = bulk.sha(url.encode())
        unique = {digest: {"channel_ids": {"Measure.tr"}, "custom_headers": False}}
        measured = [{"width": 1920, "height": 1080, "codec_name": "h264"}]
        checks = {digest: {"status": "VIDEO_AUDIO_DECODED", "video": True, "audio": True,
                           "decoded": True, "video_streams": measured,
                           "video_measurement_origin": "FFPROBE_STREAM_METADATA"}}
        public = summarize(unique, checks)
        self.assertEqual(public["streams"][0]["video_streams"], measured)
        self.assertEqual(public["streams"][0]["video_measurement_origin"], "FFPROBE_STREAM_METADATA")
        legacy, _ = fixture()
        self.assertNotIn("video_streams", legacy["streams"][0])

    def test_exact_authenticated_measurements_and_xmltv_intervals_are_audited(self):
        report, rows = fixture()
        measured = [{"width": 1920, "height": 1080, "codec_name": "h264"}]
        for item in (report["streams"][0], rows[0]):
            item.update(video_streams=measured, video_measurement_origin="FFPROBE_STREAM_METADATA")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.xml"
            path.write_text('<tv><channel id="Fixture0000.tr"/><programme channel="Fixture0000.tr" '
                            'start="20261110000000 +0100" stop="20261110010000 +0100"/></tv>')
            epg, digest = bulk.xmltv_evidence(path)
        _, audit = bulk.accept(report, rows, epg)
        self.assertEqual(audit["candidates"][0]["measured_video"], measured[0])
        self.assertNotIn("EXACT_XMLTV_ID_AND_PROGRAMMES_UNVERIFIED", audit["pending_counts"])
        self.assertEqual(len(digest), 64)
        self.assertFalse(audit["metadata_acceptance_complete"])

    def test_xmltv_collision_and_invalid_programme_do_not_pass_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.xml"
            path.write_text('<tv><channel id="A.tr"/><channel id="A.tr"/><channel id="B.tr"/>'
                            '<programme channel="A.tr" start="20261110000000" stop="20261110010000"/>'
                            '<programme channel="B.tr" start="bad" stop="bad"/></tv>')
            epg, _ = bulk.xmltv_evidence(path)
        self.assertEqual(epg, {"A.tr": False, "B.tr": False})

    def test_mismatched_or_forged_measurement_is_rejected(self):
        for invalid in (None, [{"width": True, "height": 1080, "codec_name": "h264"}],
                        [{"width": 1920, "height": 1080, "codec_name": "https://secret"}]):
            report, rows = fixture()
            report["streams"][0].update(video_streams=[{"width": 1920, "height": 1080, "codec_name": "h264"}],
                                        video_measurement_origin="FFPROBE_STREAM_METADATA")
            rows[0].update(video_streams=invalid, video_measurement_origin="FFPROBE_STREAM_METADATA")
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                bulk.accept(report, rows)

    def test_false_av_hash_identity_and_count_proof_rejected(self):
        report, rows = fixture()
        changes = [("url", "https://cdn.example.org/different"), ("channel_ids", ["Other.tr"]),
                   ("audio", False), ("probe_status", "NO_AV")]
        for field, value in changes:
            bad = deepcopy(rows)
            bad[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                bulk.accept(report, bad)
        for field, value in (("unique_url_candidates", 2), ("probed", 0),
                             ("video_audio_decoded", 0), ("status_counts", {})):
            bad = deepcopy(report)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                bulk.accept(bad, rows)

    def test_zero_verified_noop_and_complete_metadata_claim_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, rows = fixture()
            for item in (report["streams"][0], rows[0]):
                item.update(status="VIDEO_AUDIO_STREAMS_ONLY", decoded=False)
            rows[0]["probe_status"] = "VIDEO_AUDIO_STREAMS_ONLY"
            report.update(video_audio_decoded=0, status_counts={"VIDEO_AUDIO_STREAMS_ONLY": 1})
            inputs = self.evidence_files(root, report, rows)
            destination = root / "private-noop"
            with self.assertRaises(ValueError):
                bulk.export_batches(*inputs, destination)
            self.assertFalse(destination.exists())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = self.evidence_files(root)
            with self.assertRaises(ValueError):
                bulk.export_batches(*inputs, root / "private-incomplete", require_complete=True)
            self.assertFalse((root / "private-incomplete").exists())

    def test_manifest_tamper_and_existing_destination_preserve_prior_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = self.evidence_files(root)
            destination = root / "private-existing"
            destination.mkdir()
            (destination / "keep").write_bytes(b"old evidence")
            with self.assertRaises(ValueError):
                bulk.export_batches(*inputs, destination)
            self.assertEqual((destination / "keep").read_bytes(), b"old evidence")
            inputs[1].write_bytes(inputs[1].read_bytes() + b" ")
            with self.assertRaises(ValueError):
                bulk.export_batches(*inputs, root / "private-tampered")
            self.assertFalse((root / "private-tampered").exists())

    def test_cli_emits_no_plaintext_urls_or_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, sealed, private = self.evidence_files(root)
            stdout, stderr = io.StringIO(), io.StringIO()
            argv = ["--report", str(report), "--sealed", str(sealed), "--private-key", str(private),
                    "--out", str(root / "private-cli")]
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                bulk.main(argv)
            self.assertEqual(json.loads(stdout.getvalue())["eligible_unique_av_urls"], 1)
            self.assertNotIn("https://", stdout.getvalue() + stderr.getvalue())
            self.assertNotIn("DO_NOT_PRINT_SECRET", stdout.getvalue() + stderr.getvalue())
            self.assertNotIn("BEGIN PRIVATE KEY", stdout.getvalue() + stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
