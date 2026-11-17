"""Use real local FFmpeg and Tesseract on a generated Turkish-language frame.

A synthetic OCR fixture is NOT evidence for a real broadcaster or a playlist.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest
from v2.backup_text_evidence import inspect_text_observations

class LocalTurkishOCRTests(unittest.TestCase):
    def test_real_tesseract_turkish_ocr_frame(self):
        self.assertIsNotNone(shutil.which("ffmpeg"), "FFmpeg is required")
        self.assertIsNotNone(shutil.which("tesseract"), "Tesseract is required")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "turkish-frame.png"
            command = [
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=white:s=1600x240:r=1",
                "-vf", ("drawtext=font='DejaVu Sans':"
                        "text='TÜRKİYE HABERLERİ CANLI':fontsize=72:"
                        "fontcolor=black:x=35:y=60"),
                "-frames:v", "1", "-y", str(path),
            ]
            subprocess.run(command, check=True, capture_output=True, timeout=20)
            self.assertGreater(path.stat().st_size, 500)
            ocr = subprocess.run(
                ["tesseract", str(path), "stdout", "-l", "tur+eng"],
                check=True, capture_output=True, text=True, timeout=20
            ).stdout
            self.assertIn("TÜRKİYE", ocr.upper())
            hints = inspect_text_observations([{"kind":"OCR", "text":ocr[:4096]}])
            self.assertTrue(hints["observations"][0]["turkish_review_hint"])
            self.assertFalse(hints["language_evidence_verified"])
            self.assertFalse(hints["review_approved"])
            self.assertNotIn("TÜRKİYE", str(hints))

if __name__ == "__main__":
    unittest.main()
