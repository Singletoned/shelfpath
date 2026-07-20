from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

PROJECT_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_DIR / "db" / "migrations"


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(database_url: str) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                create table if not exists schema_migrations (
                    filename text primary key,
                    applied_at timestamptz not null default now()
                )
                """
            )
            cursor.execute("select filename from schema_migrations")
            already_applied = {row[0] for row in cursor.fetchall()}
            for migration in migration_files():
                if migration.name in already_applied:
                    continue
                cursor.execute(migration.read_text(encoding="utf-8"))
                cursor.execute(
                    "insert into schema_migrations (filename) values (%s)", (migration.name,)
                )
                applied.append(migration.name)
        connection.commit()
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Shelfpath Postgres migrations.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        raise ValueError("DATABASE_URL is required.")
    for filename in apply_migrations(args.database_url):
        print(f"Applied {filename}")


if __name__ == "__main__":
    main()
