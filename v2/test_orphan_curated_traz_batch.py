#!/usr/bin/env python3
"""No-network grouped 50-identity tests for new candidate-only feed batch."""
import hashlib
import unittest
from orphan_curated_traz_batch import original_targets, inspect_new_sources


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TwoNewPinnedSourceBatchTests(unittest.TestCase):
    def sample(self):
        sources = {"discevisita-tr": [], "github-auto-24": [],
                   "onureroz-turk-karma": [], "onureroz-turk-all": []}
        docs = {}
        for sid, count in zip(sources, (19,21,8,7)):
            values = ["#EXTINF:-1 tvg-id=\"ch"+str(i)+"\",Name"+str(i)
                      for i in range(count)]
            sources[sid] = [digest(x) for x in values]
            docs[sid] = "#EXTM3U\n" + "\n".join(values)
        # One real duplicate across the two Onureroz publisher lists => 54 IDs.
        # Force five exact cross-source duplicates for the true 55/50 contract.
        karma = docs["onureroz-turk-karma"].splitlines()
        all_ = docs["onureroz-turk-all"].splitlines()
        all_[1:6] = karma[1:6]
        docs["onureroz-turk-all"] = "\n".join(all_)
        sources["onureroz-turk-all"] = [digest(x) for x in all_[1:]]
        return {"sources": sources}, docs

    def test_preserves_all_55_occurrences_and_50_exact_originals(self):
        a,b = self.sample()
        from unittest.mock import patch
        with patch("orphan_curated_traz_batch.reconcile_immutable_sources",
                   return_value={"original_source_occurrences":55}):
            targets=original_targets(a,b)
        self.assertEqual(len(targets),50)
        self.assertTrue(all(x["candidates"] == {} for x in targets))

    def test_no_exact_source_matches_zero_new_claims(self):
        a,b=self.sample()
        from unittest.mock import patch
        with patch("orphan_curated_traz_batch.reconcile_immutable_sources",
                   return_value={"original_source_occurrences":55}):
            targets=original_targets(a,b)
        report, sealed=inspect_new_sources(
            targets, matcher=lambda rows,refs: ({}, {"source_documents_unavailable_count":0}),
            prober=lambda rows: self.fail("No URL may be probed if none matched"))
        self.assertEqual(report["new_candidate_stream_urls_real_ffmpeg_decoded"],0)
        self.assertEqual(report["still_without_new_exact_source_candidate"],50)
        self.assertEqual(sealed, [])

    def test_strict_match_with_actual_decoder_and_sealed_candidate(self):
        a,b=self.sample()
        from unittest.mock import patch
        with patch("orphan_curated_traz_batch.reconcile_immutable_sources",
                   return_value={"original_source_occurrences":55}):
            targets=original_targets(a,b)
        first=targets[0]["extinf_sha256"]
        url="https://public.example.org/strict-evidence.m3u8"
        sha=digest(url)
        candidate={sha: {"url":url}}
        def matcher(rows,refs):
            return {first:candidate}, {"source_documents_unavailable_count":0}
        def prober(rows):
            self.assertEqual(len(rows),1)
            original=rows[0]
            return ([{"url_sha256":sha,"status":"VIDEO_AUDIO_DECODED",
                      "video_stream":True,"audio_stream":True,
                      "ffmpeg_video_audio_decoded":True}],
                    [{"url_sha256":sha}],{sha:[original]})
        report,sealed=inspect_new_sources(targets, matcher=matcher, prober=prober)
        self.assertEqual(report["original_identities_with_new_real_av_evidence"],1)
        self.assertEqual(len(sealed),1)
        self.assertEqual(sealed[0]["url_sha256"],sha)
        self.assertNotIn("://",str(report))

    def test_metadata_only_must_not_pass_video_audio_gate(self):
        a,b=self.sample()
        from unittest.mock import patch
        with patch("orphan_curated_traz_batch.reconcile_immutable_sources",
                   return_value={"original_source_occurrences":55}):
            targets=original_targets(a,b)
        first=targets[0]["extinf_sha256"]
        url="https://public.example.org/no-audio.m3u8"
        sha=digest(url)
        def match(rows,refs):
            return {first:{sha:{"url":url}}},{"source_documents_unavailable_count":0}
        def prober(rows):
            return ([{"url_sha256":sha,"status":"VIDEO_ONLY",
                      "video_stream":True,"audio_stream":False,
                      "ffmpeg_video_audio_decoded":False}],[],{sha:[rows[0]]})
        report,sealed=inspect_new_sources(targets,matcher=match,prober=prober)
        self.assertEqual(report["new_candidate_stream_urls_real_ffmpeg_decoded"],0)
        self.assertFalse(sealed[0]["ffmpeg_video_audio_decoded"])

if __name__ == "__main__":
    unittest.main()
