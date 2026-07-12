from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import httpx

SEARCH_DELAY_SECONDS = 0.15


def main() -> None:
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30) as client:
        books = _get_books(client, supabase_url, headers)
        updated = 0
        skipped = 0
        for book in books:
            cover_id = _find_cover_id(client, book)
            if cover_id is None:
                skipped += 1
                continue
            _patch_book(client, supabase_url, headers, book["id"], cover_id)
            updated += 1
            time.sleep(SEARCH_DELAY_SECONDS)
    print(f"Updated {updated} Open Library covers; {skipped} books still have no cover.")


def _get_books(
    client: httpx.Client, supabase_url: str, headers: dict[str, str]
) -> list[dict[str, Any]]:
    response = client.get(
        f"{supabase_url}/rest/v1/books?select=id,title,author,openlibrary_cover_id&openlibrary_cover_id=is.null&order=title.asc",
        headers=headers,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase book fetch failed: {response.status_code} {response.text}")
    return response.json()


def _find_cover_id(client: httpx.Client, book: dict[str, Any]) -> int | None:
    title = book["title"]
    params = [
        f"title={quote(title)}",
        "fields=cover_i,title,author_name",
        "limit=5",
    ]
    author = book.get("author")
    if author:
        params.insert(1, f"author={quote(author)}")
    response = client.get(f"https://openlibrary.org/search.json?{'&'.join(params)}")
    if response.status_code >= 400:
        raise RuntimeError(
            f"Open Library search failed for {title!r}: {response.status_code} {response.text}"
        )
    docs = response.json().get("docs", [])
    for doc in docs:
        cover_id = doc.get("cover_i")
        if isinstance(cover_id, int):
            return cover_id
    return None


def _patch_book(
    client: httpx.Client,
    supabase_url: str,
    headers: dict[str, str],
    book_id: str,
    cover_id: int,
) -> None:
    response = client.patch(
        f"{supabase_url}/rest/v1/books?id=eq.{book_id}",
        headers={**headers, "Prefer": "return=minimal"},
        json={"openlibrary_cover_id": cover_id},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase cover update failed: {response.status_code} {response.text}")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
