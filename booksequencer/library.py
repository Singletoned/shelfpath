from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SERIES_DIR_NAME = "series"
STATE_FILE_NAME = "state.yaml"
BOOK_STATE_ROOT = "books"


class LibraryValidationError(ValueError):
    """Raised when catalogue data is malformed."""


def load_library(data_dir: Path) -> dict[str, Any]:
    series_dir = data_dir / SERIES_DIR_NAME
    state_path = data_dir / STATE_FILE_NAME

    if not data_dir.exists():
        raise FileNotFoundError(
            f"Data directory {data_dir} does not exist. Copy data.example to data and edit it."
        )
    if not series_dir.exists():
        raise FileNotFoundError(f"Series directory {series_dir} does not exist.")
    if not state_path.exists():
        raise FileNotFoundError(f"State file {state_path} does not exist.")

    series = _load_series_files(series_dir)
    state = _load_state(state_path)
    return _merge_library(series, state)


def save_book_state(data_dir: Path, book_key: str, owned: bool, read: bool) -> None:
    library = load_library(data_dir)
    if book_key not in library["books_by_key"]:
        raise LibraryValidationError(f"Unknown book key: {book_key}")

    state_path = data_dir / STATE_FILE_NAME
    state = _load_state(state_path)
    books = state.setdefault(BOOK_STATE_ROOT, {})
    books[book_key] = {"owned": owned, "read": read}
    _write_yaml(state_path, state)


def _load_series_files(series_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(series_dir.glob("*.yaml"))
    if not paths:
        raise LibraryValidationError(f"No series YAML files found in {series_dir}.")

    series = []
    seen_series_ids: set[str] = set()
    for path in paths:
        loaded = _read_yaml(path)
        if not isinstance(loaded, dict):
            raise LibraryValidationError(f"{path} must contain a YAML mapping.")
        validated = _validate_series(path, loaded)
        series_id = validated["id"]
        if series_id in seen_series_ids:
            raise LibraryValidationError(f"Duplicate series id: {series_id}")
        seen_series_ids.add(series_id)
        series.append(validated)
    return series


def _validate_series(path: Path, series: dict[str, Any]) -> dict[str, Any]:
    series_id = _required_string(path, series, "id")
    title = _required_string(path, series, "title")
    author = _optional_string(path, series, "author")
    order = _optional_string(path, series, "order")
    source = _optional_source(path, series)
    books = series.get("books")
    if not isinstance(books, list):
        raise LibraryValidationError(f"{path}: books must be a list.")

    seen_book_ids: set[str] = set()
    validated_books = []
    for index, book in enumerate(books, start=1):
        if not isinstance(book, dict):
            raise LibraryValidationError(f"{path}: book {index} must be a mapping.")
        book_id = _required_string(path, book, "id")
        if book_id in seen_book_ids:
            raise LibraryValidationError(f"{path}: duplicate book id {book_id!r}.")
        seen_book_ids.add(book_id)
        validated_books.append(
            {
                "id": book_id,
                "title": _required_string(path, book, "title"),
                "position": book.get("position", index),
                "author": _optional_string(path, book, "author") or author,
            }
        )

    return {
        "id": series_id,
        "title": title,
        "author": author,
        "order": order,
        "source": source,
        "books": validated_books,
    }


def _load_state(state_path: Path) -> dict[str, Any]:
    state = _read_yaml(state_path)
    if state is None:
        state = {}
    if not isinstance(state, dict):
        raise LibraryValidationError(f"{state_path} must contain a YAML mapping.")
    books = state.setdefault(BOOK_STATE_ROOT, {})
    if not isinstance(books, dict):
        raise LibraryValidationError(f"{state_path}: books must be a mapping.")

    for book_key, book_state in books.items():
        if not isinstance(book_key, str):
            raise LibraryValidationError(f"{state_path}: state keys must be strings.")
        if not isinstance(book_state, dict):
            raise LibraryValidationError(f"{state_path}: {book_key} state must be a mapping.")
        _validate_bool(state_path, book_key, book_state, "owned")
        _validate_bool(state_path, book_key, book_state, "read")
    return state


def _merge_library(series: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    state_books = state[BOOK_STATE_ROOT]
    books_by_key = {}
    warnings = []
    merged_series = []

    for series_item in series:
        merged_books = []
        owned_count = 0
        read_count = 0
        for book in series_item["books"]:
            book_key = f"{series_item['id']}/{book['id']}"
            book_state = state_books.get(book_key, {})
            owned = bool(book_state.get("owned", False))
            read = bool(book_state.get("read", False))
            merged_book = {
                **book,
                "key": book_key,
                "owned": owned,
                "read": read,
            }
            books_by_key[book_key] = merged_book
            merged_books.append(merged_book)
            if owned:
                owned_count += 1
            if read:
                read_count += 1

        merged_series.append(
            {
                **series_item,
                "books": merged_books,
                "book_count": len(merged_books),
                "owned_count": owned_count,
                "read_count": read_count,
                "missing_count": len(merged_books) - owned_count,
            }
        )

    for book_key in state_books:
        if book_key not in books_by_key:
            warnings.append(f"State contains unknown book key: {book_key}")

    return {"series": merged_series, "books_by_key": books_by_key, "warnings": warnings}


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=True, allow_unicode=True)


def _required_string(path: Path, data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LibraryValidationError(f"{path}: {field} must be a non-empty string.")
    return value


def _optional_string(path: Path, data: dict[str, Any], field: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LibraryValidationError(f"{path}: {field} must be a non-empty string when set.")
    return value


def _optional_source(path: Path, data: dict[str, Any]) -> dict[str, str] | None:
    source = data.get("source")
    if source is None:
        return None
    if not isinstance(source, dict):
        raise LibraryValidationError(f"{path}: source must be a mapping when set.")

    validated = {}
    for field in ("name", "url", "accessed", "notes"):
        value = source.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise LibraryValidationError(
                f"{path}: source.{field} must be a non-empty string when set."
            )
        validated[field] = value
    if not validated:
        raise LibraryValidationError(f"{path}: source must contain at least one field.")
    return validated


def _validate_bool(path: Path, book_key: str, book_state: dict[str, Any], field: str) -> None:
    value = book_state.get(field, False)
    if not isinstance(value, bool):
        raise LibraryValidationError(f"{path}: {book_key}.{field} must be true or false.")
