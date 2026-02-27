import os
from pathlib import Path

from app.services.db import get_conn

DDL_PATH = os.getenv("OPENCLAW_DDL_PATH", "scripts/init_db.sql")
MIGRATIONS_DIR = Path("scripts/migrations")


def main() -> None:
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", "database/app.db"))
    db_exists = db_path.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with open(DDL_PATH, "r", encoding="utf-8") as file:
        ddl = file.read()

    with get_conn() as conn:
        conn.executescript(ddl)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {row[0] for row in conn.execute("SELECT name FROM schema_migrations").fetchall()}
        if MIGRATIONS_DIR.exists():
            migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
            if not db_exists:
                for migration in migrations:
                    if migration.name in applied:
                        continue
                    conn.execute(
                        "INSERT INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                        (migration.name,),
                    )
            else:
                for migration in migrations:
                    if migration.name in applied:
                        continue
                    conn.executescript(migration.read_text(encoding="utf-8"))
                    conn.execute(
                        "INSERT INTO schema_migrations (name, applied_at) VALUES (?, datetime('now'))",
                        (migration.name,),
                    )

    print(f"DB initialized at {db_path}")


if __name__ == "__main__":
    main()
