from __future__ import annotations

from pathlib import Path

COVER_SIZE = "M"
COVER_ROOT = Path("static/covers")
OPENLIBRARY_COVER_DIR = COVER_ROOT / "openlibrary"


def openlibrary_remote_cover_url(cover_id: int) -> str:
    return f"https://covers.openlibrary.org/b/id/{cover_id}-{COVER_SIZE}.jpg"


def openlibrary_cached_cover_path(cover_id: int) -> Path:
    return OPENLIBRARY_COVER_DIR / f"{cover_id}-{COVER_SIZE}.jpg"


def openlibrary_cached_cover_url(cover_id: int) -> str:
    return f"/covers/openlibrary/{cover_id}-{COVER_SIZE}.jpg"


def openlibrary_cover_urls(cover_id: int | None) -> tuple[str | None, str | None]:
    if cover_id is None:
        return None, None
    remote_url = openlibrary_remote_cover_url(cover_id)
    if openlibrary_cached_cover_path(cover_id).exists():
        return openlibrary_cached_cover_url(cover_id), remote_url
    return remote_url, remote_url
