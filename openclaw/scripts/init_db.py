import os
from pathlib import Path

from app.services.db import get_conn

DDL_PATH = os.getenv("OPENCLAW_DDL_PATH", "scripts/init_db.sql")


def main() -> None:
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", "database/app.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with open(DDL_PATH, "r", encoding="utf-8") as file:
        ddl = file.read()

    with get_conn() as conn:
        conn.executescript(ddl)

    print(f"DB initialized at {db_path}")


if __name__ == "__main__":
    main()
