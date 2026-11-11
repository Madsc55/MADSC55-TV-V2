import unittest
from stage3_recovery_queue import build_recovery_queue


class RecoveryQueueTests(unittest.TestCase):
    def test_transient_is_queued_and_history_not_mutated(self):
        records = [{"url": "https://example.org/a", "last_http_status": 503,
                    "observations": [{"status": "AV_VERIFIED"}]}]
        original = repr(records)
        queue = build_recovery_queue(records)
        self.assertEqual(queue[0]["action"], "RETRY")
        self.assertTrue(queue[0]["preserve_history"])
        self.assertEqual(repr(records), original)

    def test_attempt_limit_and_permanent_failure(self):
        records = [
            {"url": "https://example.org/a", "last_http_status": 503, "recovery_attempts": 3},
            {"url": "https://example.org/b", "last_http_status": 404},
        ]
        queue = build_recovery_queue(records)
        self.assertEqual(len(queue), 2)
        self.assertTrue(all(item['action'] == 'REVIEW' for item in queue))
        self.assertTrue(all(item['next_attempt'] is None for item in queue))

    def test_http_200_requires_av_check(self):
        queue = build_recovery_queue([{"url": "https://example.org/a", "last_http_status": 200}])
        self.assertEqual(queue[0]["action"], "CHECK_AV")

    def test_duplicate_url_rejected(self):
        with self.assertRaises(ValueError):
            build_recovery_queue([{"url": "https://example.org/a"}, {"url": "https://example.org/a"}])

    def test_invalid_history_rejected(self):
        with self.assertRaises(ValueError):
            build_recovery_queue([{"url": "https://example.org/a", "observations": "lost"}])


if __name__ == "__main__":
    unittest.main()
