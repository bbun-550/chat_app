import os

from app.services.db import get_conn

DDL_PATH = os.getenv("OPENCLAW_DDL_PATH", "scripts/init_db.sql")


def main() -> None:
    db_path = os.getenv("OPENCLAW_DB_PATH", "database/app.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with open(DDL_PATH, "r", encoding="utf-8") as file:
        ddl = file.read()

    with get_conn() as conn:
        conn.executescript(ddl)

    print(f"DB initialized at {db_path}")


if __name__ == "__main__":
    main()
