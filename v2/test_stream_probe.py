import json
import subprocess
import unittest
from unittest.mock import patch
from stream_probe import probe, verify_decoded_av

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
    @patch('stream_probe.subprocess.run')
    def test_measured_resolution_and_audio(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({'streams': [
            {'codec_type': 'video', 'codec_name': 'h264', 'width': 1920, 'height': 1080},
            {'codec_type': 'audio', 'codec_name': 'aac'}]}), '')
        result = probe('https://example.org/live.m3u8')
        self.assertEqual(result['status'], 'AV_VERIFIED')
        self.assertEqual((result['width'], result['height']), (1920, 1080))
        self.assertTrue(result['resolution_verified'])
        self.assertEqual(result['evidence_level'], 'ffprobe_stream_metadata')
        self.assertFalse(result['decoded_av_verified'])

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run')
    def test_missing_or_invalid_dimensions_are_not_verified(self, run, which):
        for width, height in ((None, None), (0, 1080), ('1920', 1080), (99999, 1080)):
            with self.subTest(width=width, height=height):
                run.return_value = subprocess.CompletedProcess([], 0, json.dumps({'streams': [
                    {'codec_type': 'video', 'codec_name': 'h264', 'width': width, 'height': height},
                    {'codec_type': 'audio', 'codec_name': 'aac'}]}), '')
                result = probe('https://example.org/live.m3u8')
                self.assertEqual(result['status'], 'AV_VERIFIED')
                self.assertIsNone(result['width'])
                self.assertIsNone(result['height'])
                self.assertFalse(result['resolution_verified'])

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('stream_probe.subprocess.run')
    def test_decode_requires_successful_ffmpeg_exit(self, run, which):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        self.assertTrue(verify_decoded_av('https://example.org/live.m3u8')['decoded_av_verified'])
        run.return_value = subprocess.CompletedProcess([], 1, '', 'failed')
        self.assertFalse(verify_decoded_av('https://example.org/live.m3u8')['decoded_av_verified'])

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffmpeg')
    @patch('stream_probe.subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 5))
    def test_decode_timeout_fails_closed(self, run, which):
        self.assertFalse(verify_decoded_av('https://example.org/live.m3u8')['decoded_av_verified'])

    @patch('stream_probe.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('stream_probe.subprocess.run', side_effect=subprocess.TimeoutExpired('ffprobe', 5))
    def test_timeout(self, run, which):
        self.assertEqual(probe('https://example.org/live.m3u8')['status'], 'TIMEOUT')

if __name__ == '__main__':
    unittest.main()
