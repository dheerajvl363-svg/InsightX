import json
import logging
from pathlib import Path
import sys

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal, init_db
from app.schemas.post import RawPostPayload
from app.services.ingestion import IngestionService
from app.services.normalizer import DataNormalizer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("load_mock_data")


def load_mock_posts(file_path: Path = None):
    """
    Loads mock social media data from JSON and ingests it through the Phase 2 pipeline.
    """
    if file_path is None:
        file_path = backend_dir / "data" / "mock_posts.json"

    if not file_path.exists():
        raise FileNotFoundError(f"Mock data file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    logger.info(f"Loaded {len(records)} mock records from {file_path}")

    # Ensure database tables and schema are initialized
    init_db()

    db = SessionLocal()
    try:
        service = IngestionService(db)

        # Normalize records
        normalized_posts = []
        validation_failures = 0

        for idx, record in enumerate(records, start=1):
            try:
                raw_payload = RawPostPayload.model_validate(record)
                normalized = DataNormalizer.normalize(raw_payload)
                normalized_posts.append(normalized)
            except Exception as e:
                logger.error(f"Record #{idx} validation/normalization error: {e}")
                validation_failures += 1

        # Batch ingest normalized posts
        batch_response = service.ingest_batch(normalized_posts)

        total_received = len(records)
        created = batch_response.successful
        duplicates = batch_response.duplicates
        failed = batch_response.failed + validation_failures

        print("\n" + "=" * 50)
        print("InsightX — Mock Data Ingestion Summary")
        print("=" * 50)
        print(f"Total records processed : {total_received}")
        print(f"Successfully created    : {created}")
        print(f"Duplicates handled      : {duplicates}")
        print(f"Failures                : {failed}")
        print("=" * 50 + "\n")

        return {
            "total": total_received,
            "created": created,
            "duplicates": duplicates,
            "failed": failed,
        }

    finally:
        db.close()


if __name__ == "__main__":
    load_mock_posts()
