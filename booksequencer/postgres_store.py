from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from booksequencer.store import DEFAULT_LIST_NAME, _merge_rows, _require_user, _select_list


class PostgresStore:
    """Direct Postgres persistence for Shelfpath's catalogue and list state."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def load_library(
        self, user: dict[str, Any] | None, list_id: str | None = None
    ) -> dict[str, Any]:
        current_user = _require_user(user)
        lists = await self.list_lists(current_user)
        current_list = _select_list(lists, list_id)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute("select * from series order by title")
            series = cursor.fetchall()
            cursor.execute("select * from books order by series_id, position")
            books = cursor.fetchall()
            cursor.execute(
                "select book_id, owned, read, wanted from book_states where list_id = %s",
                (current_list["id"],),
            )
            states = cursor.fetchall()
        library = _merge_rows(series, books, states)
        library["lists"] = lists
        library["current_list"] = current_list
        return library

    async def list_lists(self, user: dict[str, Any] | None) -> list[dict[str, Any]]:
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            self._upsert_user(cursor, current_user)
            cursor.execute(
                """
                select l.id, l.name, l.owner_clerk_user_id, lm.role
                from list_members lm join lists l on l.id = lm.list_id
                where lm.clerk_user_id = %s order by l.created_at
                """,
                (current_user["id"],),
            )
            rows = cursor.fetchall()
            if not rows:
                cursor.execute(
                    "insert into lists (name, owner_clerk_user_id) values (%s, %s) returning id",
                    (DEFAULT_LIST_NAME, current_user["id"]),
                )
                list_id = cursor.fetchone()["id"]
                cursor.execute(
                    """
                    insert into list_members (list_id, clerk_user_id, role)
                    values (%s, %s, 'owner')
                    """,
                    (list_id, current_user["id"]),
                )
                rows = [
                    {
                        "id": list_id,
                        "name": DEFAULT_LIST_NAME,
                        "owner_clerk_user_id": current_user["id"],
                        "role": "owner",
                    }
                ]
        return [
            {**row, "is_owner": row["owner_clerk_user_id"] == current_user["id"]} for row in rows
        ]

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
        current_list = _select_list(await self.list_lists(current_user), list_id)
        if current_list["role"] == "viewer":
            raise PermissionError("View-only members cannot change book states.")
        with self._connection() as connection, connection.cursor() as cursor:
            for key, state in book_states.items():
                cursor.execute("select id from books where key = %s", (key,))
                row = cursor.fetchone()
                if row is None:
                    raise ValueError(f"Unknown book key: {key}")
                cursor.execute(
                    """
                    insert into book_states (list_id, book_id, owned, read, wanted)
                    values (%s, %s, %s, %s, %s)
                    on conflict (list_id, book_id) do update set
                      owned = excluded.owned, read = excluded.read, wanted = excluded.wanted,
                      updated_at = now()
                    """,
                    (
                        current_list["id"],
                        row["id"],
                        state["owned"],
                        state["read"],
                        state.get("wanted", True),
                    ),
                )

    async def local_test_user(self, email: str, password: str | None) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("SHELFPATH_LOCAL_AUTH_EMAIL must not be empty.")
        return {"id": f"local:{normalized_email}", "email": normalized_email, "local_auth": True}

    async def update_list_person_role(self, user, list_id, email, role) -> None:
        current_user = _require_user(user)
        if role not in {"editor", "viewer"}:
            raise ValueError("Shared list role must be editor or viewer.")
        with self._connection() as connection, connection.cursor() as cursor:
            self._require_owner(cursor, current_user["id"], list_id)
            cursor.execute(
                "select clerk_user_id from users where email = %s", (email.strip().lower(),)
            )
            person = cursor.fetchone()
            if person is None:
                raise ValueError("That person must sign in to Shelfpath before they can be added.")
            cursor.execute(
                """
                insert into list_members (list_id, clerk_user_id, role) values (%s, %s, %s)
                on conflict (list_id, clerk_user_id) do update set role = excluded.role
                """,
                (list_id, person["clerk_user_id"], role),
            )

    async def accept_list_invitation(self, user, list_id, role) -> None:
        current_user = _require_user(user)
        if role not in {"editor", "viewer"}:
            raise ValueError("Invitation role must be editor or viewer.")
        with self._connection() as connection, connection.cursor() as cursor:
            self._upsert_user(cursor, current_user)
            cursor.execute(
                """
                insert into list_members (list_id, clerk_user_id, role) values (%s, %s, %s)
                on conflict (list_id, clerk_user_id) do update set role = excluded.role
                """,
                (list_id, current_user["id"], role),
            )

    async def get_list_people(self, user, list_id) -> dict[str, Any]:
        current_user = _require_user(user)
        lists = await self.list_lists(current_user)
        book_list = _select_list([item for item in lists if item["id"] == list_id], list_id)
        if not book_list["is_owner"]:
            raise ValueError("Only the list owner can manage people.")
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select u.email, lm.role from list_members lm
                join users u on u.clerk_user_id = lm.clerk_user_id
                where lm.list_id = %s order by lm.created_at
                """,
                (list_id,),
            )
            people = cursor.fetchall()
        return {"list": book_list, "people": people}

    async def remove_list_person(self, user, list_id, email) -> None:
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            self._require_owner(cursor, current_user["id"], list_id)
            cursor.execute(
                """
                delete from list_members using users
                where list_members.clerk_user_id = users.clerk_user_id
                  and list_members.list_id = %s
                  and users.email = %s and list_members.role != 'owner'
                """,
                (list_id, email.strip().lower()),
            )

    async def can_suggest_series(self, user) -> bool:
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "select 1 from ai_series_suggestion_allowed_users where clerk_user_id = %s",
                (current_user["id"],),
            )
            return cursor.fetchone() is not None

    async def suggestion_count_today(self, user) -> int:
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select count(*) as count from ai_series_suggestions
                where requested_by_clerk_user_id = %s and created_at >= current_date
                """,
                (current_user["id"],),
            )
            return cursor.fetchone()["count"]

    async def create_series_suggestion(self, user, prompt, status, proposal=None, error=None):
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into ai_series_suggestions
                  (requested_by_clerk_user_id, prompt, status, proposal, source_urls,
                   failure_message)
                values (%s, %s, %s, %s, %s, %s) returning *
                """,
                (
                    current_user["id"],
                    prompt,
                    status,
                    psycopg.types.json.Jsonb(proposal) if proposal else None,
                    psycopg.types.json.Jsonb(proposal.get("source")) if proposal else None,
                    error,
                ),
            )
            return cursor.fetchone()

    async def get_series_suggestion(self, user, suggestion_id):
        _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select *, failure_message as error, source_urls as sources
                from ai_series_suggestions where id = %s
                """,
                (suggestion_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Unknown series suggestion id: {suggestion_id}")
        return row

    async def approve_series_suggestion(self, user, suggestion_id) -> None:
        raise NotImplementedError("Postgres suggestion approval has not been migrated yet.")

    async def reject_series_suggestion(self, user, suggestion_id) -> None:
        current_user = _require_user(user)
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                update ai_series_suggestions set status = 'rejected', decided_at = now()
                where id = %s and requested_by_clerk_user_id = %s
                """,
                (suggestion_id, current_user["id"]),
            )

    def _connection(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _upsert_user(self, cursor, user):
        cursor.execute(
            """
            insert into users (clerk_user_id, email) values (%s, %s)
            on conflict (clerk_user_id) do update set email = excluded.email
            """,
            (user["id"], user.get("email")),
        )

    def _require_owner(self, cursor, user_id, list_id):
        cursor.execute(
            "select 1 from lists where id = %s and owner_clerk_user_id = %s", (list_id, user_id)
        )
        if cursor.fetchone() is None:
            raise ValueError("Only the list owner can manage people.")
