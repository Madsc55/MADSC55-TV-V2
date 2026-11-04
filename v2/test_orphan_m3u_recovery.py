#!/usr/bin/env python3
"""Grouped safety and recovery tests for the three known upstream orphan feeds."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from orphan_m3u_recovery import (
    parse_exact_pairs, find_historical, find_official_alternates, evaluate, audit,
    restore_exact_original_metadata_from_official_alternates,
    exact_channel_identity, exact_no_epg_logo_group_name, reviewed_hanoicab3_identity,
    find_existing_exact_identity,
)


class OrphanRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.dis = "#EXTINF:-1 tvg-id=\"cnn.tr\",CNN Türk"
        self.sun = "#EXTINF:-1 tvg-id=\"k+1\",K+"
        self.onur = "#EXTINF:-1 tvg-id=\"tur.tr\",TR"
        self.a = "https://public.example.org/a.m3u8"
        self.b = "https://public.example.org/b.m3u8"

    def test_only_real_original_extinf_line_matches_archive(self):
        initial = "#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Different\n" + self.a + "\n"
        _, orphans = parse_exact_pairs(initial)
        original = "#EXTM3U\n" + self.dis + "\n" + self.a + "\n"
        matches, counts = find_historical(
            orphans, "discevisita/iptv", "tr.m3u",
            commits=lambda *a, **k: ["a"*40],
            reader=lambda url: original)
        self.assertEqual(len(matches[self.dis]), 1)
        self.assertEqual(counts["historical_files_read"], 1)

    def test_historical_exact_epg_name_with_changed_logo_recovers_candidate(self):
        old_line = '#EXTINF:-1 tvg-id="KanalT.tr" tvg-logo="old.png",Kanal T'
        new_line = '#EXTINF:-1 tvg-id="KanalT.tr" tvg-logo="new.png",Kanal T'
        wrong_line = '#EXTINF:-1 tvg-id="KanalT.tr",Kanal T 2'
        candidates = [
            {"extinf": new_line}, {"extinf": wrong_line}]
        historical = "#EXTM3U\n" + old_line + "\n" + self.a + "\n"
        matches, evidence = find_historical(
            candidates, "discevisita/iptv", "tr.m3u",
            commits=lambda *args, **kwargs: ["a" * 40],
            reader=lambda url: historical)
        sha = hashlib.sha256(self.a.encode()).hexdigest()
        self.assertEqual(matches[new_line][sha]["url"], self.a)
        self.assertEqual(matches[new_line][sha]["proof_rules"],
                         ["EXACT_EPG_ID_AND_NAME"])
        self.assertNotIn(wrong_line, matches)
        self.assertEqual(evidence["historical_files_read"], 1)

    def test_historical_revisions_paginate_and_never_invent_commits(self):
        from orphan_m3u_recovery import historical_revisions
        calls = []
        def fake_read(url, api=False):
            from urllib.parse import parse_qs, urlsplit
            self.assertTrue(api)
            qs = parse_qs(urlsplit(url).query)
            self.assertEqual(qs["per_page"], ["100"])
            page = int(qs["page"][0])
            calls.append(page)
            first = (page - 1) * 100
            count = 100 if page == 1 else 50
            return json.dumps([{"sha": format(first + i + 1, "040x")}
                               for i in range(count)]).encode()
        with patch("orphan_m3u_recovery._read", side_effect=fake_read):
            revs = historical_revisions("Hannstcott/SunshineTr",
                                        "sunshinetv.m3u", limit=150)
        self.assertEqual(len(revs), 150)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(len(set(revs)), 150)

    def test_historical_revisions_duplicate_page_rejected(self):
        from orphan_m3u_recovery import historical_revisions
        def fake_read(url, api=False):
            from urllib.parse import parse_qs, urlsplit
            page = int(parse_qs(urlsplit(url).query)["page"][0])
            return json.dumps([{"sha": format(i + 1, "040x")}
                               for i in range(100 if page == 1 else 1)]).encode()
        with patch("orphan_m3u_recovery._read", side_effect=fake_read):
            with self.assertRaisesRegex(ValueError, "Duplicate historical"):
                historical_revisions("discevisita/iptv", "tr.m3u", limit=101)

    def test_historical_revisions_reject_unbounded_or_unpinned_scope(self):
        from orphan_m3u_recovery import historical_revisions
        with self.assertRaises(ValueError):
            historical_revisions("discevisita/iptv", "tr.m3u", limit=301)
        with self.assertRaises(ValueError):
            historical_revisions("untrusted/iptv", "tr.m3u", limit=100)

    def test_historical_exact_extinf_provenance_remains_explicit(self):
        historical = "#EXTM3U\n" + self.dis + "\n" + self.a + "\n"
        matches, evidence = find_historical(
            [{"extinf": self.dis}], "discevisita/iptv", "tr.m3u",
            commits=lambda *args, **kwargs: ["a" * 40],
            reader=lambda url: historical)
        sha = hashlib.sha256(self.a.encode()).hexdigest()
        self.assertEqual(matches[self.dis][sha]["proof_rules"], ["EXACT_EXTINF"])

    def test_malformed_http_without_host_is_reported_not_played(self):
        from orphan_m3u_recovery import classify_invalid_uri_structure
        self.assertEqual(classify_invalid_uri_structure("http:///missing.m3u8"),
                         "HTTP_URI_WITHOUT_HOST")
        text = "#EXTM3U\n#EXTINF:-1,No host\nhttp:///missing.m3u8\n"
        pairs, orphans = parse_exact_pairs(text)
        self.assertEqual(len(pairs), 0)
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["uri_structure"], "HTTP_URI_WITHOUT_HOST")

    def test_nonpublic_http_is_safely_excluded_but_not_an_orphan(self):
        from orphan_m3u_recovery import count_excluded_network_references
        content = ("#EXTM3U\n#EXTINF:-1,Private\n"
                   "http://192.168.1.10/live.m3u8\n"
                   "#EXTINF:-1,Valid\nhttps://public.example.org/good.m3u8\n")
        rows, orphan = parse_exact_pairs(content)
        self.assertEqual(len(orphan), 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(count_excluded_network_references(content), 1)

    def test_nonoriginal_source_path_cannot_be_sneaked_in(self):
        with self.assertRaisesRegex(ValueError, "outside pinned"):
            find_historical([], "somewhere/unknown", "other.m3u",
                            commits=lambda *a, **k: [])

    def test_unavailable_publisher_can_only_restore_exact_metadata_from_official_source(self):
        original_a = '#EXTINF:-1 tvg-id="One.tr",One'
        original_b = '#EXTINF:-1 tvg-id="Two.tr",Two'
        other = '#EXTINF:-1 tvg-id="Two.tr",Two 2'
        baseline = {"sources": {"onureroz-turk-all": [
            hashlib.sha256(original_a.encode()).hexdigest(),
            hashlib.sha256(original_b.encode()).hexdigest(),
        ]}}
        checked = []
        def read(url):
            checked.append(url)
            if url.endswith("all.m3u"):
                raise ValueError("Not an M3U document")
            return ("#EXTM3U\n" + original_a + "\n" + self.a + "\n"
                    + original_b + "\n" + self.b + "\n"
                    + other + "\n" + self.a + "\n")
        restored = restore_exact_original_metadata_from_official_alternates(
            "onureroz-turk-all", baseline, reader=read)
        paired, orphans = parse_exact_pairs(restored)
        self.assertEqual(paired, {})
        self.assertEqual({r["extinf_sha256"] for r in orphans},
                         set(baseline["sources"]["onureroz-turk-all"]))
        self.assertEqual(len(orphans), 2)
        self.assertNotIn(self.a, restored)
        self.assertNotIn(self.b, restored)
        self.assertTrue(checked)

    def test_unavailable_publisher_missing_one_exact_hash_hard_fails(self):
        original = '#EXTINF:-1 tvg-id="One.tr",One'
        absent = '#EXTINF:-1 tvg-id="Two.tr",Two'
        baseline = {"sources": {"onureroz-turk-karma": [
            hashlib.sha256(original.encode()).hexdigest(),
            hashlib.sha256(absent.encode()).hexdigest(),
        ]}}
        def read(url):
            return "#EXTM3U\n" + original + "\n" + self.a + "\n"
        with self.assertRaisesRegex(ValueError, "EXACT_METADATA_NOT_RECOVERED"):
            restore_exact_original_metadata_from_official_alternates(
                "onureroz-turk-karma", baseline, reader=read)

    def test_partial_onur_official_alternates_do_not_claim_full_recovery(self):
        missing = [{"extinf": self.onur}]
        def read(url):
            if url.endswith("index.m3u"):
                return "#EXTM3U\n" + self.onur + "\n" + self.b
            return "#EXTM3U\n#EXTINF:-1,Other\n" + self.a
        evidence, status = find_official_alternates(missing, reader=read)
        self.assertEqual(len(evidence[self.onur]), 1)
        self.assertEqual(status["official_alternate_feeds_read"], 3)


    def test_official_world_index_requires_exact_identity_for_candidates(self):
        # This URL is explicitly listed by the original publisher.
        wanted = '#EXTINF:-1 tvg-id="TestWorld.tr" tvg-logo="old.png",Test World'
        same_identity = '#EXTINF:-1 tvg-id="TestWorld.tr" tvg-logo="new.png",Test World'
        different_channel = '#EXTINF:-1 tvg-id="TestWorld.tr",Test World 2'
        seen = []
        def read(url):
            seen.append(url)
            if url == "https://onureroz.com/indirmeler/dunya/index.m3u":
                return ("#EXTM3U\n" + same_identity + "\n" + self.a +
                        "\n" + different_channel + "\n" + self.b + "\n")
            return "#EXTM3U\n"
        matched, summary = find_official_alternates([{"extinf": wanted}], reader=read)
        self.assertEqual(len(seen), 3)
        self.assertEqual(summary["official_alternate_feeds_read"], 3)
        self.assertEqual(set(matched), {wanted})
        self.assertEqual(set(matched[wanted]), {hashlib.sha256(self.a.encode()).hexdigest()})
        self.assertEqual(matched[wanted][hashlib.sha256(self.a.encode()).hexdigest()]["proof_rules"],
                         ["EXACT_EPG_ID_AND_NAME_OFFICIAL_ALTERNATE"])


    def test_no_epg_requires_exact_name_group_and_logo(self):
        original = '#EXTINF:-1 tvg-logo="https://logos.example.org/test.png" group-title="Haber",Kanal A'
        same = '#EXTINF:-1 group-title="Haber" tvg-logo="https://logos.example.org/test.png",KANAL A'
        wrong_group = same.replace('group-title="Haber"', 'group-title="Spor"')
        wrong_logo = same.replace("test.png", "other.png")
        self.assertEqual(exact_no_epg_logo_group_name(original),
                         exact_no_epg_logo_group_name(same))
        self.assertNotEqual(exact_no_epg_logo_group_name(original),
                            exact_no_epg_logo_group_name(wrong_group))
        self.assertNotEqual(exact_no_epg_logo_group_name(original),
                            exact_no_epg_logo_group_name(wrong_logo))
        self.assertIsNone(exact_no_epg_logo_group_name('#EXTINF:-1 group-title="Haber",Kanal A'))
        self.assertIsNone(exact_no_epg_logo_group_name(original.replace("tvg-logo", "logo")))
        self.assertIsNone(exact_no_epg_logo_group_name(original.replace("Kanal A", "")))
        self.assertIsNone(exact_no_epg_logo_group_name(original.replace('#EXTINF:-1', '#EXTINF:-1 tvg-id="KanalA.tr"')))

    def test_no_epg_strong_exact_catalog_recovers_candidate_not_av(self):
        original = '#EXTINF:-1 tvg-logo="https://logos.example.org/one.png" group-title="News",One TV'
        changed = '#EXTINF:-1 group-title="News" tvg-logo="https://logos.example.org/one.png",ONE TV'
        orphan = [{"extinf": original, "extinf_sha256": hashlib.sha256(original.encode()).hexdigest()}]
        feed = "#EXTM3U\n" + changed + "\n" + self.a + "\n"
        catalog = [{"id": "reviewed-feed", "url": "https://feeds.example.org/world.m3u"}]
        found, stats = find_existing_exact_identity(orphan, catalog, reader=lambda _: feed)
        sha = hashlib.sha256(self.a.encode()).hexdigest()
        self.assertEqual(found[orphan[0]["extinf_sha256"]][sha]["proof_rules"],
                         ["EXACT_NO_EPG_LOGO_GROUP_NAME"])
        self.assertEqual(stats["orphan_entries_with_exact_no_epg_logo_group_name"], 1)

    def test_no_epg_same_name_only_or_wrong_logo_cannot_match(self):
        original = '#EXTINF:-1 tvg-logo="https://logos.example.org/one.png" group-title="News",One TV'
        altered = '#EXTINF:-1 tvg-logo="https://logos.example.org/two.png" group-title="News",One TV'
        orphan = [{"extinf": original, "extinf_sha256": hashlib.sha256(original.encode()).hexdigest()}]
        catalog = [{"id": "reviewed-feed", "url": "https://feeds.example.org/world.m3u"}]
        found, stats = find_existing_exact_identity(orphan, catalog,
                        reader=lambda _: "#EXTM3U\n" + altered + "\n" + self.a + "\n")
        self.assertFalse(found)
        self.assertEqual(stats["orphan_entries_with_any_exact_existing_match"], 0)

    def test_no_epg_strong_official_alternate_is_only_url_evidence(self):
        original = '#EXTINF:-1 tvg-logo="https://logos.example.org/test.png" group-title="Test",One'
        alternate = '#EXTINF:-1 group-title="Test" tvg-logo="https://logos.example.org/test.png",ONE'
        def read(_):
            return "#EXTM3U\n" + alternate + "\n" + self.b + "\n"
        candidates, stats = find_official_alternates([{"extinf": original}], reader=read)
        sha = hashlib.sha256(self.b.encode()).hexdigest()
        self.assertEqual(candidates[original][sha]["proof_rules"],
                         ["EXACT_NO_EPG_LOGO_GROUP_NAME_OFFICIAL_ALTERNATE"])
        self.assertEqual(stats["official_alternate_feeds_read"], 3)

    def test_no_epg_historical_revisions_allow_strong_identity_only(self):
        original = '#EXTINF:-1 tvg-logo="https://logos.example.org/test.png" group-title="News",ONE TV'
        historical = '#EXTINF:-1 group-title="News" tvg-logo="https://logos.example.org/test.png",One TV'
        matches, stats = find_historical(
            [{"extinf": original}], "discevisita/iptv", "tr.m3u",
            commits=lambda *a, **k: ["a"*40],
            reader=lambda _: "#EXTM3U\n" + historical + "\n" + self.a + "\n")
        sha = hashlib.sha256(self.a.encode()).hexdigest()
        self.assertEqual(matches[original][sha]["proof_rules"],
                         ["EXACT_NO_EPG_LOGO_GROUP_NAME"])
        self.assertEqual(stats["historical_files_read"], 1)


    def test_reviewed_hanoicab3_alias_only_exact_known_epg_and_names(self):
        original = '#EXTINF:-1 tvg-id="antg",Hanoicab 3 | An Ninh Thế Giới'
        alt = '#EXTINF:-1 tvg-id="antg",An Ninh Thế Giới'
        self.assertEqual(reviewed_hanoicab3_identity(original),
                         reviewed_hanoicab3_identity(alt))
        self.assertIsNone(reviewed_hanoicab3_identity(
            '#EXTINF:-1 tvg-id="antv",An Ninh Thế Giới'))
        self.assertIsNone(reviewed_hanoicab3_identity(
            '#EXTINF:-1 tvg-id="antg",An Ninh Thế Giới 2'))
        self.assertIsNone(reviewed_hanoicab3_identity(
            '#EXTINF:-1,Hanoicab 3 | An Ninh Thế Giới'))

    def test_reviewed_hanoicab3_source_name_alias_must_still_be_probed(self):
        original = '#EXTINF:-1 tvg-id="antg",Hanoicab 3 | An Ninh Thế Giới'
        alternate = '#EXTINF:-1 tvg-id="antg",An Ninh Thế Giới'
        record = {"extinf": original,
                  "extinf_sha256": hashlib.sha256(original.encode()).hexdigest()}
        feed = "#EXTM3U\n" + alternate + "\n" + self.a + "\n"
        catalog = [{"id":"verified-public-source", "url":"https://public.example.org/all.m3u"}]
        matched, report = find_existing_exact_identity([record], catalog,
                        reader=lambda _url: feed)
        sha = hashlib.sha256(self.a.encode()).hexdigest()
        proof = matched[record["extinf_sha256"]][sha]
        self.assertEqual(proof["proof_rules"], ["REVIEWED_ANTG_NAME_ALIAS"])
        self.assertEqual(report["orphan_entries_with_reviewed_hanoicab_name_alias"], 1)
        self.assertNotIn("video_stream", proof)


    def test_vendor_malformed_extinf_commas_do_not_hide_real_exact_epg_name(self):
        vtc12 = ('#EXTINF:-1, tvg-id="vtc12hd" group-title="VTC" '
                 'catchup-source="https://history.example.org/catchup",VTC12')
        vtc13 = ('#EXTINF:-1, tvg-id="vtc13hd" group-title="VTC" '
                 'catchup-source="https://history.example.org/catchup",VTC13')
        self.assertEqual(exact_channel_identity(vtc12), ("vtc12hd", "vtc12"))
        self.assertEqual(exact_channel_identity(vtc13), ("vtc13hd", "vtc13"))
        self.assertEqual(exact_channel_identity(
            '#EXTINF:-1 tvg-id="News.tr",News, Europe'),
            ("news.tr", "news, europe"))

    def test_vendor_unclosed_group_quote_restores_only_exact_hanoicab_name(self):
        broken = ('#EXTINF:-1 tvg-id="antg" group-title="VTVCAB" '
                  'tvg-logo="https://logos.example.org/hanoicab.png" '
                  'group-title=" ,Hanoicab 3 | An Ninh Thế Giới')
        good = '#EXTINF:-1 tvg-id="antg",An Ninh Thế Giới'
        self.assertEqual(exact_channel_identity(broken),
                         ("antg", "hanoicab 3 | an ninh thế giới"))
        self.assertEqual(reviewed_hanoicab3_identity(broken),
                         reviewed_hanoicab3_identity(good))
        self.assertIsNone(exact_channel_identity(
            '#EXTINF:-1 tvg-id="antg" group-title="unfinished'))
        self.assertIsNone(exact_channel_identity(
            '#EXTINF:-1 tvg-id="antg" group-title=" ,Wrong,Comma'))

    def test_malformed_vendor_original_retains_sha_exact_alt_and_no_auto_av(self):
        broken = ('#EXTINF:-1 tvg-id="antg" group-title="VTVCAB" '
                  'tvg-logo="https://logos.example.org/h.png" group-title=" ,'
                  'Hanoicab 3 | An Ninh Thế Giới')
        original_sha = hashlib.sha256(broken.encode()).hexdigest()
        orphan = [{"extinf": broken, "extinf_sha256": original_sha}]
        feed = ('#EXTM3U\n#EXTINF:-1 tvg-id="antg",An Ninh Thế Giới\n'
                + self.b + '\n')
        found, report = find_existing_exact_identity(
            orphan, [{"id": "reviewed-vietnam", "url": "https://feeds.example.org/vn.m3u"}],
            reader=lambda _url: feed)
        candidate = found[original_sha][hashlib.sha256(self.b.encode()).hexdigest()]
        self.assertEqual(candidate["proof_rules"], ["REVIEWED_ANTG_NAME_ALIAS"])
        self.assertEqual(report["orphan_entries_with_any_exact_existing_match"], 1)
        self.assertNotIn("video_stream", candidate)

    def test_no_http_url_is_inferred_from_invalid_or_missing_reference(self):
        content = ("#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Next\n" + self.a
                   + "\n#EXTINF:-1,Empty\n/relative/not-an-absolute-url\n")
        urls, missing = parse_exact_pairs(content)
        self.assertEqual(len(missing), 2)
        self.assertEqual(sum(len(s) for s in urls.values()), 1)

    def test_exact_epg_id_and_name_matching_without_fuzzy_guessing(self):
        src = '#EXTINF:-1 tvg-id="ZDF.de" tvg-logo="old.png",ZDF'
        alt = '#EXTINF:-1 tvg-id="ZDF.de" tvg-logo="new.png",ZDF'
        changed_name = '#EXTINF:-1 tvg-id="ZDF.de",ZDFneo'
        self.assertEqual(exact_channel_identity(src), exact_channel_identity(alt))
        self.assertNotEqual(exact_channel_identity(src),
                            exact_channel_identity(changed_name))
        self.assertIsNone(exact_channel_identity('#EXTINF:-1,ZDF'))

    def test_exact_existing_source_match_does_not_invent_url(self):
        src = '#EXTINF:-1 tvg-id="ZDF.de",ZDF'
        orphan = [{"extinf": src, "extinf_sha256": hashlib.sha256(src.encode()).hexdigest()}]
        catalog = [{"id": "already-known", "url": "https://feeds.example.org/world.m3u"}]
        alternate = '#EXTINF:-1 tvg-id="ZDF.de" group-title="Germany",ZDF'
        content = "#EXTM3U\n" + alternate + "\n" + self.b + "\n"
        found, stats = find_existing_exact_identity(
            orphan, catalog, reader=lambda _: content)
        digest = hashlib.sha256(self.b.encode()).hexdigest()
        self.assertEqual(found[orphan[0]["extinf_sha256"]][digest]["url"], self.b)
        self.assertEqual(stats["orphan_entries_with_exact_existing_epg_and_name"], 1)
        self.assertEqual(stats["preconfigured_sources_checked"], 1)
        self.assertEqual(stats["source_documents_unavailable_count"], 0)


    def test_identical_original_extinf_without_epg_id_matches_exactly(self):
        original = '#EXTINF:-1 group-title="World",Unlisted Regional TV'
        orphan = [{"extinf": original,
                   "extinf_sha256": hashlib.sha256(original.encode()).hexdigest()}]
        feed = "#EXTM3U\n" + original + "\n" + self.a + "\n"
        catalog = [{"id": "public-reviewed", "url": "https://feeds.example.org/all.m3u"}]
        found, report = find_existing_exact_identity(
            orphan, catalog, reader=lambda url: feed)
        match = found[orphan[0]["extinf_sha256"]][hashlib.sha256(self.a.encode()).hexdigest()]
        self.assertEqual(match["proof_existing_source_ids"], ["public-reviewed"])
        self.assertEqual(match["proof_rules"], ["EXACT_ORIGINAL_EXTINF"])
        self.assertEqual(report["orphan_entries_with_exact_original_extinf"], 1)
        self.assertEqual(report["orphan_entries_with_any_exact_existing_match"], 1)
        self.assertEqual(report["orphan_entries_with_exact_existing_epg_and_name"], 0)

    def test_without_epg_id_name_only_or_changed_extinf_never_matches(self):
        original = '#EXTINF:-1 group-title="World",Unlisted Regional TV'
        orphan = [{"extinf": original,
                   "extinf_sha256": hashlib.sha256(original.encode()).hexdigest()}]
        altered = '#EXTINF:-1 group-title="Other",Unlisted Regional TV'
        feed = "#EXTM3U\n" + altered + "\n" + self.a + "\n"
        catalog = [{"id": "public-reviewed", "url": "https://feeds.example.org/all.m3u"}]
        found, report = find_existing_exact_identity(
            orphan, catalog, reader=lambda url: feed)
        self.assertFalse(found)
        self.assertEqual(report["orphan_entries_with_any_exact_existing_match"], 0)
        self.assertEqual(report["orphan_entries_with_exact_original_extinf"], 0)

    def test_tampered_original_sha_never_enters_exact_source_recovery(self):
        original = '#EXTINF:-1,Unknown TV'
        orphan = [{"extinf": original, "extinf_sha256": "0" * 64}]
        with self.assertRaises(ValueError):
            find_existing_exact_identity(orphan, [])

    def test_probe_dedup_and_no_plaintext_in_public_report(self):
        c = {"url": self.a, "proof_commits": ["a"*40]}
        entry = {"source_id": "discevisita-tr", "extinf_sha256": "x"*64,
                 "extinf": self.dis,
                 "candidates": {hashlib.sha256(self.a.encode()).hexdigest(): c}}
        def verified(item):
            return {"url_sha256": item[0], "status": "VIDEO_STREAM_OBSERVED",
                    "video_stream": True, "audio_stream": True}
        p, rows, m = evaluate([entry, entry], probe=verified)
        self.assertEqual(len(p), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], self.a)
        self.assertIn(entry, m[p[0]["url_sha256"]])

    def test_failed_historical_candidates_preserved_for_retest(self):
        from orphan_m3u_recovery import sealed_retest_candidate_rows
        url = self.a
        digest = hashlib.sha256(url.encode()).hexdigest()
        orphan = {"source_id": "discevisita-tr", "extinf_sha256": "a" * 64,
                  "candidates": {digest: {"url": url,
                                         "proof_commits": ["b" * 40],
                                         "proof_rules": ["EXACT_EXTINF"]}}}
        state = {digest: {"url_sha256": digest,
                          "status": "PROBE_FAILED_NOT_PROVEN_DEAD",
                          "video_stream": False, "audio_stream": False}}
        rows = sealed_retest_candidate_rows([orphan], state)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url_sha256"], digest)
        self.assertEqual(rows[0]["proof_commits"], ["b" * 40])
        self.assertEqual(rows[0]["source_ids"], ["discevisita-tr"])
        self.assertTrue(rows[0]["needs_retest"])

    def test_same_stream_in_two_sources_keeps_both_provenances(self):
        from orphan_m3u_recovery import sealed_retest_candidate_rows
        digest = hashlib.sha256(self.a.encode()).hexdigest()
        sources = [
            {"source_id": "source-a", "extinf_sha256": "a" * 64,
             "candidates": {digest: {"url": self.a}}},
            {"source_id": "source-b", "extinf_sha256": "b" * 64,
             "candidates": {digest: {"url": self.a}}}]
        probes = {digest: {"status": "VIDEO_STREAM_OBSERVED",
                           "video_stream": True, "audio_stream": True}}
        rows = sealed_retest_candidate_rows(sources, probes)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_ids"], ["source-a", "source-b"])
        self.assertEqual(rows[0]["orphan_extinf_sha256"], ["a" * 64, "b" * 64])
        self.assertFalse(rows[0]["needs_retest"])

    def test_all_candidates_are_sealed_only_in_private_archive(self):
        line = self.dis
        def reader(url):
            if "discevisita/iptv/main" in url:
                return "#EXTM3U\n" + line + "\n"
            if "discevisita/iptv/" in url:
                return "#EXTM3U\n" + line + "\n" + self.a + "\n"
            return "#EXTM3U\n"
        def failed(item):
            return {"url_sha256": item[0], "status": "PROBE_FAILED_NOT_PROVEN_DEAD",
                    "video_stream": False, "audio_stream": False}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with patch("orphan_m3u_recovery.seal_rows", return_value=1) as seal:
                result = audit(
                    report_path=path / "public.json",
                    sealed_path=path / "av.sealed",
                    all_candidates_sealed_path=path / "all.sealed",
                    key_path=path / "unused.pem", limit=1,
                    reader=reader, commits=lambda *args, **kwargs: ["a" * 40],
                    probe=failed)
                self.assertEqual(seal.call_count, 1)
                rows = seal.call_args.args[0]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["url"], self.a)
                self.assertTrue(rows[0]["needs_retest"])
                self.assertEqual(seal.call_args.args[2], path / "all.sealed")
            self.assertEqual(result["all_proven_url_candidates_sealed_for_future_retest"], 1)
            self.assertEqual(result["currently_unverified_candidate_urls_preserved_in_encrypted_archive"], 1)
            self.assertNotIn(self.a, (path / "public.json").read_text())

    def test_candidate_archive_never_overwrites_existing_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            exists = path / "existing.sealed"
            exists.write_text("PRESERVE")
            with self.assertRaisesRegex(ValueError, "Refusing overwrite"):
                audit(report_path=path / "public.json",
                      sealed_path=path / "av.sealed",
                      all_candidates_sealed_path=exists,
                      key_path=path / "unused.pem", reader=lambda _: "#EXTM3U\n")
            self.assertEqual(exists.read_text(), "PRESERVE")

    def test_source_now_repairs_exact_old_metadata_not_same_name_guess(self):
        from orphan_m3u_recovery import candidate_repairs_from_current_verified_sources
        meta = '#EXTINF:-1 tvg-id="T.tr",TR TV'
        docs = {
            "discevisita-tr": "#EXTM3U\n" + meta +
                             "\nhttps://example.org/new-current.m3u8\n",
            "github-auto-24": "#EXTM3U\n",
            "onureroz-turk-karma": "#EXTM3U\n",
            "onureroz-turk-all": "#EXTM3U\n",
        }
        baseline = {"sources": {k: [] for k in docs}}
        baseline["sources"]["discevisita-tr"] = [
            hashlib.sha256(meta.encode()).hexdigest()]
        results = candidate_repairs_from_current_verified_sources(baseline, docs)
        self.assertEqual(len(results), 1)
        one = results[0]
        self.assertEqual(one["reason"], "UPSTREAM_ORIGINAL_URI_RESTORED")
        self.assertEqual(one["source_id"], "discevisita-tr")
        self.assertEqual(len(one["candidates"]), 1)
        self.assertTrue(next(iter(one["candidates"].values()))[
            "proof_original_upstream_now_has_uri"])
        self.assertEqual(one["uri_structure"], "PUBLIC_ABSOLUTE_HTTP_URI")

    def test_current_upstream_fix_is_ffprobed_and_not_published(self):
        meta = '#EXTINF:-1 tvg-id="T.tr",TR TV'
        baseline = {"sources": {
            "discevisita-tr": [hashlib.sha256(meta.encode()).hexdigest()],
            "github-auto-24": [],
            "onureroz-turk-karma": [],
            "onureroz-turk-all": []}}
        current = "#EXTM3U\n" + meta + "\nhttps://example.org/new-current.m3u8\n"
        def reader(url):
            if "discevisita/iptv/main" in url:
                return current
            return "#EXTM3U\n"
        def probe(item):
            return {"url_sha256": item[0], "status": "VIDEO_STREAM_OBSERVED",
                    "video_stream": True, "audio_stream": True}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with (patch("orphan_baseline_guard.load_immutable_baseline",
                        return_value=baseline),
                  patch("orphan_m3u_recovery.seal_rows", return_value=1)):
                output = audit(
                    report_path=path / "public.json",
                    sealed_path=path / "private.sealed",
                    all_candidates_sealed_path=path / "all.sealed",
                    immutable_orphan_baseline_path=path / "mock-source-baseline.json",
                    key_path=path / "unused.pem",
                    reader=reader,
                    commits=lambda *args, **kwargs: [],
                    probe=probe)
            self.assertEqual(output["restored_current_upstream_uri_occurrences"], 1)
            self.assertEqual(output["currently_unpaired_source_occurrences"], 0)
            self.assertEqual(output["unique_candidates_video_audio_verified"], 1)
            self.assertEqual(output["immutable_orphan_identity_guard"]["status"],
                             "NO_ORIGINAL_METADATA_IDENTITY_LOSS")
            self.assertNotIn("example.org", (path / "public.json").read_text())


    def test_verified_public_document_exact_identity_recovery_only(self):
        """New Archive evidence must not change exact-identity semantics."""
        from orphan_m3u_recovery import find_existing_exact_identity
        missing = [
            {"extinf": self.dis, "extinf_sha256": hashlib.sha256(self.dis.encode()).hexdigest()},
            {"extinf": self.onur, "extinf_sha256": hashlib.sha256(self.onur.encode()).hexdigest()},
        ]
        src = {"id": "docref-reviewed", "url": "https://archive.org/download/iptv-list/tr.m3u",
               "kind": "m3u", "scope": "candidate",
               "origin": "public-document-reference"}
        exact = "#EXTM3U\n" + self.dis + "\n" + self.a + "\n"
        wrong = '#EXTINF:-1 tvg-id="different.tr",CNN Türk'
        content = exact + wrong + "\n" + self.b + "\n"
        fetched = []
        def doc_fetch(url):
            fetched.append(url)
            return content
        matched, report = find_existing_exact_identity(
            missing, [src], reader=lambda u: self.fail("Must use guarded document reader"),
            doc_reader=doc_fetch, doc_resolver=lambda url: True)
        self.assertEqual(len(matched), 1)
        self.assertEqual(report["vetted_public_document_sources_checked"], 1)
        self.assertEqual(report["orphan_entries_with_exact_existing_epg_and_name"], 1)
        key = missing[0]["extinf_sha256"]
        self.assertEqual(matched[key][hashlib.sha256(self.a.encode()).hexdigest()]
                         ["proof_existing_source_ids"], ["docref-reviewed"])
        self.assertEqual(fetched, [src["url"]])

    def test_document_source_private_dns_blocks_fetch_and_candidate(self):
        from orphan_m3u_recovery import find_existing_exact_identity
        missing = [{"extinf": self.dis,
                    "extinf_sha256": hashlib.sha256(self.dis.encode()).hexdigest()}]
        src = {"id": "docref-reviewed", "url": "https://archive.org/download/public/list.m3u",
               "kind": "m3u", "scope": "candidate",
               "origin": "public-document-reference"}
        matched, report = find_existing_exact_identity(
            missing, [src], reader=lambda u: self.fail("Wrong reader"),
            doc_reader=lambda u: self.fail("Untrusted DNS must prevent fetch"),
            doc_resolver=lambda url: False)
        self.assertEqual(dict(matched), {})
        self.assertEqual(report["source_documents_unavailable_count"], 1)

    def test_document_source_invalid_header_is_not_promoted(self):
        from orphan_m3u_recovery import find_existing_exact_identity
        missing = [{"extinf": self.dis,
                    "extinf_sha256": hashlib.sha256(self.dis.encode()).hexdigest()}]
        src = {"id": "docref-reviewed", "url": "https://archive.org/download/public/list.m3u",
               "kind": "m3u", "scope": "candidate",
               "origin": "public-document-reference"}
        matched, report = find_existing_exact_identity(
            missing, [src], doc_reader=lambda url: self.dis+"\n"+self.a,
            doc_resolver=lambda url: True)
        self.assertEqual(dict(matched), {})
        self.assertEqual(report["source_documents_unavailable_count"], 1)


    def test_catalog_preserves_63_sources_and_adds_reviewed_public_documents(self):
        from orphan_m3u_recovery import existing_source_catalog
        from document_platform_discovery import digest
        rows = []
        for name in ("a.m3u", "b.m3u8"):
            url = "https://archive.org/download/public-record/" + name
            rows.append({"id": "docref-" + digest(url)[:20], "url": url,
                         "kind": "m3u", "scope": "candidate",
                         "origin": "public-document-reference"})
        with patch("document_platform_discovery.accepted_sources", return_value=rows):
            result = existing_source_catalog()
        self.assertEqual(len(result), 65)
        self.assertEqual(len(result[:63]), 63)
        self.assertEqual(len({item["id"] for item in result}), len(result))
        self.assertEqual(len([x for x in result
            if x.get("origin") == "public-document-reference"]), 2)
        self.assertTrue(all(x["id"].startswith("docref-") for x in result[-2:]))

    def test_catalog_does_not_duplicate_existing_source_url(self):
        from orphan_m3u_recovery import existing_source_catalog
        with patch("document_platform_discovery.accepted_sources", return_value=[]):
            original = existing_source_catalog()
        duplicated = dict(original[0], origin="public-document-reference")
        with patch("document_platform_discovery.accepted_sources",
                   return_value=[duplicated]):
            result = existing_source_catalog()
        self.assertEqual(len(result), 63)

    def test_end_to_end_four_source_batch_and_sealed_only_for_verified_av(self):
        def reader(url):
            if "discevisita/iptv/main" in url:
                return "#EXTM3U\n" + self.dis + "\n#EXTINF:-1,Safe\n" + self.a
            if "SunshineTr/main" in url:
                return "#EXTM3U\n" + self.sun + "\n#EXTINF:-1,Safe\n" + self.b
            if "/karma-index.m3u" in url:
                return "#EXTM3U\n" + self.onur + "\n/relative.m3u8"
            if url.endswith("/all.m3u"):
                return "#EXTM3U\n" + self.onur + "\n/relative.m3u8"
            if "discevisita/iptv/" in url:
                return "#EXTM3U\n" + self.dis + "\n" + self.a
            if "SunshineTr/" in url:
                return "#EXTM3U\n#EXTINF:-1,Other\n" + self.b
            if url.endswith("/index.m3u"):
                return "#EXTM3U\n" + self.onur + "\n" + self.b
            return "#EXTM3U\n"
        def probe(item):
            return {"url_sha256": item[0], "status": "VIDEO_STREAM_OBSERVED",
                    "video_stream": True, "audio_stream": item[1] == self.a}
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/"public.json"
            sealed = Path(directory)/"private.sealed"
            with patch("orphan_m3u_recovery.seal_rows") as seal:
                res = audit(report_path=report, sealed_path=sealed,
                            key_path=Path(directory)/"unused.pem", limit=1,
                            reader=reader,
                            commits=lambda *a, **k: ["a"*40], probe=probe)
                seal.assert_called_once()
                self.assertEqual(len(seal.call_args.args[0]), 1)
            public = report.read_text()
            self.assertEqual(res["orphan_entries"], 4)
            self.assertEqual(res["unique_orphan_metadata_identities"], 3)
            self.assertEqual(res["duplicate_orphan_occurrences"], 1)
            self.assertEqual(res["unique_candidates_video_audio_verified"], 1)
            self.assertEqual(res["orphan_entries_without_current_av"], 3)
            self.assertNotIn(self.a, public)
            self.assertNotIn(self.b, public)
            self.assertNotIn("CNN Türk", public)


if __name__ == "__main__":
    unittest.main()
