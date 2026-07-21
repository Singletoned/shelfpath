from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from booksequencer.catalogue import sanitize_book_author
from booksequencer.library import SERIES_DIR_NAME, _load_series_files

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required.")
    series = _load_series_files(DATA_DIR / SERIES_DIR_NAME)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for item in series:
                cursor.execute(
                    """
                    insert into series (id, title, author, sort_order, source)
                    values (%s, %s, %s, %s, %s)
                    on conflict (id) do update set title = excluded.title, author = excluded.author,
                    sort_order = excluded.sort_order, source = excluded.source
                    """,
                    (
                        item["id"],
                        item["title"],
                        item.get("author"),
                        item.get("order"),
                        Jsonb(item.get("source")),
                    ),
                )
                for book in item["books"]:
                    cursor.execute(
                        """
                        insert into books
                          (series_id, book_id, title, position, author, openlibrary_cover_id)
                        values (%s, %s, %s, %s, %s, %s)
                        on conflict (series_id, book_id) do update set title = excluded.title,
                        position = excluded.position, author = excluded.author,
                        openlibrary_cover_id = excluded.openlibrary_cover_id
                        """,
                        (
                            item["id"],
                            book["id"],
                            book["title"],
                            book["position"],
                            sanitize_book_author(book.get("author")),
                            book.get("openlibrary_cover_id"),
                        ),
                    )
    print(f"Imported {len(series)} series and {sum(len(item['books']) for item in series)} books.")


if __name__ == "__main__":
    main()
