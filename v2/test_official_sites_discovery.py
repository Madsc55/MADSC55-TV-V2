import unittest
from official_sites_discovery import select_official_sites

class OfficialSiteScopeTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [
            {"id": "tr.news", "name": "TR News", "country": "TR", "website": "https://tr.example"},
            {"id": "az.news", "name": "AZ News", "country": "AZ", "website": "https://az.example"},
            {"id": "us.news", "name": "US News", "country": "US", "website": "https://us.example"},
            {"id": "bad.http", "name": "HTTP Site", "country": "US", "website": "http://bad.example"},
            {"id": "adult", "name": "Adult", "country": "US", "website": "https://adult.example", "is_nsfw": True},
            {"id": "closed", "name": "Closed", "country": "GB", "website": "https://closed.example", "closed": True},
        ]

    def test_default_scope_remains_tr_az(self):
        rows = select_official_sites(self.catalog)
        self.assertEqual({row["country"] for row in rows}, {"TR", "AZ"})
        self.assertEqual(len(rows), 2)

    def test_worldwide_scope_includes_all_public_country_sites(self):
        rows = select_official_sites(self.catalog, worldwide=True)
        self.assertEqual({row["country"] for row in rows}, {"TR", "AZ", "US"})
        self.assertEqual(len(rows), 3)

if __name__ == "__main__":
    unittest.main()
