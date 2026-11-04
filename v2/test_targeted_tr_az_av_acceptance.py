#!/usr/bin/env python3
"""Offline grouped acceptance: targeted TR/AZ metadata is never language proof."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from targeted_tr_az_av_acceptance import (
    target_hint, selected_inventory, build_inventory, validate)
from final_batch_acceptance import sha


class TargetedTrAzAcceptanceTests(unittest.TestCase):
    def test_source_scope_or_exact_metadata_hints_target_but_not_foreign(self):
        cases = [
            ({"name":"Generic","tvg_id":""},{"TR"},True),
            ({"name":"Generic","tvg_id":""},{"AZ","world"},True),
            ({"name":"TRT Haber","tvg_id":"TRTHaber.tr"},{"world"},True),
            ({"name":"AzTV","tvg_id":"AzTV.az"},{"world"},True),
            ({"name":"Generic","tvg_id":""},{"world"},False),
            ({"name":"English News","tvg_id":"News.en"},{"world"},False),
        ]
        for meta, scopes, expected in cases:
            with self.subTest(meta=meta,scopes=scopes):
                self.assertEqual(target_hint({"meta":meta,"scopes":scopes}),expected)

    def test_real_source_hashes_and_provenance_preserved_in_target(self):
        srcs=[{"id":"tr","scope":"TR"},{"id":"world","scope":"world"}]
        url="https://example.org/channel.m3u8"
        outputs=[
            ("tr",[{"url":url,"name":"Unknown","tvg_id":""}],"FETCHED"),
            ("world",[{"url":url,"name":"Unknown","tvg_id":""}],"FETCHED")
        ]
        inventory=build_inventory(outputs,srcs)
        self.assertEqual(len(inventory),1)
        selected=selected_inventory(inventory)
        self.assertEqual(len(selected),1)
        row=selected[sha(url)]
        self.assertEqual(row["source_ids"],{"tr","world"})
        self.assertEqual(row["scopes"],{"TR","world"})
        self.assertEqual(row["url"],url)
        self.assertEqual(sha(row["url"]),sha(url))

    def _fixture(self, directory):
        h=sha("https://example.org/live.m3u8")
        item={"url_sha256":h,"source_ids":["tr"],"name":"TRT 1",
              "language_route":"TR_SOURCE_HINT",
              "audio_tags_not_spoken_language_proof":[],
              "spoken_language_verified":False,
              "status":"VIDEO_AUDIO_DECODED",
              "video":True,"audio":True,"decoded":True,
              "ibo_player_verified":False}
        sealed={"schema":1,"kind":"RSA_OAEP_SHA256_AES256_GCM_ZLIB",
                "records_encrypted":1,"nonce":"DUMMY",
                "wrapped_key":"DUMMY","ciphertext":"DUMMY"}
        payload=json.dumps(sealed).encode()
        filename="target-traz-001.sealed"
        (directory/filename).write_bytes(payload)
        doc={
            "schema":1,"kind":"V2_TR_AZ_METADATA_SCOPED_AV",
            "protected_main_playlist_modified":False,
            "ibo_player_verified":False,
            "spoken_language_verified":0,
            "plaintext_url_in_public_report":False,
            "selection_is_spoken_language_proof":False,
            "target_url_candidates":1,"total_discovered_url_candidates":3,
            "excluded_from_target_scope":2,
            "probed":1,"unprobed":0,"audio_video_decoded":1,
            "av_status_counts":{"VIDEO_AUDIO_DECODED":1},
            "source_fetch_failures":0,"sealed_url_count":1,
            "sealed_artifacts":[{"name":filename,"count":1,
                  "sha256":hashlib.sha256(payload).hexdigest()}],
            "candidates":[item]
        }
        out=directory/"targeted-tr-az-acceptance.json"
        out.write_text(json.dumps(doc))
        return out,doc

    def test_anonymous_target_proof_validates_and_tampering_fails(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            path,doc=self._fixture(directory)
            result=validate(path,require_complete=True)
            self.assertEqual(result["included_target_urls"],1)
            self.assertEqual(result["decoded_video_audio"],1)
            self.assertFalse(result["spoken_language_verified"])
            self.assertFalse(result["ibo_device_verified"])
            doc["candidates"][0]["url"]="https://example.org/private"
            path.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,"PLAINTEXT_URL_FIELD"):
                validate(path)

    def test_unprobed_and_source_outage_refuse_full_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            path,doc=self._fixture(Path(d))
            doc["source_fetch_failures"]=1
            path.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,"INCOMPLETE_TARGET"):
                validate(path,require_complete=True)
            self.assertFalse(validate(path)["source_coverage_complete"])


if __name__=="__main__":
    unittest.main()
