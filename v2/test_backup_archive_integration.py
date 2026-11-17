import hashlib
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from v2.backup_archive_offline import run
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
    def test_asr_hint_connected_but_never_auto_approves(self):
        k=key(3)
        with TemporaryDirectory() as d:
            p=Path(d)
            (p/"inventory.json").write_text(json.dumps({"channels":[{"url_sha256":k}]}))
            (p/"playback.json").write_text(json.dumps({"by_url_sha256":{k:{
                "status":"AV_VERIFIED","audio":True,"decoded_av_verified":True,
                "decode_status":"DECODED_AV"}}}))
            (p/"language.json").write_text(json.dumps({"by_url_sha256":{}}))
            (p/"speech.json").write_text(json.dumps({
                "policy":"READ_ONLY_SAMPLED_ASR_HINTS_REQUIRE_REVIEW",
                "results":[{"url_sha256":k,"status":"LANGUAGE_MODEL_HINT_ONLY",
                            "detected_language":"tr","speech_detected":True,
                            "language_probability":0.99}]}))
            result=run(p/"inventory.json",p/"playback.json",p/"language.json",
                       p/"out.json",1,p/"speech.json")
            self.assertEqual(result["counts"],{"UNCERTAIN":1})
            self.assertNotIn("https://",(p/"out.json").read_text())

if __name__=="__main__":
    unittest.main()
