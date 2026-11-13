import json
import tempfile
import unittest
from pathlib import Path
from secure_archive import encrypt
from export_ibo_batches import export, render, _safe_http_url

SECRET = 'test-only-archive-password-12345'

class BatchTests(unittest.TestCase):
    def test_exact_verified_counts_and_existing_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for i in range(2005):
                rows.append({'url': f'https://example.invalid/stream/{i}', 'name': f'Channel {i}',
                             'group': 'TR', 'http_hls_status': 'AV_VERIFIED'})
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
                   'group': 'TR', 'http_hls_status': 'AV_VERIFIED'}
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
                     'group': 'TR', 'http_hls_status': 'AV_VERIFIED'}
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

    def test_m3u_metadata_cannot_inject_new_channels(self):
        records = [
            {'url': 'https://example.invalid/live/one.m3u8',
             'name': 'One\n#EXTINF:-1,FAKE',
             'group': 'Haber\r#EXTINF:-1,INJECTED',
             'logo': 'https://example.invalid/logo.png"\n#EXTINF:-1,FAKE'},
            {'url': 'https://example.invalid/live/two.m3u8',
             'name': 'Two\u2028#EXTINF:-1,FAKE',
             'group': 'Sport\u0085#EXTINF:-1,FAKE',
             'logo': 'https://example.invalid/logo.png'}
        ]
        playlist = render(records).decode('utf-8')
        self.assertEqual(len(playlist.splitlines()), 5)
        self.assertEqual(playlist.count('#EXTINF:-1'), 2)
        self.assertEqual(playlist.count('tvg-logo='), 1)
        self.assertIn('group-title="Haber #EXTINF:-1', playlist)
        self.assertTrue(playlist.endswith('https://example.invalid/live/two.m3u8\n'))

    def test_malformed_encrypted_inventory_urls_are_never_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            urls = ['https://example.invalid/a\n#EXTINF:-1,FAKE',
                    'https://example.invalid:99999/a',
                    'https://name:secret@example.invalid/a',
                    'https://example.invalid/white space',
                    'ftp://example.invalid/a',
                    'https://example.invalid/good.m3u8']
            rows = [{'url': url, 'name': 'Channel', 'group': 'TR',
                     'http_hls_status': 'AV_VERIFIED'} for url in urls]
            rows.append(None)
            encrypted = root / 'inventory.enc'
            encrypted.write_bytes(encrypt(('\n'.join(json.dumps(x) for x in rows) + '\n').encode(), SECRET))
            result = export(encrypted, SECRET, root / 'packages', sizes=(1000,))
            self.assertEqual(result['av_verified_unique'], 1)
            self.assertEqual(result['packages'][0]['count'], 1)
            playlist = Path(result['packages'][0]['path']).read_text()
            self.assertEqual(playlist.count('#EXTINF:'), 1)
            self.assertIn('https://example.invalid/good.m3u8', playlist)
            self.assertNotIn('FAKE', playlist)
            for bad in urls[:-1]:
                self.assertFalse(_safe_http_url(bad))

    def test_symlink_output_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {'url': 'https://example.invalid/stream/1', 'name': 'One',
                   'group': 'TR', 'http_hls_status': 'AV_VERIFIED'}
            archive = root / 'inventory.enc'
            archive.write_bytes(encrypt((json.dumps(row)+'\n').encode(), SECRET))
            protected = root / 'protected'
            protected.mkdir()
            link = root / 'out-link'
            link.symlink_to(protected, target_is_directory=True)
            with self.assertRaises(ValueError):
                export(archive, SECRET, link, sizes=(1000,))
            self.assertEqual(list(protected.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
