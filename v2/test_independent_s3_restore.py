#!/usr/bin/env python3
"""Grouped offline remote retrieval tests; actual production run uses AWS."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from archive_acceptance_gate import BASELINE
from historical_inventory_guard import preserve_to_new_archive
from independent_s3_restore import restore_s3_version

class RemoteRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.source = Path(cls.tmp.name) / "source.enc"
        history = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            preserve_to_new_archive(cls.source, history, [])
        cls.sha = hashlib.sha256(cls.source.read_bytes()).hexdigest()

    def test_mock_remote_copy_decrypts_all_real_baseline_hashes(self):
        def copy_from_remote(command, **kwargs):
            self.assertEqual(command[:3], ["aws", "s3api", "get-object"])
            shutil.copyfile(self.source, command[-1])
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            self.assertEqual(
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=copy_from_remote), self.sha)

    def test_s3_object_key_reserved_uri_characters_restore(self):
        # Real S3 keys may contain #, ?, spaces and percent characters.
        # Evidence must represent the same object without URI fragment/query loss.
        from archive_acceptance_gate import check
        key = "v2/private archive#1?revision%20.enc"
        def copy_from_remote(command, **kwargs):
            self.assertEqual(command[command.index("--key") + 1], key)
            shutil.copyfile(self.source, command[-1])
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            self.assertEqual(restore_s3_version("versioned-bucket", key,
                "version-one", self.sha, runner=copy_from_remote), self.sha)

    def test_s3_retrieval_timeout_is_bounded_and_configurable(self):
        observed = []
        def copy_from_remote(command, **kwargs):
            observed.append(kwargs["timeout"])
            shutil.copyfile(self.source, command[-1])
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32,
                                  "V2_S3_RESTORE_TIMEOUT_SECONDS": "1200"}):
            self.assertEqual(restore_s3_version("versioned-bucket", "v2/archive.enc",
                             "version-one", self.sha, runner=copy_from_remote), self.sha)
        self.assertEqual(observed, [1200])

    def test_invalid_s3_timeout_is_rejected_before_remote_access(self):
        def must_not_run(command, **kwargs):
            self.fail("Invalid timeout must not reach S3")
        for invalid in ("0", "-1", "3601", "NaN", "29"):
            with self.subTest(timeout=invalid):
                with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32,
                                          "V2_S3_RESTORE_TIMEOUT_SECONDS": invalid}):
                    with self.assertRaisesRegex(ValueError, "timeout"):
                        restore_s3_version("versioned-bucket", "v2/archive.enc",
                                           "version-one", self.sha, runner=must_not_run)

    def test_matching_version_with_wrong_pinned_digest_is_rejected(self):
        def copy_from_remote(command, **kwargs):
            shutil.copyfile(self.source, command[-1])
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(RuntimeError, "pinned original checksum"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", "0" * 64, runner=copy_from_remote)

    def test_remote_timeout_fails_closed_without_restore_acceptance(self):
        calls = []
        def timed_out(command, **kwargs):
            calls.append(kwargs["timeout"])
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32,
                                  "V2_S3_RESTORE_TIMEOUT_SECONDS": "60"}):
            with self.assertRaises(subprocess.TimeoutExpired):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=timed_out)
        self.assertEqual(calls, [60])

    def test_missing_or_malformed_remote_version_metadata_is_rejected(self):
        for payload in ('{}', 'not-json', '[]', '{"VersionId": null}'):
            with self.subTest(payload=payload):
                def copy_from_remote(command, **kwargs):
                    shutil.copyfile(self.source, command[-1])
                    return SimpleNamespace(stdout=payload)
                with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
                    with self.assertRaises((RuntimeError, ValueError)):
                        restore_s3_version("versioned-bucket", "v2/archive.enc",
                                           "version-one", self.sha, runner=copy_from_remote)

    def test_s3_success_metadata_without_download_is_rejected(self):
        def no_file(command, **kwargs):
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(RuntimeError, "regular encrypted archive"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=no_file)

    def test_s3_symlink_download_is_rejected(self):
        def symlink_file(command, **kwargs):
            Path(command[-1]).symlink_to(self.source)
            return SimpleNamespace(stdout=json.dumps({"VersionId": "version-one"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(RuntimeError, "regular encrypted archive"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=symlink_file)

    def test_missing_private_key_prevents_remote_request(self):
        def must_not_run(command, **kwargs):
            self.fail("S3 must not be contacted without archive key")
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": ""}):
            with self.assertRaisesRegex(RuntimeError, "Missing private archive key"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=must_not_run)

    def test_invalid_archive_key_is_rejected_before_remote_request(self):
        def must_not_run(command, **kwargs):
            self.fail("Invalid archive key must not reach S3")
        for invalid in ("a" * 63, "z" * 64, "a" * 65, "ab" * 31 + "zz"):
            with self.subTest(key_length=len(invalid)):
                with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": invalid}):
                    with self.assertRaisesRegex(RuntimeError, "invalid private archive key"):
                        restore_s3_version("versioned-bucket", "v2/archive.enc",
                                           "version-one", self.sha, runner=must_not_run)

    def test_s3_key_utf8_byte_limit_and_del_rejected_before_network(self):
        def must_not_run(command, **kwargs):
            self.fail("Invalid S3 key must not reach remote retrieval")
        invalid_keys = ("é" * 513, "v2/archive" + chr(127) + ".enc", "")
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            for key in invalid_keys:
                with self.subTest(key_length=len(key)):
                    with self.assertRaisesRegex(ValueError, "S3 object key"):
                        restore_s3_version("versioned-bucket", key,
                                           "version-one", self.sha, runner=must_not_run)

    def test_malformed_bucket_dns_names_rejected_before_s3(self):
        def must_not_run(command, **kwargs):
            self.fail("Invalid bucket must not reach remote retrieval")
        invalid = ("abc..def", "abc.-def", "abc-.def", "192.168.1.1",
                   "abc_def", "a" * 64)
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            for bucket in invalid:
                with self.subTest(bucket=bucket):
                    with self.assertRaisesRegex(ValueError, "S3 bucket"):
                        restore_s3_version(bucket, "v2/archive.enc",
                                           "version-one", self.sha, runner=must_not_run)

    def test_null_version_is_mutable_and_rejected_before_s3(self):
        def must_not_run(command, **kwargs):
            self.fail("Mutable null version must never be downloaded")
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "null", self.sha, runner=must_not_run)

    def test_del_in_version_rejected_before_remote_access(self):
        def must_not_run(command, **kwargs):
            self.fail("Control character in version must not reach S3")
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(ValueError, "immutable"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version" + chr(127), self.sha, runner=must_not_run)

    def test_bad_remote_version_and_digest_are_rejected(self):
        def copy_from_remote(command, **kwargs):
            shutil.copyfile(self.source, command[-1])
            return SimpleNamespace(stdout=json.dumps({"VersionId": "wrong-version"}))
        with patch.dict(os.environ, {"V2_ARCHIVE_KEY_HEX": "ab" * 32}):
            with self.assertRaisesRegex(RuntimeError, "version"):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "version-one", self.sha, runner=copy_from_remote)
            with self.assertRaises(ValueError):
                restore_s3_version("versioned-bucket", "v2/archive.enc",
                                   "", self.sha, runner=copy_from_remote)

if __name__ == "__main__":
    unittest.main(verbosity=2)
