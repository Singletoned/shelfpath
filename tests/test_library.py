from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from booksequencer.library import LibraryValidationError, load_library, save_book_state


class LibraryTests(unittest.TestCase):
    def test_loads_series_and_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_valid_data(data_dir)

            library = load_library(data_dir)

            series = library["series"][0]
            self.assertEqual(series["title"], "Example Series")
            self.assertEqual(series["book_count"], 2)
            self.assertEqual(series["owned_count"], 1)
            self.assertEqual(series["read_count"], 2)
            self.assertEqual(series["missing_count"], 1)
            self.assertTrue(series["books"][1]["read"])
            self.assertFalse(series["books"][1]["owned"])

    def test_saves_book_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_valid_data(data_dir)

            save_book_state(data_dir, "example-series/second-book", owned=True, read=True)

            library = load_library(data_dir)
            second_book = library["books_by_key"]["example-series/second-book"]
            self.assertTrue(second_book["owned"])
            self.assertTrue(second_book["read"])

    def test_rejects_duplicate_book_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_valid_data(
                data_dir,
                books=[
                    {"id": "same", "title": "One"},
                    {"id": "same", "title": "Two"},
                ],
            )

            with self.assertRaisesRegex(LibraryValidationError, "duplicate book id"):
                load_library(data_dir)

    def test_rejects_non_boolean_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_valid_data(data_dir)
            self._write_yaml(
                data_dir / "state.yaml",
                {"books": {"example-series/first-book": {"owned": "yes", "read": True}}},
            )

            with self.assertRaisesRegex(LibraryValidationError, "owned must be true or false"):
                load_library(data_dir)

    def test_warns_about_unknown_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_valid_data(data_dir)
            self._write_yaml(
                data_dir / "state.yaml",
                {"books": {"example-series/missing-book": {"owned": True, "read": False}}},
            )

            library = load_library(data_dir)

            self.assertEqual(
                library["warnings"],
                ["State contains unknown book key: example-series/missing-book"],
            )

    def _write_valid_data(self, data_dir: Path, books: list[dict] | None = None) -> None:
        if books is None:
            books = [
                {"id": "first-book", "title": "First Book", "position": 1},
                {"id": "second-book", "title": "Second Book", "position": 2},
            ]
        series_dir = data_dir / "series"
        series_dir.mkdir(parents=True)
        self._write_yaml(
            series_dir / "example-series.yaml",
            {
                "id": "example-series",
                "title": "Example Series",
                "author": "Example Author",
                "books": books,
            },
        )
        self._write_yaml(
            data_dir / "state.yaml",
            {
                "books": {
                    "example-series/first-book": {"owned": True, "read": True},
                    "example-series/second-book": {"owned": False, "read": True},
                }
            },
        )

    def _write_yaml(self, path: Path, data: dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle)


if __name__ == "__main__":
    unittest.main()
