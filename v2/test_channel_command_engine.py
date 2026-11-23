"""No-network acceptance tests: named/ordinal commands never delete channel URLs."""
import unittest
from collections import Counter

from channel_command_engine import (
    operate, record_url, record_name, grouped, parts_for, key,
)
from playlist_parts_manager import split_records, category, checksum, logical


SAMPLE = (
    '#EXTM3U\n'
    '#EXTINF:-1 group-title="⭐ FAVORİLER 1 (62)",Existing favorite\nhttps://sample.test/f\n'
    '#EXTINF:-1 group-title="📺 HABER (73)",News A\nhttps://sample.test/n1\n'
    '#EXTINF:-1 group-title="📺 HABER (73)",News B\nhttps://sample.test/n2\n'
    '#EXTINF:-1 group-title="🗂️ YEDEKLER (1107)",TRT 1\nhttps://sample.test/1\n'
    '#EXTINF:-1 group-title="🗂️ YEDEKLER (1107)",TRT 2\nhttps://sample.test/2\n'
    '#EXTINF:-1 group-title="🗂️ YEDEKLER (1107)",TRT 3\nhttps://sample.test/3\n'
    '#EXTINF:-1 group-title="🗂️ YEDEKLER (1107)",Sözlü TV\nhttps://sample.test/4\n'
    '#EXTINF:-1 group-title="ANA ARŞİV (15703)",Archived A\nhttps://sample.test/a\n'
    '#EXTINF:-1 group-title="TÜRK ARŞİVİ (424)",Turkish A\nhttps://sample.test/t\n'
    '#EXTINF:-1 group-title="YABANCI ARŞİVİ (284)",Turkish abroad\nhttps://sample.test/x\n'
).encode("utf-8")


def run(raw, action, **kw):
    return operate(raw, {"action": action, "expected_sha256": checksum(raw), **kw})


def names_in(raw, group):
    _, buckets, labels = grouped(raw)
    return [record_name(r) for r in buckets[key(group)]]


