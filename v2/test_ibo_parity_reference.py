"""Offline guard against drifting from the canonical IBO playlist reference."""
import unittest
from ibo_parity import IBO

class CanonicalIBOReferenceTests(unittest.TestCase):
    def test_parity_uses_confirmed_main_playlist(self):
        self.assertEqual(IBO, "https://raw.githubusercontent.com/Madsc55/MADSC55-TV-V2/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")

if __name__ == "__main__":
    unittest.main()
