from __future__ import annotations

from sentinelops.db.init_db import create_all


def main() -> int:
    create_all()
    print("✅ DB tables created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
