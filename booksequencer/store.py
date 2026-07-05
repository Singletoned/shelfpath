from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import httpx

from booksequencer.library import load_library, save_book_state, save_book_states


class Store(Protocol):
    async def load_library(self, user: dict[str, Any] | None) -> dict[str, Any]: ...

    async def save_book_state(
        self, user: dict[str, Any] | None, book_key: str, owned: bool, read: bool
    ) -> None: ...

    async def save_book_states(
        self, user: dict[str, Any] | None, book_states: dict[str, dict[str, bool]]
    ) -> None: ...


class FileStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    async def load_library(self, user: dict[str, Any] | None) -> dict[str, Any]:
        return load_library(self.data_dir)

    async def save_book_state(
        self, user: dict[str, Any] | None, book_key: str, owned: bool, read: bool
    ) -> None:
        save_book_state(self.data_dir, book_key, owned, read)

    async def save_book_states(
        self, user: dict[str, Any] | None, book_states: dict[str, dict[str, bool]]
    ) -> None:
        save_book_states(self.data_dir, book_states)


class SupabaseStore:
    def __init__(self, supabase_url: str, publishable_key: str) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key

    async def load_library(self, user: dict[str, Any] | None) -> dict[str, Any]:
        current_user = _require_user(user)
        list_id = await self._ensure_personal_list(current_user)
        series_rows = await self._request(
            current_user, "GET", "/rest/v1/series?select=*&order=title.asc"
        )
        book_rows = await self._request(
            current_user,
            "GET",
            "/rest/v1/books?select=*&order=series_id.asc,position.asc",
        )
        state_rows = await self._request(
            current_user,
            "GET",
            f"/rest/v1/book_states?select=book_id,owned,read&list_id=eq.{list_id}",
        )
        return _merge_rows(series_rows, book_rows, state_rows)

    async def save_book_state(
        self, user: dict[str, Any] | None, book_key: str, owned: bool, read: bool
    ) -> None:
        await self.save_book_states(user, {book_key: {"owned": owned, "read": read}})

    async def save_book_states(
        self, user: dict[str, Any] | None, book_states: dict[str, dict[str, bool]]
    ) -> None:
        current_user = _require_user(user)
        list_id = await self._ensure_personal_list(current_user)
        keys = sorted(book_states)
        if not keys:
            return
        key_filter = ",".join(keys)
        books = await self._request(
            current_user,
            "GET",
            f"/rest/v1/books?select=id,key&key=in.({key_filter})",
        )
        ids_by_key = {book["key"]: book["id"] for book in books}
        unknown_keys = set(keys) - set(ids_by_key)
        if unknown_keys:
            raise ValueError(f"Unknown book keys: {', '.join(sorted(unknown_keys))}")
        rows = [
            {
                "list_id": list_id,
                "book_id": ids_by_key[book_key],
                "owned": book_state["owned"],
                "read": book_state["read"],
            }
            for book_key, book_state in book_states.items()
        ]
        await self._request(
            current_user,
            "POST",
            "/rest/v1/book_states?on_conflict=list_id,book_id",
            json=rows,
            extra_headers={"Prefer": "resolution=merge-duplicates"},
        )

    async def _ensure_personal_list(self, user: dict[str, Any]) -> str:
        memberships = await self._request(
            user,
            "GET",
            "/rest/v1/list_members?select=list_id,role,lists(name)&order=created_at.asc&limit=1",
        )
        if memberships:
            return memberships[0]["list_id"]

        inserted_lists = await self._request(
            user,
            "POST",
            "/rest/v1/lists",
            json={"name": "My books", "owner_user_id": user["id"]},
            extra_headers={"Prefer": "return=representation"},
        )
        list_id = inserted_lists[0]["id"]
        await self._request(
            user,
            "POST",
            "/rest/v1/list_members",
            json={"list_id": list_id, "user_id": user["id"], "role": "owner"},
        )
        return list_id

    async def _request(
        self,
        user: dict[str, Any],
        method: str,
        path: str,
        json: Any | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        headers = {
            "apikey": self.publishable_key,
            "Authorization": f"Bearer {user['access_token']}",
        }
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.supabase_url}{path}",
                headers=headers,
                json=json,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase request failed: {response.status_code} {response.text}")
        if not response.content:
            return None
        return response.json()


def build_store(
    storage: str, data_dir: Path, supabase_url: str | None, publishable_key: str | None
) -> Store:
    if storage == "file":
        return FileStore(data_dir)
    if storage == "supabase":
        if not supabase_url or not publishable_key:
            raise ValueError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY are required.")
        return SupabaseStore(supabase_url, publishable_key)
    raise ValueError(f"Unknown storage backend: {storage}")


def _require_user(user: dict[str, Any] | None) -> dict[str, Any]:
    if user is None:
        raise ValueError("Supabase storage requires an authenticated user.")
    return user


def _merge_rows(
    series_rows: list[dict[str, Any]],
    book_rows: list[dict[str, Any]],
    state_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    states_by_book_id = {row["book_id"]: row for row in state_rows}
    books_by_series: dict[str, list[dict[str, Any]]] = {row["id"]: [] for row in series_rows}
    books_by_key = {}

    for row in book_rows:
        state = states_by_book_id.get(row["id"], {})
        book = {
            "id": row["book_id"],
            "title": row["title"],
            "position": row["position"],
            "author": row.get("author"),
            "key": row["key"],
            "owned": bool(state.get("owned", False)),
            "read": bool(state.get("read", False)),
        }
        books_by_series.setdefault(row["series_id"], []).append(book)
        books_by_key[row["key"]] = book

    merged_series = []
    for row in series_rows:
        books = books_by_series.get(row["id"], [])
        owned_count = sum(1 for book in books if book["owned"])
        read_count = sum(1 for book in books if book["read"])
        merged_series.append(
            {
                "id": row["id"],
                "title": row["title"],
                "author": row.get("author"),
                "order": row.get("sort_order"),
                "source": row.get("source"),
                "books": books,
                "book_count": len(books),
                "owned_count": owned_count,
                "read_count": read_count,
                "missing_count": len(books) - owned_count,
            }
        )
    return {"series": merged_series, "books_by_key": books_by_key, "warnings": []}
