from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import httpx

from booksequencer.library import load_library, save_book_state, save_book_states

DEFAULT_LIST_NAME = "My books"
SUGGESTION_DAILY_LIMIT = 5


class Store(Protocol):
    async def load_library(
        self, user: dict[str, Any] | None, list_id: str | None = None
    ) -> dict[str, Any]: ...

    async def list_lists(self, user: dict[str, Any] | None) -> list[dict[str, Any]]: ...

    async def share_list(
        self,
        user: dict[str, Any] | None,
        list_id: str,
        email: str,
        role: str,
    ) -> None: ...

    async def can_suggest_series(self, user: dict[str, Any] | None) -> bool: ...

    async def suggestion_count_today(self, user: dict[str, Any] | None) -> int: ...

    async def create_series_suggestion(
        self,
        user: dict[str, Any] | None,
        prompt: str,
        status: str,
        proposal: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]: ...

    async def get_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> dict[str, Any]: ...

    async def approve_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None: ...

    async def reject_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None: ...

    async def save_book_state(
        self,
        user: dict[str, Any] | None,
        book_key: str,
        owned: bool,
        read: bool,
        wanted: bool = True,
        list_id: str | None = None,
    ) -> None: ...

    async def save_book_states(
        self,
        user: dict[str, Any] | None,
        book_states: dict[str, dict[str, bool]],
        list_id: str | None = None,
    ) -> None: ...


class FileStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    async def load_library(
        self, user: dict[str, Any] | None, list_id: str | None = None
    ) -> dict[str, Any]:
        library = load_library(self.data_dir)
        library["lists"] = [_file_list()]
        library["current_list"] = _file_list()
        return library

    async def list_lists(self, user: dict[str, Any] | None) -> list[dict[str, Any]]:
        return [_file_list()]

    async def share_list(
        self,
        user: dict[str, Any] | None,
        list_id: str,
        email: str,
        role: str,
    ) -> None:
        raise ValueError("Shared lists require Supabase storage.")

    async def can_suggest_series(self, user: dict[str, Any] | None) -> bool:
        return False

    async def suggestion_count_today(self, user: dict[str, Any] | None) -> int:
        return 0

    async def create_series_suggestion(
        self,
        user: dict[str, Any] | None,
        prompt: str,
        status: str,
        proposal: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        raise ValueError("AI series suggestions require Supabase storage.")

    async def get_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> dict[str, Any]:
        raise ValueError("AI series suggestions require Supabase storage.")

    async def approve_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None:
        raise ValueError("AI series suggestions require Supabase storage.")

    async def reject_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None:
        raise ValueError("AI series suggestions require Supabase storage.")

    async def save_book_state(
        self,
        user: dict[str, Any] | None,
        book_key: str,
        owned: bool,
        read: bool,
        wanted: bool = True,
        list_id: str | None = None,
    ) -> None:
        save_book_state(self.data_dir, book_key, owned, read, wanted)

    async def save_book_states(
        self,
        user: dict[str, Any] | None,
        book_states: dict[str, dict[str, bool]],
        list_id: str | None = None,
    ) -> None:
        save_book_states(self.data_dir, book_states)


class SupabaseStore:
    def __init__(self, supabase_url: str, publishable_key: str) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self.publishable_key = publishable_key

    async def load_library(
        self, user: dict[str, Any] | None, list_id: str | None = None
    ) -> dict[str, Any]:
        current_user = _require_user(user)
        lists = await self.list_lists(current_user)
        current_list = _select_list(lists, list_id)
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
            f"/rest/v1/book_states?select=book_id,owned,read,wanted&list_id=eq.{current_list['id']}",
        )
        library = _merge_rows(series_rows, book_rows, state_rows)
        library["lists"] = lists
        library["current_list"] = current_list
        return library

    async def list_lists(self, user: dict[str, Any] | None) -> list[dict[str, Any]]:
        current_user = _require_user(user)
        memberships = await self._request(
            current_user,
            "GET",
            "/rest/v1/list_members?select=list_id,role,lists(id,name,owner_user_id)&order=created_at.asc",
        )
        if not memberships:
            await self._create_personal_list(current_user)
            memberships = await self._request(
                current_user,
                "GET",
                "/rest/v1/list_members?select=list_id,role,lists(id,name,owner_user_id)&order=created_at.asc",
            )
        return [_membership_list(membership, current_user["id"]) for membership in memberships]

    async def share_list(
        self,
        user: dict[str, Any] | None,
        list_id: str,
        email: str,
        role: str,
    ) -> None:
        current_user = _require_user(user)
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("Email address is required.")
        if role not in {"editor", "viewer"}:
            raise ValueError("Shared list role must be editor or viewer.")
        await self._request(
            current_user,
            "POST",
            "/rest/v1/rpc/add_list_member_by_email",
            json={
                "target_list_id": list_id,
                "member_email": normalized_email,
                "member_role": role,
            },
        )

    async def can_suggest_series(self, user: dict[str, Any] | None) -> bool:
        current_user = _require_user(user)
        rows = await self._request(
            current_user,
            "GET",
            "/rest/v1/ai_series_suggestion_allowed_users?select=id&limit=1",
        )
        return bool(rows)

    async def suggestion_count_today(self, user: dict[str, Any] | None) -> int:
        current_user = _require_user(user)
        rows = await self._request(
            current_user,
            "POST",
            "/rest/v1/rpc/count_ai_series_suggestions_today",
            json={},
        )
        if not isinstance(rows, int):
            raise ValueError("Supabase suggestion count response was not an integer.")
        return rows

    async def create_series_suggestion(
        self,
        user: dict[str, Any] | None,
        prompt: str,
        status: str,
        proposal: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        current_user = _require_user(user)
        rows = await self._request(
            current_user,
            "POST",
            "/rest/v1/ai_series_suggestions",
            json={
                "requested_by_user_id": current_user["id"],
                "prompt": prompt,
                "status": status,
                "proposal": proposal,
                "sources": _proposal_sources(proposal),
                "error": error,
            },
            extra_headers={"Prefer": "return=representation"},
        )
        return rows[0]

    async def get_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> dict[str, Any]:
        current_user = _require_user(user)
        rows = await self._request(
            current_user,
            "GET",
            f"/rest/v1/ai_series_suggestions?select=*&id=eq.{suggestion_id}&limit=1",
        )
        if not rows:
            raise ValueError(f"Unknown series suggestion id: {suggestion_id}")
        return rows[0]

    async def approve_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None:
        current_user = _require_user(user)
        await self._request(
            current_user,
            "POST",
            "/rest/v1/rpc/approve_ai_series_suggestion",
            json={"suggestion_id": suggestion_id},
        )

    async def reject_series_suggestion(
        self, user: dict[str, Any] | None, suggestion_id: str
    ) -> None:
        current_user = _require_user(user)
        await self._request(
            current_user,
            "POST",
            "/rest/v1/rpc/reject_ai_series_suggestion",
            json={"suggestion_id": suggestion_id},
        )

    async def save_book_state(
        self,
        user: dict[str, Any] | None,
        book_key: str,
        owned: bool,
        read: bool,
        wanted: bool = True,
        list_id: str | None = None,
    ) -> None:
        await self.save_book_states(
            user, {book_key: {"owned": owned, "read": read, "wanted": wanted}}, list_id
        )

    async def save_book_states(
        self,
        user: dict[str, Any] | None,
        book_states: dict[str, dict[str, bool]],
        list_id: str | None = None,
    ) -> None:
        current_user = _require_user(user)
        lists = await self.list_lists(current_user)
        current_list = _select_list(lists, list_id)
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
                "list_id": current_list["id"],
                "book_id": ids_by_key[book_key],
                "owned": book_state["owned"],
                "read": book_state["read"],
                "wanted": book_state.get("wanted", True),
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

    async def _create_personal_list(self, user: dict[str, Any]) -> str:
        inserted_lists = await self._request(
            user,
            "POST",
            "/rest/v1/lists",
            json={"name": DEFAULT_LIST_NAME, "owner_user_id": user["id"]},
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


def _file_list() -> dict[str, Any]:
    return {"id": "file", "name": DEFAULT_LIST_NAME, "role": "owner", "is_owner": True}


def _require_user(user: dict[str, Any] | None) -> dict[str, Any]:
    if user is None:
        raise ValueError("Supabase storage requires an authenticated user.")
    return user


def _select_list(lists: list[dict[str, Any]], list_id: str | None) -> dict[str, Any]:
    if not lists:
        raise ValueError("User has no lists.")
    if list_id:
        for book_list in lists:
            if book_list["id"] == list_id:
                return book_list
        raise ValueError(f"Unknown or inaccessible list id: {list_id}")
    return lists[0]


def _membership_list(membership: dict[str, Any], current_user_id: str) -> dict[str, Any]:
    book_list = membership.get("lists")
    if not isinstance(book_list, dict):
        raise ValueError("List membership response did not include list details.")
    owner_user_id = book_list.get("owner_user_id")
    return {
        "id": membership["list_id"],
        "name": book_list["name"],
        "role": membership["role"],
        "is_owner": owner_user_id == current_user_id,
    }


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
            "wanted": bool(state.get("wanted", True)),
            "cover_url": _openlibrary_cover_url(row.get("openlibrary_cover_id")),
        }
        books_by_series.setdefault(row["series_id"], []).append(book)
        books_by_key[row["key"]] = book

    merged_series = []
    for row in series_rows:
        books = books_by_series.get(row["id"], [])
        owned_count = sum(1 for book in books if book["owned"])
        read_count = sum(1 for book in books if book["read"])
        wanted_count = sum(1 for book in books if book["wanted"] and not book["owned"])
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
                "wanted_count": wanted_count,
                "missing_count": wanted_count,
            }
        )
    return {"series": merged_series, "books_by_key": books_by_key, "warnings": []}


def _openlibrary_cover_url(cover_id: int | None) -> str | None:
    if cover_id is None:
        return None
    return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


def _proposal_sources(proposal: dict[str, Any] | None) -> Any | None:
    if not proposal:
        return None
    return proposal.get("source")
