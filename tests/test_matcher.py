import unittest
from scraper.matcher import listing_matches_profile

class TestMatcher(unittest.TestCase):
    def test_basic_match(self):
        listing = {
            "title": "Python Backend Engineer",
            "description": "Django, REST API",
            "company": "SuperTech"
        }
        profile = {
            "inclusion_keywords": ["python"],
            "exclusion_keywords": ["on-site"],
            "alerts_paused": False
        }
        self.assertTrue(listing_matches_profile(listing, profile))

    def test_exclusion_match(self):
        listing = {
            "title": "Python Backend Engineer (on-site)",
            "description": "Django, REST API",
            "company": "SuperTech"
        }
        profile = {
            "inclusion_keywords": ["python"],
            "exclusion_keywords": ["on-site"],
            "alerts_paused": False
        }
        self.assertFalse(listing_matches_profile(listing, profile))

    def test_paused_alerts(self):
        listing = {
            "title": "Python Backend Engineer",
            "description": "Django, REST API",
            "company": "SuperTech"
        }
        profile = {
            "inclusion_keywords": ["python"],
            "exclusion_keywords": ["on-site"],
            "alerts_paused": True
        }
        self.assertFalse(listing_matches_profile(listing, profile))

if __name__ == "__main__":
    unittest.main()
