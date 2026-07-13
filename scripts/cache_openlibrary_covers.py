from __future__ import annotations

import os
from pathlib import Path

import httpx

from booksequencer.covers import (
    OPENLIBRARY_COVER_DIR,
    openlibrary_cached_cover_path,
    openlibrary_remote_cover_url,
)


def main() -> None:
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_role_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    OPENLIBRARY_COVER_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        cover_ids = _get_cover_ids(client, supabase_url, headers)
        downloaded = 0
        existing = 0
        failed = 0
        for cover_id in cover_ids:
            target = openlibrary_cached_cover_path(cover_id)
            if target.exists() and target.stat().st_size > 0:
                existing += 1
                continue
            if _download_cover(client, cover_id, target):
                downloaded += 1
            else:
                failed += 1
    print(f"Cached {downloaded} Open Library covers; {existing} already cached; {failed} failed.")


def _get_cover_ids(client: httpx.Client, supabase_url: str, headers: dict[str, str]) -> list[int]:
    response = client.get(
        f"{supabase_url}/rest/v1/books?select=openlibrary_cover_id&openlibrary_cover_id=not.is.null",
        headers=headers,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Supabase cover fetch failed: {response.status_code} {response.text}")
    cover_ids = set()
    for row in response.json():
        cover_id = row.get("openlibrary_cover_id")
        if isinstance(cover_id, int):
            cover_ids.add(cover_id)
    return sorted(cover_ids)


def _download_cover(client: httpx.Client, cover_id: int, target: Path) -> bool:
    response = client.get(openlibrary_remote_cover_url(cover_id))
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400 or not content_type.startswith("image/"):
        return False
    temporary_target = target.with_suffix(f"{target.suffix}.tmp")
    temporary_target.write_bytes(response.content)
    temporary_target.replace(target)
    return True


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required.")
    return value


if __name__ == "__main__":
    main()
