from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx

from booksequencer.library import SERIES_DIR_NAME, _load_series_files

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"


def main() -> None:
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    series = _load_series_files(DATA_DIR / SERIES_DIR_NAME)
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Prefer": "resolution=merge-duplicates",
    }
    with httpx.Client(timeout=30, headers=headers) as client:
        _upsert_series(client, supabase_url, series)
        _upsert_books(client, supabase_url, series)
    print(f"Imported {len(series)} series.")


def _upsert_series(client: httpx.Client, supabase_url: str, series: list[dict[str, Any]]) -> None:
    rows = [
        {
            "id": item["id"],
            "title": item["title"],
            "author": item.get("author"),
            "sort_order": item.get("order"),
            "source": item.get("source"),
        }
        for item in series
    ]
    _post(client, f"{supabase_url}/rest/v1/series?on_conflict=id", rows)


def _upsert_books(client: httpx.Client, supabase_url: str, series: list[dict[str, Any]]) -> None:
    rows = []
    for item in series:
        for book in item["books"]:
            rows.append(
                {
                    "series_id": item["id"],
                    "book_id": book["id"],
                    "title": book["title"],
                    "position": book["position"],
                    "author": book.get("author"),
                }
            )
    _post(client, f"{supabase_url}/rest/v1/books?on_conflict=series_id,book_id", rows)
    print(f"Imported {len(rows)} books.")


def _post(client: httpx.Client, url: str, rows: list[dict[str, Any]]) -> None:
    response = client.post(url, json=rows)
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase import failed: {response.status_code} {response.text}")


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
