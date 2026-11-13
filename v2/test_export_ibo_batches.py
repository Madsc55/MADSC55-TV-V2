import json
import tempfile
import unittest
from pathlib import Path
from secure_archive import encrypt
from export_ibo_batches import export, render, valid_stream_url

SECRET = 'test-only-archive-password-12345'

class BatchTests(unittest.TestCase):
    def test_exact_verified_counts_and_existing_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for i in range(2005):
                rows.append({'url': f'https://example.invalid/stream/{i}', 'name': f'Channel {i}',
                             'group': 'TR', 'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'})
            rows.append({'url': 'https://example.invalid/failed', 'name': 'Failed',
                         'http_hls_status': 'UNVERIFIED_OR_FAILED'})
            rows.append(dict(rows[0]))
            encrypted = root / 'inventory.enc'
            encrypted.write_bytes(encrypt(('\n'.join(json.dumps(x) for x in rows)+'\n').encode(), SECRET))
            result = export(encrypted, SECRET, root / 'out', existing={rows[0]['url']})
            self.assertEqual(result['av_verified_unique'], 2004)
            groups = {}
            for package in result['packages']:
                groups.setdefault(package['batch_size'], []).append(package['count'])
                data = Path(package['path']).read_text()
                self.assertTrue(data.startswith('#EXTM3U\n'))
                self.assertEqual(data.count('#EXTINF:'), package['count'])
                self.assertNotIn(rows[0]['url'], data)
                self.assertNotIn('https://example.invalid/failed', data)
            self.assertEqual(groups[1000], [1000, 1000, 4])
            self.assertEqual(groups[2000], [2000, 4])

    def test_existing_package_is_never_removed_or_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'url': 'https://example.invalid/stream/1', 'name': 'One',
                   'group': 'TR', 'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'}
            archive = root / 'inventory.enc'
            archive.write_bytes(encrypt((json.dumps(row)+'\n').encode(), SECRET))
            output = root / 'out'
            output.mkdir()
            exact = output / 'IBO_AV_VERIFIED_1000_PART1.m3u8'
            exact.write_bytes(b'ORIGINAL_PACKAGE')
            with self.assertRaises(FileExistsError):
                export(archive, SECRET, output, sizes=(1000,))
            self.assertEqual(exact.read_bytes(), b'ORIGINAL_PACKAGE')
            exact.unlink()
            historical = output / 'IBO_AV_VERIFIED_2000_PART1.m3u8'
            historical.write_bytes(b'OLDER_PACKAGE_KEEP')
            result = export(archive, SECRET, output, sizes=(1000,))
            self.assertEqual(result['av_verified_unique'], 1)
            self.assertEqual(historical.read_bytes(), b'OLDER_PACKAGE_KEEP')
            self.assertEqual(len(result['packages']), 1)

    def test_output_preflight_rejects_partial_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [{'url': f'https://example.invalid/stream/{i}', 'name': str(i),
                     'group': 'TR', 'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'}
                    for i in range(2)]
            archive = root / 'inventory.enc'
            archive.write_bytes(encrypt(('\n'.join(json.dumps(x) for x in rows)+'\n').encode(), SECRET))
            output = root / 'out'
            output.mkdir()
            blocked = output / 'IBO_AV_VERIFIED_2000_PART1.m3u8'
            blocked.write_bytes(b'KEEP')
            with self.assertRaises(FileExistsError):
                export(archive, SECRET, output, sizes=(1000, 2000))
            self.assertFalse((output / 'IBO_AV_VERIFIED_1000_PART1.m3u8').exists())
            self.assertEqual(blocked.read_bytes(), b'KEEP')
            with self.assertRaises(ValueError):
                export(archive, SECRET, output, sizes=(1000, 1000))
            self.assertFalse((output / 'IBO_AV_VERIFIED_1000_PART1.m3u8').exists())
            for size in (0, -1, True):
                with self.subTest(size=size), self.assertRaises(ValueError):
                    export(archive, SECRET, output, sizes=(size,))

    def test_legacy_metadata_only_av_record_cannot_be_reexported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # The old scanner marked codec headers as AV_VERIFIED without decoding.
            rows = [
                {"url": "https://example.invalid/legacy", "name": "Legacy",
                 "http_hls_status": "AV_VERIFIED"},
                {"url": "https://example.invalid/string-flag", "name": "Spoof",
                 "http_hls_status": "AV_VERIFIED",
                 "decoded_av_verified": "true", "decode_status": "DECODED_AV"},
                {"url": "https://example.invalid/no-decode", "name": "Not decoded",
                 "http_hls_status": "AV_VERIFIED",
                 "decoded_av_verified": True, "decode_status": "NOT_DECODED_THIS_RUN"},
            ]
            encrypted = root / "historical.enc"
            encrypted.write_bytes(encrypt(
                ("\n".join(json.dumps(row) for row in rows) + "\n").encode(), SECRET))
            output = root / "packages"
            result = export(encrypted, SECRET, output, sizes=(1000,))
            self.assertEqual(result["av_verified_unique"], 0)
            self.assertEqual(result["packages"], [])
            self.assertFalse(list(output.glob("*.m3u8")))

    def test_symlink_output_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'url': 'https://example.invalid/stream/1', 'name': 'One',
                   'group': 'TR', 'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'}
            archive = root / 'inventory.enc'
            archive.write_bytes(encrypt((json.dumps(row)+'\n').encode(), SECRET))
            protected = root / 'protected'
            protected.mkdir()
            link = root / 'out-link'
            link.symlink_to(protected, target_is_directory=True)
            with self.assertRaises(ValueError):
                export(archive, SECRET, link, sizes=(1000,))
            self.assertEqual(list(protected.iterdir()), [])


    def test_untrusted_stream_urls_cannot_inject_m3u_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_urls = (
                "https://example.invalid/live\n#EXTINF:-1,INJECTED\nhttps://bad.invalid/injected",
                "https://example.invalid/live\r#EXTINF:-1,INJECTED",
                "https://example.invalid/live\tother",
                "https://example.invalid:99999/live",
                "https://user:secret@example.invalid/live",
                "https://[broken/path",
                "https://example.invalid/live path",
            )
            records = [{'url': url, 'name': 'Bad', 'group': 'TR',
                        'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'} for url in bad_urls]
            records.append({'url': 'https://example.invalid/good', 'name': 'Good',
                            'group': 'TR', 'http_hls_status': 'AV_VERIFIED',
                             'decoded_av_verified': True, 'decode_status': 'DECODED_AV'})
            for bad in bad_urls:
                self.assertFalse(valid_stream_url(bad))
                with self.assertRaises(ValueError):
                    render([{'url': bad, 'name': 'Bad'}])
            archive = root / 'inventory.enc'
            archive.write_bytes(encrypt(('\n'.join(json.dumps(x) for x in records) + '\n').encode(), SECRET))
            result = export(archive, SECRET, root / 'out', sizes=(1000,))
            self.assertEqual(result['av_verified_unique'], 1)
            out = Path(result['packages'][0]['path']).read_text()
            self.assertEqual(out.count('#EXTINF:'), 1)
            self.assertNotIn('INJECTED', out)
            self.assertIn('https://example.invalid/good', out)

    def test_metadata_controls_do_not_create_fake_m3u_rows(self):
        records = [{'url': 'https://example.invalid/good',
                    'name': 'News\n#EXTINF:-1,Fake',
                    'group': 'TR\r\n#EXTINF:-1,Fake',
                    'logo': 'https://example.invalid/logo.png\n#EXTINF:-1,Fake'}]
        output = render(records).decode()
        self.assertEqual(sum(line.startswith('#EXTINF:') for line in output.splitlines()), 1)
        self.assertEqual(len(output.splitlines()), 3)
        self.assertNotIn('tvg-logo=', output)
        self.assertIn('https://example.invalid/good', output)

    def test_unicode_line_separators_cannot_create_fake_channels(self):
        for separator in ("\u0085", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                record = {
                    "url": "https://example.invalid/safe.m3u8",
                    "name": "News" + separator + "#EXTINF:-1,FAKE",
                    "group": "TR" + separator + "#EXTINF:-1,FAKE",
                }
                output = render([record]).decode("utf-8")
                self.assertEqual(len(output.splitlines()), 3)
                self.assertEqual(sum(line.startswith("#EXTINF:") for line in output.splitlines()), 1)
                self.assertEqual(output.splitlines()[2], record["url"])



    def test_unhandled_unicode_c1_and_format_controls_are_rejected(self):
        for dangerous in ("\u0081", "\u0085", "\u2028", "\u2029", "\u2066"):
            with self.subTest(char=hex(ord(dangerous))):
                url = "https://example.invalid/live" + dangerous + "fake"
                self.assertFalse(valid_stream_url(url))
                with self.assertRaises(ValueError):
                    render([{"url": url, "name": "bad"}])
                playlist = render([{
                    "url": "https://example.invalid/safe",
                    "name": "News" + dangerous + "#EXTINF:-1,FAKE",
                    "group": "TR" + dangerous + ' group-title="INJECTED"',
                }]).decode("utf-8")
                self.assertEqual(len(playlist.splitlines()), 3)
                self.assertEqual(sum(line.startswith("#EXTINF:") for line in playlist.splitlines()), 1)
                self.assertNotIn(dangerous, playlist)

    def test_non_object_encrypted_inventory_rows_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = {"url": "https://example.invalid/good.m3u8", "name": "GOOD",
                    "group": "TR", "http_hls_status": "AV_VERIFIED", "decoded_av_verified": True, "decode_status": "DECODED_AV"}
            jsonl = "\n".join(json.dumps(row) for row in (
                None, [], "string", 123, good)) + "\n"
            archive = root / "inventory.enc"
            archive.write_bytes(encrypt(jsonl.encode(), SECRET))
            result = export(archive, SECRET, root / "out", sizes=(1000,))
            self.assertEqual(result["av_verified_unique"], 1)
            playlist = Path(result["packages"][0]["path"]).read_text()
            self.assertIn("https://example.invalid/good.m3u8", playlist)
            self.assertEqual(playlist.count("#EXTINF:"), 1)

if __name__ == '__main__':
    unittest.main()
