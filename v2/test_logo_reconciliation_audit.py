import unittest
from logo_reconciliation_audit import audit


def playlist(*entries):
    return "#EXTM3U\n" + "".join(
        '#EXTINF:-1 tvg-id="%s"%s group-title="YEDEKLER",%s\n%s\n'
        % (identity, (' tvg-logo="%s"' % logo) if logo else "", name, url)
        for identity, logo, name, url in entries
    )


class LogoAuditTests(unittest.TestCase):
    def test_matching_identity_produces_review_only_candidate(self):
        url = "https://example.org/live.m3u8"
        old = playlist(("a", "https://example.org/logo.png", "A", url))
        current = playlist(("a", "", "A", url))
        result = audit(current, old)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["status"], "REVIEW_REQUIRED_NOT_VERIFIED")

    def test_changed_identity_is_rejected(self):
        url = "https://example.org/live.m3u8"
        result = audit(playlist(("b", "", "B", url)),
                       playlist(("a", "https://example.org/a.png", "A", url)))
        self.assertEqual(result["candidate_count"], 0)

    def test_duplicate_stream_url_is_ambiguous(self):
        url = "https://example.org/live.m3u8"
        old = playlist(("a", "https://example.org/a.png", "A", url))
        current = playlist(("a", "", "A", url), ("b", "", "B", url))
        self.assertEqual(audit(current, old)["candidate_count"], 0)

    def test_existing_logo_is_preserved(self):
        url = "https://example.org/live.m3u8"
        old = playlist(("a", "https://example.org/old.png", "A", url))
        current = playlist(("a", "https://example.org/new.png", "A", url))
        self.assertEqual(audit(current, old)["candidate_count"], 0)

    def test_non_https_historical_logo_is_rejected(self):
        url = "https://example.org/live.m3u8"
        old = playlist(("a", "http://example.org/a.png", "A", url))
        self.assertEqual(audit(playlist(("a", "", "A", url)), old)["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
