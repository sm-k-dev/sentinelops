from sentinelops.db.session import SessionLocal
from sentinelops.services.rules_runner import run_all_rules


def main() -> int:
    db = SessionLocal()
    try:
        run_all_rules(db)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
