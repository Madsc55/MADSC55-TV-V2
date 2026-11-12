"""Offline tests of the Drive identity, revision and byte checks."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stage4_drive_archive import DriveArchive, MEDIA, NAME, receipt_archive, sha256


class Stage4DriveArchiveTests(unittest.TestCase):
    def setUp(self):
        self.drive = DriveArchive("test-token")
        self.data = b"test encrypted archive bytes"

    def test_receipt_is_bound_to_the_same_run(self):
        receipt = json.dumps({"run_id": "123", "archive_bytes": len(self.data),
                              "archive": {"sha256": sha256(self.data)}}).encode()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            (directory / "receipt.json").write_bytes(receipt)
            with patch.dict("os.environ", {"EXPECTED_RECEIPT": sha256(receipt), "GITHUB_RUN_ID": "123"}):
                self.assertEqual(receipt_archive(directory), (sha256(self.data), len(self.data)))
                with patch.dict("os.environ", {"GITHUB_RUN_ID": "124"}):
                    with self.assertRaisesRegex(ValueError, "another Actions run"):
                        receipt_archive(directory)

    def test_wrong_same_named_file_is_rejected(self):
        file = {"id": "wrong-file", "name": NAME, "mimeType": MEDIA, "trashed": False,
                "capabilities": {"canEdit": True, "canDownload": True}}
        with patch.object(self.drive, "request", return_value=io.BytesIO(json.dumps({"files": [file]}).encode())):
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                self.drive.file(write=True)

    def test_only_the_pinned_revision_with_original_bytes_can_restore(self):
        for pinned, data in ((True, self.data), (True, self.data.upper()), (False, self.data)):
            meta = json.dumps({"id": "rev", "keepForever": pinned, "size": str(len(self.data))}).encode()
            with self.subTest(pinned=pinned, data=data), tempfile.TemporaryDirectory() as directory:
                directory = Path(directory)
                with patch.object(self.drive, "file", return_value={"id": "private-file"}), patch.object(
                    self.drive, "request", side_effect=[io.BytesIO(meta), io.BytesIO(data)],
                ) as request:
                    if pinned and data == self.data:
                        self.drive.download(directory, sha256(self.data), len(self.data), "rev")
                        self.assertEqual((directory / "inventory.enc").read_bytes(), self.data)
                        self.assertTrue(request.call_args.args[0].endswith("/files/private-file/revisions/rev"))
                    else:
                        with self.assertRaises(ValueError):
                            self.drive.download(directory, sha256(self.data), len(self.data), "rev")
                        if not pinned:
                            request.assert_called_once()
