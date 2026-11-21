"""Offline synthetic tests; never fetch Drive, decrypt or access a stream."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from v2.stage4_historical_restore_verify import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def zip_bytes(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return out.getvalue()


class HistoricalReceiptTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.source = root / "producer.zip"
        self.restored = root / "independent-restore.zip"
        self.drive = root / "independent-drive.enc"
        self.archive = b"SIMULATED-CIPHERTEXT-NEVER-REAL-STREAM-URL"
        self.producer = {
            "run_id": "fixture-run", "engine_commit": "fixture-sha",
            "archive": {"schema": 1, "record_count": 3, "sha256": sha(self.archive)},
            "archive_bytes": len(self.archive), "candidates": 2,
            "historical_records": 1, "sources_fetched": 4,
            "all_regions_av": 2, "tr_az_av": 1,
        }
        self.accepted = dict(self.producer, drive={
            "version": "4", "revision_sha256": "a" * 64},
            restored_from="google-drive-independent-runner", restored_records=3)
        self.build()

    def build(self):
        producer_json = (json.dumps(self.producer, sort_keys=True) + "\n").encode()
        restored_json = (json.dumps(self.accepted, sort_keys=True) + "\n").encode()
        producer_zip = zip_bytes({"inventory.enc": self.archive, "receipt.json": producer_json})
        restored_zip = zip_bytes({"accepted.json": restored_json})
        self.source.write_bytes(producer_zip)
        self.restored.write_bytes(restored_zip)
        self.drive.write_bytes(self.archive)
        self.expected = {
            "run_id": "fixture-run", "engine_commit": "fixture-sha",
            "producer_zip_sha256": sha(producer_zip),
            "restore_zip_sha256": sha(restored_zip),
            "producer_receipt_sha256": sha(producer_json),
            "accepted_receipt_sha256": sha(restored_json),
            "archive_sha256": sha(self.archive), "archive_bytes": len(self.archive),
            "archive_records": 3, "candidates": 2, "historical_records": 1,
            "sources_fetched": 4, "all_regions_av": 2, "tr_az_av": 1,
            "drive_version": "4", "drive_revision_sha256": "a" * 64,
        }

    def check(self):
        return verify(self.source, self.restored, self.drive, expected=self.expected)

    def test_matching_receipts_are_historical_only(self):
        result = self.check()
        self.assertTrue(result["offline_artifact_provenance_verified"])
        self.assertFalse(result["new_restore_performed"])
        self.assertFalse(result["turkish_authorized_vault_issue6_accepted"])
        self.assertFalse(result["ci_job_status_checked_by_this_script"])

    def test_modified_drive_ciphertext_rejected(self):
        self.drive.write_bytes(b"damaged")
        with self.assertRaises(ValueError):
            self.check()

    def test_artifact_zip_digest_mismatch_rejected(self):
        self.source.write_bytes(self.source.read_bytes() + b"X")
        with self.assertRaises(ValueError):
            self.check()

    def test_false_transport_rejected_even_with_matching_hashes(self):
        self.accepted["restored_from"] = "local-fixture"
        self.build()
        with self.assertRaisesRegex(ValueError, "Drive restore receipt mismatch"):
            self.check()

    def test_wrong_restored_count_rejected(self):
        self.accepted["restored_records"] = 4
        self.build()
        with self.assertRaisesRegex(ValueError, "Drive restore receipt mismatch"):
            self.check()

    def test_producer_receipt_tampering_rejected(self):
        self.accepted["candidates"] = 7
        self.build()
        with self.assertRaisesRegex(ValueError, "changed the original"):
            self.check()

    def test_duplicate_zip_member_rejected(self):
        out = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(out, "w") as z:
                z.writestr("inventory.enc", self.archive)
                z.writestr("receipt.json", b"{}")
                z.writestr("receipt.json", b"{}")
        self.source.write_bytes(out.getvalue())
        self.expected["producer_zip_sha256"] = sha(out.getvalue())
        with self.assertRaisesRegex(ValueError, "ZIP members"):
            self.check()

    def test_symlink_source_rejected(self):
        link = self.source.parent / "symlink.zip"
        link.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            verify(link, self.restored, self.drive, expected=self.expected)


if __name__ == "__main__":
    unittest.main()
