import hashlib
import unittest
from v2.backup_evidence_adapter import join_evidence

def key(i):
    return hashlib.sha256(str(i).encode()).hexdigest()

class AdapterTests(unittest.TestCase):
    def test_verified_av_and_reviewed_language(self):
        k=key(1)
        p={k:{"playback":"VIDEO_DECODED","audio":"AUDIO_DECODED","decoded_av_verified":True}}
        l={k:{"language":"TR","language_evidence_verified":True,"review_approved":True}}
        self.assertEqual(join_evidence([{"url_sha256":k}],p,l,1)["counts"]["TURK_WORKING"],1)

    def test_unreviewed_model_hint_remains_uncertain(self):
        k=key(1)
        l={k:{"language":"TR","language_evidence_verified":True}}
        self.assertEqual(join_evidence([{"url_sha256":k}],{},l,1)["counts"]["UNCERTAIN"],1)

    def test_timeout_not_permanent_failure(self):
        k=key(1)
        p={k:{"retries_exhausted":True,"status":"TIMEOUT"}}
        self.assertTrue(join_evidence([{"url_sha256":k}],p,{},1)["channels"][0]["retry"])

    def test_unknown_reference_rejected(self):
        with self.assertRaises(ValueError):
            join_evidence([{"url_sha256":key(1)}],{key(2):{}},{},1)

    def test_duplicate_inventory_rejected(self):
        with self.assertRaises(ValueError):
            join_evidence([{"url_sha256":key(1)},{"url_sha256":key(1)}],{},{},2)

if __name__ == "__main__":
    unittest.main()
