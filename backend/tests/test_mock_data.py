import json
from pathlib import Path
import unittest

from app.database import SessionLocal
from app.models.post import Post
from app.schemas.post import NormalizedPost, RawPostPayload
from app.services.normalizer import DataNormalizer
from scripts.load_mock_data import load_mock_posts

BACKEND_DIR = Path(__file__).resolve().parent.parent
MOCK_DATA_PATH = BACKEND_DIR / "data" / "mock_posts.json"


class TestMockData(unittest.TestCase):
    """
    Automated test suite verifying the integrity, diversity, and repeatability
    of the InsightX mock social media dataset.
    """

    @classmethod
    def setUpClass(cls):
        with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
            cls.raw_records = json.load(f)

        cls.parsed_payloads = [RawPostPayload.model_validate(r) for r in cls.raw_records]
        cls.normalized_posts = [DataNormalizer.normalize(p) for p in cls.parsed_payloads]

    def test_1_file_exists(self):
        self.assertTrue(MOCK_DATA_PATH.exists(), f"File does not exist: {MOCK_DATA_PATH}")
        self.assertTrue(MOCK_DATA_PATH.is_file())

    def test_2_json_loads_successfully(self):
        self.assertIsInstance(self.raw_records, list)
        self.assertGreater(len(self.raw_records), 0)
        for r in self.raw_records:
            self.assertIsInstance(r, dict)

    def test_3_record_count_range(self):
        count = len(self.raw_records)
        self.assertGreaterEqual(count, 40, "Dataset should have at least 40 records")
        self.assertLessEqual(count, 60, "Dataset should have at most 60 records")

    def test_4_parse_with_raw_post_payload(self):
        self.assertEqual(len(self.parsed_payloads), len(self.raw_records))
        for p in self.parsed_payloads:
            self.assertIsInstance(p, RawPostPayload)

    def test_5_normalize_all_records(self):
        self.assertEqual(len(self.normalized_posts), len(self.raw_records))
        for np in self.normalized_posts:
            self.assertIsInstance(np, NormalizedPost)

    def test_6_platform_and_external_id_present(self):
        for np in self.normalized_posts:
            self.assertTrue(bool(np.platform_name and np.platform_name.strip()))
            self.assertTrue(bool(np.external_post_id and np.external_post_id.strip()))

    def test_7_multiple_platforms_represented(self):
        platforms = {np.platform_name for np in self.normalized_posts}
        self.assertGreaterEqual(len(platforms), 4)
        self.assertIn("X", platforms)
        self.assertIn("Telegram", platforms)
        self.assertIn("Reddit", platforms)
        self.assertIn("YouTube", platforms)

    def test_8_multiple_languages_represented(self):
        languages = {np.language for np in self.normalized_posts if np.language}
        self.assertGreaterEqual(len(languages), 3)
        self.assertIn("en", languages)
        self.assertIn("te", languages)
        self.assertIn("hi", languages)

    def test_9_omission_of_optional_fields(self):
        missing_url = [np for np in self.normalized_posts if np.url is None]
        missing_author = [np for np in self.normalized_posts if np.author_username is None]
        missing_metrics = [np for np in self.normalized_posts if np.metrics is None]

        self.assertGreater(len(missing_url), 0, "Some records must omit URL")
        self.assertGreater(len(missing_author), 0, "Some records must omit author")
        self.assertGreater(len(missing_metrics), 0, "Some records must omit metrics")

    def test_10_deliberate_duplicates_exist(self):
        seen = set()
        duplicates = []
        for np in self.normalized_posts:
            key = (np.platform_name, np.external_post_id)
            if key in seen:
                duplicates.append(key)
            else:
                seen.add(key)

        self.assertGreaterEqual(len(duplicates), 2, "Deliberate duplicates must exist in mock dataset")

    def test_11_repeated_loader_creates_no_duplicates(self):
        db = SessionLocal()
        initial_count = db.query(Post).count()
        db.close()

        # Execute loader
        result = load_mock_posts(MOCK_DATA_PATH)
        self.assertEqual(result["created"], 0, "Second run should create 0 new records")
        self.assertEqual(result["duplicates"], len(self.raw_records))
        self.assertEqual(result["failed"], 0)

        db = SessionLocal()
        final_count = db.query(Post).count()
        db.close()

        self.assertEqual(initial_count, final_count, "Database post count must not increase on duplicate run")


if __name__ == "__main__":
    unittest.main()