class ChannelCommandEngineTests(unittest.TestCase):
    def test_favorite_copy_and_user_chosen_order(self):
        out, statuses, report = run(SAMPLE, "copy", source="YEDEKLER",
            target="FAVORİLER 1", channels=["TRT 1", "TRT 2", "TRT 3"],
            position=1)
        self.assertEqual(names_in(out, "FAVORİLER 1")[:4],
                         ["TRT 1", "TRT 2", "TRT 3", "Existing favorite"])
        self.assertEqual(names_in(out, "YEDEKLER"),
                         ["TRT 1", "TRT 2", "TRT 3", "Sözlü TV"])
        self.assertEqual(report["before_total"], 10)
        self.assertEqual(report["after_total"], 13)
        self.assertEqual(report["deleted"], 0)
        self.assertEqual(out.count(b"https://sample.test/1"), 2)
        self.assertIn('FAVORİLER 1 (4)', out.decode())
        self.assertEqual(statuses, {})

    def test_copy_favorite_again_moves_existing_without_duplication(self):
        out, _, _ = run(SAMPLE, "copy", source="YEDEKLER",
                        target="FAVORİLER 1", channels=["TRT 1"], position=1)
        out2, _, report = run(out, "copy", source="YEDEKLER",
                              target="FAVORİLER 1", channels=["TRT 1"], position=2)
        self.assertEqual(report["after_total"], report["before_total"])
        self.assertEqual(names_in(out2, "FAVORİLER 1"), ["Existing favorite", "TRT 1"])

    def test_reorder_exact_positions(self):
        favorite, _, _ = run(SAMPLE, "copy", source="YEDEKLER",
                             target="FAVORİLER 1", channels=["TRT 1", "TRT 2", "TRT 3"],
                             position=1)
        ordered, _, _ = run(favorite, "reorder", source="FAVORİLER 1",
                            channels=["TRT 3", "TRT 1", "TRT 2"], position=1)
        self.assertEqual(names_in(ordered, "FAVORİLER 1")[:3],
                         ["TRT 3", "TRT 1", "TRT 2"])
        self.assertEqual(len(split_records(ordered)[1]), len(split_records(favorite)[1]))

    def test_move_backup_ordinal_to_news_without_deleting(self):
        out, _, report = run(SAMPLE, "move", source="YEDEKLER",
                             target="HABER", channels=[{"position": 4}], position=1)
        self.assertEqual(names_in(out, "HABER"), ["Sözlü TV", "News A", "News B"])
        self.assertEqual(names_in(out, "YEDEKLER"), ["TRT 1", "TRT 2", "TRT 3"])
        self.assertEqual(report["before_total"], report["after_total"])
        self.assertEqual(report["deleted"], 0)
        self.assertIn('YEDEKLER (3)', out.decode())
        self.assertIn('HABER (3)', out.decode())

    def test_foreign_to_turkish_archive(self):
        expanded = SAMPLE + ('#EXTINF:-1 group-title="YABANCI ARŞİVİ (284)",Foreign B\n'
                             'https://sample.test/x2\n').encode()
        out, _, _ = run(expanded, "move", source="YABANCI ARŞİVİ",
                         target="TÜRK ARŞİVİ", channels=["Turkish abroad"])
        self.assertEqual(names_in(out, "TÜRK ARŞİVİ"), ["Turkish A", "Turkish abroad"])
        self.assertEqual(names_in(out, "YABANCI ARŞİVİ"), ["Foreign B"])

    def test_archive_from_news_preserves_url_and_count(self):
        out, _, report = run(SAMPLE, "archive", source="HABER",
                             channels=["News B"], target="ANA ARŞİV")
        self.assertEqual(names_in(out, "HABER"), ["News A"])
        self.assertEqual(names_in(out, "ANA ARŞİV"), ["Archived A", "News B"])
        self.assertEqual(report["after_total"], report["before_total"])
        self.assertEqual(report["deleted"], 0)

    def test_mark_broken_keeps_archive_record(self):
        out, statuses, report = run(SAMPLE, "mark", source="YABANCI ARŞİVİ",
                                     channels=["Turkish abroad"], status="broken")
        self.assertEqual(out, SAMPLE)
        self.assertEqual(len(statuses), 1)
        self.assertEqual(next(iter(statuses.values()))["status"], "broken")
        self.assertEqual(report["deleted"], 0)

    def test_recount_only_corrects_stale_category_labels(self):
        out, _, _ = run(SAMPLE, "recount")
        self.assertIn('FAVORİLER 1 (1)', out.decode())
        self.assertIn('HABER (2)', out.decode())
        self.assertIn('YEDEKLER (4)', out.decode())
        self.assertIn('TÜRK ARŞİVİ (1)', out.decode())
        self.assertEqual(Counter(map(record_url, split_records(out)[1])),
                         Counter(map(record_url, split_records(SAMPLE)[1])))
        before = [x.split(b'group-title="')[0] for x in split_records(SAMPLE)[1]]
        after = [x.split(b'group-title="')[0] for x in split_records(out)[1]]
        self.assertEqual(before, after)

    def test_rejects_stale_sha_and_ambiguous_selector(self):
        with self.assertRaisesRegex(ValueError, "SHA"):
            operate(SAMPLE, {"action": "recount", "expected_sha256": "0" * 64})
        duplicate = SAMPLE.replace(b",Turkish A", b",TRT 1")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            run(duplicate, "copy", target="FAVORİLER 1", channels=["TRT 1"])

    def test_cannot_empty_last_category_or_create_unknown_category(self):
        with self.assertRaisesRegex(ValueError, "Empty categories"):
            run(SAMPLE, "move", source="YABANCI ARŞİVİ",
                target="TÜRK ARŞİVİ", channels=["Turkish abroad"])
        with self.assertRaisesRegex(ValueError, "Unknown category"):
            run(SAMPLE, "copy", source="YEDEKLER",
                target="Invented category", channels=["TRT 1"])

    def test_renamed_parts_reassemble_exactly(self):
        out, _, _ = run(SAMPLE, "recount")
        parts, manifest = parts_for(out, checksum(SAMPLE))
        self.assertEqual(manifest["total_records"], 10)
        self.assertEqual(manifest["source_sha256"], checksum(SAMPLE))
        self.assertEqual(b''.join(parts.values()), out[len(split_records(out)[0]):])
        self.assertTrue(all(logical(category(value)) == entry["group"]
                            for entry in manifest["entries"]
                            for value in split_records(parts[entry["file"]])[1]))


if __name__ == "__main__":
    unittest.main()
