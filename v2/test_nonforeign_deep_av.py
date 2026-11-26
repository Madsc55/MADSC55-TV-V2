import unittest
from nonforeign_fresh_full import red_eligible, RETRY_GAP
class DecisionTests(unittest.TestCase):
    def test_lock(self):
        rounds=[{"started":i*(RETRY_GAP+1),"finished":i*(RETRY_GAP+1)+1,"evidence":[{"status":"ORIGINAL_HTTP_404","video":False,"audio":False}]} for i in range(3)]
        self.assertTrue(red_eligible(rounds,False))
        self.assertFalse(red_eligible(rounds,True))
        self.assertFalse(red_eligible(rounds[:2],False))
        rounds[1]["evidence"][0]["status"]="HTTP_403"
        self.assertFalse(red_eligible(rounds,False))
        rounds[1]["evidence"][0]["status"]="ORIGINAL_HTTP_404"
        rounds[1]["started"]=1
        self.assertFalse(red_eligible(rounds,False))

    def test_three_rounds_even_when_first_succeeds(self):
        from unittest.mock import patch
        from nonforeign_fresh_full import review
        row={"url":"https://example.org/a","url_sha256":"test"}
        def sample(startup):
            return [{"status":"MEDIA_60S","video":True,"audio":True,"full_sample":True,
                     "quality_flags":[],"startup_seconds":startup}]
        with patch("nonforeign_fresh_full.inspect",side_effect=[sample(2),sample(25),sample(3)]) as inspect, patch("nonforeign_fresh_full.time.sleep") as sleep:
            got=review(row,"ffmpeg",set())
        self.assertEqual(inspect.call_count,3)
        self.assertEqual(sleep.call_count,2)
        self.assertTrue(all(c.kwargs["timeout"]==180 and c.kwargs["seconds"]==60 for c in inspect.call_args_list))
        self.assertEqual(got["classification"],"AV_60S_LATE_START_VERIFIED")
        self.assertEqual(got["startup_seconds"],[2,25,3])
        self.assertEqual(got["consistency_score"],1.0)
        with patch("nonforeign_fresh_full.inspect",side_effect=[sample(2),sample(3),sample(4)]), patch("nonforeign_fresh_full.time.sleep"):
            self.assertEqual(review(row,"ffmpeg",set())["classification"],"AV_60S_VERIFIED")

    def test_inconsistent_or_missing_startup_is_not_green(self):
        from unittest.mock import patch
        from nonforeign_fresh_full import review
        good=[{"status":"MEDIA_60S","video":True,"audio":True,"full_sample":True,
               "quality_flags":[],"startup_seconds":20}]
        no_start=[{**good[0],"startup_seconds":None}]
        bad=[{"status":"FETCH_FAILED","video":False,"audio":False}]
        with patch("nonforeign_fresh_full.inspect",side_effect=[good,no_start,bad]),patch("nonforeign_fresh_full.time.sleep"):
            got=review({"url":"https://example.org/a","url_sha256":"test"},"ffmpeg",set())
        self.assertEqual(got["classification"],"AV_60S_INCONSISTENT_REVIEW")
        self.assertEqual(got["healthy_rounds"],1)
        self.assertEqual(got["consistency_score"],0.3333)

    def test_startup_observation_extends_capture_after_decoded_av(self):
        from unittest.mock import patch
        from yedekler_quality_review import StartupObservation
        clock=[0.]
        with patch("yedekler_quality_review.time.monotonic",side_effect=lambda:clock[0]),patch("yedekler_quality_review.local_frame",side_effect=lambda data,fmt,kind,exe:kind=="v" or clock[0]>=30):
            obs=StartupObservation("ffmpeg")
            clock[0]=20
            obs.observe(b"video","mpegts")
            self.assertIsNone(obs.ready_at)
            self.assertEqual(obs.deadline(),180)
            clock[0]=30
            obs.observe(b"video+audio","mpegts")
            self.assertEqual(obs.metrics()["first_video_seconds"],20)
            self.assertEqual(obs.metrics()["startup_seconds"],30)
            self.assertEqual(obs.deadline(),92)
            clock[0]=91
            self.assertEqual(obs.remaining(),1)

    def test_deadline_does_not_claim_late_decode(self):
        from unittest.mock import patch
        from yedekler_quality_review import StartupObservation
        clock=[0.]
        def decode(*args):
            clock[0]=181
            return True
        with patch("yedekler_quality_review.time.monotonic",side_effect=lambda:clock[0]),patch("yedekler_quality_review.local_frame",side_effect=decode):
            obs=StartupObservation("ffmpeg")
            clock[0]=179
            obs.observe(b"data","mpegts")
            self.assertIsNone(obs.metrics()["startup_seconds"])
