#!/usr/bin/env python3
"""Synthetic offline regression only; not production channel acceptance."""
import hashlib
import unittest
from ibo_package_acceptance import parse,validate,package

def fixture(n):
    rows=[(f'#EXTINF:-1 tvg-id="id{i}",Channel {i}',f'https://example.org/{i}.m3u8') for i in range(n)]
    text="#EXTM3U\n"+"".join(a+"\n"+b+"\n" for a,b in rows)
    proofs={hashlib.sha256((a+"\n"+b).encode()).hexdigest():{"status":"AV_VERIFIED","video":"h264","audio":"aac"} for a,b in rows}
    return text,proofs

class PackageTests(unittest.TestCase):
    def test_both_targets(self):
        text,proof=fixture(2000)
        for target in (1000,2000):
            out,report=package(text,target,proof)
            self.assertEqual(len(parse(out)),target)
            self.assertEqual(report["records"],target)
    def test_shortage(self):
        text,proof=fixture(2)
        with self.assertRaises(ValueError):
            package(text,1000,proof)
    def test_missing_av(self):
        text,proof=fixture(1000)
        proof.pop(next(iter(proof)))
        with self.assertRaises(ValueError):
            package(text,1000,proof)
    def test_malformed(self):
        for text in ("#EXTM3U\n#EXTINF:-1,Name\n", "#EXTM3U\nhttps://x.org/a", "#EXTM3U\n#EXTINF:-1,Name\nfile:///tmp/x"):
            with self.assertRaises(ValueError):
                parse(text)
    def test_duplicate(self):
        text,_=fixture(1)
        with self.assertRaises(ValueError):
            validate(parse(text+text.splitlines()[1]+"\n"+text.splitlines()[2]+"\n"))
if __name__=="__main__":
    unittest.main()
