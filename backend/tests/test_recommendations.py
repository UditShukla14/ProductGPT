import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal, init_db
from app.schemas.recommendations import HvacRecommendationRequest
from app.services.hvac_search import search_hvac_systems
from app.schemas.hvac import HvacSearchRequest
from app.services.recommender import recommend_hvac_systems
from app.ingestion.goodman_ratings import ingest_goodman_ratings
from app.config import settings


def test_seed_and_recommend(tmp_path=None):
    init_db()
    db = SessionLocal()
    try:
        ingest_goodman_ratings(db, settings.default_goodman_ratings_xlsx, replace=True)

        search_result, meta = search_hvac_systems(
            db,
            HvacSearchRequest(tonnage=2.0, min_seer=15, limit=5),
        )
        assert meta["total"] > 0
        assert all(s.tonnage == 2.0 for s in search_result)
        assert all(s.seer >= 15 for s in search_result if s.seer is not None)

        recs = recommend_hvac_systems(
            db,
            HvacRecommendationRequest(
                tonnage=2.0,
                min_seer=15,
                equipment_category="AC",
                refrigerant_type="R-32",
                limit=5,
            ),
        )
        assert len(recs.recommendations) <= 5
        assert recs.recommendations[0].score > 0
        assert recs.recommendations[0].system.components
    finally:
        db.close()


if __name__ == "__main__":
    test_seed_and_recommend()
    print("tests passed")
