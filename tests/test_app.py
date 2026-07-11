from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from starlette.testclient import TestClient

import app as app_module
from booksequencer.config import Settings


class AppTests(unittest.TestCase):
    def test_series_and_shop_pages_reflect_saved_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            self.assertEqual(client.get("/").status_code, 200)
            self.assertEqual(client.get("/series/example-series").status_code, 200)
            shop_response = client.get("/shop")
            self.assertEqual(shop_response.status_code, 200)
            self.assertIn("Second Book", shop_response.text)

            post_response = client.post(
                "/books/example-series/second-book/state?next=/shop",
                data={"owned": "on", "read": "on"},
                follow_redirects=False,
            )
            self.assertEqual(post_response.status_code, 303)
            self.assertEqual(post_response.headers["location"], "/shop")
            self.assertNotIn("Second Book", client.get("/shop").text)

    def test_supabase_storage_redirects_anonymous_users_to_login(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login?next=/")

    def test_series_page_can_sort_by_title(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.get("/series/example-series?sort=title")

            self.assertEqual(response.status_code, 200)
            self.assertLess(response.text.index("Aardvark Book"), response.text.index("First Book"))
            self.assertIn("Alphabetical", response.text)
            self.assertIn("Series order", response.text)

    def test_series_bulk_save_preserves_sort_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.post(
                "/series/example-series/state?sort=title",
                data={
                    "book_key": [
                        "example-series/first-book",
                        "example-series/second-book",
                    ],
                    "owned": ["example-series/second-book"],
                    "read": ["example-series/second-book"],
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 303)
            self.assertEqual(
                response.headers["location"],
                "http://testserver/series/example-series?sort=title",
            )

    def test_lists_page_loads_for_file_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.get("/lists")

            self.assertEqual(response.status_code, 200)
            self.assertIn("My books", response.text)
            self.assertIn("Currently selected", response.text)

    def test_series_bulk_save_persists_multiple_changed_books(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.post(
                "/series/example-series/state",
                data={
                    "book_key": [
                        "example-series/first-book",
                        "example-series/second-book",
                    ],
                    "owned": [
                        "example-series/first-book",
                        "example-series/second-book",
                    ],
                    "read": [
                        "example-series/first-book",
                        "example-series/second-book",
                    ],
                },
                follow_redirects=False,
            )

            self.assertEqual(response.status_code, 303)
            with (data_dir / "state.yaml").open(encoding="utf-8") as handle:
                state = yaml.safe_load(handle)
            self.assertTrue(state["books"]["example-series/first-book"]["owned"])
            self.assertTrue(state["books"]["example-series/second-book"]["owned"])
            self.assertTrue(state["books"]["example-series/first-book"]["read"])
            self.assertTrue(state["books"]["example-series/second-book"]["read"])

    def _create_file_app(self, data_dir: Path):
        return app_module.create_app(settings=self._settings(data_dir))

    def _settings(self, data_dir: Path, storage: str = "file") -> Settings:
        return Settings(
            storage=storage,
            data_dir=data_dir,
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="test-key",
            session_secret="test-secret",
            debug=True,
        )

    def _write_data(self, data_dir: Path) -> None:
        series_dir = data_dir / "series"
        series_dir.mkdir(parents=True)
        self._write_yaml(
            series_dir / "example-series.yaml",
            {
                "id": "example-series",
                "title": "Example Series",
                "author": "Example Author",
                "books": [
                    {"id": "first-book", "title": "First Book", "position": 1},
                    {"id": "second-book", "title": "Second Book", "position": 2},
                    {"id": "aardvark-book", "title": "Aardvark Book", "position": 3},
                ],
            },
        )
        self._write_yaml(
            data_dir / "state.yaml",
            {
                "books": {
                    "example-series/first-book": {"owned": True, "read": True},
                    "example-series/second-book": {"owned": False, "read": True},
                    "example-series/aardvark-book": {"owned": False, "read": False},
                }
            },
        )

    def _write_yaml(self, path: Path, data: dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle)


class FailingStore:
    async def load_library(self, user, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def list_lists(self, user):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def share_list(self, user, list_id, email, role):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def save_book_state(self, user, book_key, owned, read, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def save_book_states(self, user, book_states, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")


if __name__ == "__main__":
    unittest.main()
