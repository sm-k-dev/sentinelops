from datetime import datetime, timezone
from sqlalchemy.orm import Session

from sentinelops.db.session import get_db
from sentinelops.models.event import Event

def main():
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        e = Event(
            source="stripe",
            provider_event_id=f"seed_{int(datetime.now().timestamp())}",
            event_type="seed.test_event",
            status="verified",
            signature=None,
            livemode=False,
            created_at_provider=datetime.now(timezone.utc),
            raw={"seed": True, "note": "manual insert for daily summary test"},
        )
        db.add(e)
        db.commit()
        print(" seeded 1 event:", e.provider_event_id)
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

if __name__ == "__main__":
    main()
