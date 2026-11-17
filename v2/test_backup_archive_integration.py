import hashlib
import unittest
from v2.backup_playback_import import convert
from v2.backup_evidence_adapter import join_evidence

def key(i):
    return hashlib.sha256(str(i).encode()).hexdigest()

class IntegrationTests(unittest.TestCase):
    def test_verified_playback_and_reviewed_turkish_classifies(self):
        k=key(1)
        inventory=[{"url_sha256":k}]
        imported=convert({"channels":inventory},{"coverage_complete":True,"channel_results":[{
            "url_sha256":k,"status":"AV_VERIFIED","audio":True,
            "decoded_av_verified":True,"decode_status":"DECODED_AV"}]})
        language={k:{"language":"TR","language_evidence_verified":True,"review_approved":True}}
        result=join_evidence(inventory,imported["by_url_sha256"],language,1)
        self.assertEqual(result["counts"],{"TURK_WORKING":1})
    def test_unreviewed_turkish_hint_remains_uncertain(self):
        k=key(2)
        inventory=[{"url_sha256":k}]
        imported=convert({"channels":inventory},{"coverage_complete":True,"channel_results":[{
            "url_sha256":k,"status":"AV_VERIFIED","audio":True,
            "decoded_av_verified":True,"decode_status":"DECODED_AV"}]})
        language={k:{"language":"TR","language_evidence_verified":False,"review_approved":False}}
        result=join_evidence(inventory,imported["by_url_sha256"],language,1)
        self.assertEqual(result["counts"],{"UNCERTAIN":1})
if __name__=="__main__":
    unittest.main()
