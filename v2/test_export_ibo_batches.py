import json
import tempfile
import unittest
from pathlib import Path
from secure_archive import encrypt
from export_ibo_batches import export

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

if __name__ == '__main__':
    unittest.main()
