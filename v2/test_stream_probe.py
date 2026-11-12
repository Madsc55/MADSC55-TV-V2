import json
import subprocess
import unittest
from unittest.mock import patch
from stream_probe import probe

class StreamProbeTests(unittest.TestCase):
    def test_invalid_url(self):
        self.assertEqual(probe('file:///etc/passwd')['status'], 'INVALID_URL')
        self.assertEqual(probe('https://u:p@example.com/x')['status'], 'INVALID_URL')

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run')
    def test_real_stream_metadata(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac'}]}), '')
        result = probe('https://example.org/live.m3u8')
        self.assertEqual(result['status'], 'AV_VERIFIED')
        self.assertTrue(result['video'] and result['audio'])
        self.assertNotIn('example.org', str(result))

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run')
    def test_video_only_not_verified(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'}]}), '')
        self.assertEqual(probe('https://example.org/live.m3u8')['status'], 'VIDEO_ONLY')

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run', side_effect=subprocess.TimeoutExpired('ffprobe', 5))
    def test_timeout(self, run, which):
        self.assertEqual(probe('https://example.org/live.m3u8')['status'], 'TIMEOUT')

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run')
    def test_malformed_probe_payloads_fail_closed(self, run, which):
        for payload in ('[]', '{}', '{"streams":null}', '{"streams":"video"}',
                        '{"streams":[null]}', '{"streams":[{"codec_type":"video"},false]}'):
            with self.subTest(payload=payload):
                run.return_value = subprocess.CompletedProcess([], 0, payload, '')
                self.assertEqual(probe('https://example.org/live.m3u8')['status'],
                                 'INVALID_PROBE_RESULT')

    def test_invalid_timeout_never_invokes_ffprobe(self):
        for timeout in (float('nan'), float('inf'), -1, 0, 121):
            with self.subTest(timeout=timeout):
                self.assertEqual(probe('https://example.org/live.m3u8', timeout=timeout)['status'],
                                 'INVALID_INPUT')

if __name__ == '__main__':
    unittest.main()
