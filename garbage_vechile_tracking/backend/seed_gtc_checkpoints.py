"""Seed GTC checkpoint entries with back-dated data."""
import random
import sys
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.database.database import SessionLocal, engine
from app.models import models

models.Base.metadata.create_all(bind=engine)

DAYS_BACK = 10
MAX_ENTRIES_PER_TRUCK_PER_DAY = 2

WASTE_TYPES = ["dry", "wet", "metal", "plastic", "sanitary"]
REMARKS = [
    None,
    "Arrived on schedule",
    "Load covered properly",
    "Minor spillage observed",
    "Needs wash before next trip",
    "Segregation verified",
]


def _pick_waste_flags() -> dict:
    selected = random.sample(WASTE_TYPES, k=random.randint(1, 3))
    return {
        "is_dry": "dry" in selected,
        "is_wet": "wet" in selected,
        "is_metal": "metal" in selected,
        "is_plastic": "plastic" in selected,
        "is_sanitary": "sanitary" in selected,
    }


def seed_gtc_checkpoints(days_back: int = DAYS_BACK) -> bool:
    db = SessionLocal()
    try:
        db.execute(delete(models.GtcCheckpointEntry))
        db.commit()

        trucks = db.query(models.Truck).all()
        if not trucks:
            print("No trucks found. Seed trucks before seeding checkpoints.")
            return False

        entry_count = 0
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for offset in range(days_back):
            day = today - timedelta(days=offset)
            for truck in trucks:
                entries_today = random.randint(0, MAX_ENTRIES_PER_TRUCK_PER_DAY)
                for _ in range(entries_today):
                    hour = random.randint(6, 19)
                    minute = random.choice([0, 10, 20, 30, 40, 50])
                    arrived_at = day.replace(hour=hour, minute=minute)
                    waste_flags = _pick_waste_flags()

                    entry = models.GtcCheckpointEntry(
                        truck_id=truck.id,
                        arrived_at=arrived_at,
                        truck_cleanliness_score=random.randint(4, 10),
                        gtc_cleanliness_score=random.randint(4, 10),
                        remarks=random.choice(REMARKS),
                        **waste_flags,
                    )
                    db.add(entry)
                    entry_count += 1

        db.commit()
        print(f"Seeded {entry_count} GTC checkpoint entries.")
        return True
    except Exception as exc:
        db.rollback()
        print(f"Failed to seed GTC checkpoint entries: {exc}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = seed_gtc_checkpoints()
    sys.exit(0 if success else 1)
