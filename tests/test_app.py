from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml
from starlette.testclient import TestClient

import app as app_module
from booksequencer.config import Settings


class AppTests(unittest.TestCase):
    def test_icon_assets_are_publicly_available(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        favicon = client.get("/static/icons/favicon.svg")
        manifest = client.get("/static/site.webmanifest")

        self.assertEqual(favicon.status_code, 200)
        self.assertIn("image/svg+xml", favicon.headers["content-type"])
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("Shelfpath", manifest.text)

    def test_health_endpoint_does_not_require_authentication(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

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

    def test_supabase_storage_shows_anonymous_users_the_splash_page(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        response = client.get("/", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Know whether to buy it", response.text)
        self.assertIn("Sign in or create an account", response.text)
        self.assertIn('id="login-form"', response.text)
        self.assertIn('class="shop-verdict wanted"', response.text)
        self.assertIn('class="shop-book"', response.text)
        self.assertIn('class="book-row hunting"', response.text)

    def test_login_page_uses_a_constrained_spaced_form(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        response = client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="login-page"', response.text)
        self.assertIn('class="login-form"', response.text)
        self.assertIn('class="login-intro"', response.text)

    def test_login_redirect_preserves_requested_query(self):
        settings = self._settings(Path("unused"), storage="supabase")
        app = app_module.create_app(settings=settings, store=FailingStore())
        client = TestClient(app)

        response = client.get("/shop?q=The+Colour+of+Magic", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            response.headers["location"],
            "/login?next=/shop%3Fq%3DThe%2BColour%2Bof%2BMagic",
        )

    def test_local_auth_mode_sets_session_without_magic_link(self):
        settings = self._settings(Path("unused"), storage="supabase").__class__(
            **{
                **self._settings(Path("unused"), storage="supabase").__dict__,
                "local_auth_email": "test@example.invalid",
                "local_auth_password": "local-password",
                "supabase_service_role_key": "service-role-key",
            }
        )
        store = LocalAuthStore()
        app = app_module.create_app(settings=settings, store=store)
        client = TestClient(app)

        response = client.get("/login?next=/shop", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/shop")
        self.assertEqual(store.email, "test@example.invalid")

    def test_local_logout_shows_local_sign_in_action(self):
        settings = self._settings(Path("unused"), storage="supabase").__class__(
            **{
                **self._settings(Path("unused"), storage="supabase").__dict__,
                "local_auth_email": "test@example.invalid",
                "local_auth_password": "local-password",
                "supabase_service_role_key": "service-role-key",
            }
        )
        store = LocalAuthStore()
        client = TestClient(app_module.create_app(settings=settings, store=store))

        client.get("/login")
        logout_response = client.post("/logout", follow_redirects=False)
        signed_out_page = client.get("/login?local_signed_out=1")
        protected_response = client.get("/", follow_redirects=False)
        sign_in_response = client.post(
            "/login/local", data={"next": "/shop"}, follow_redirects=False
        )

        self.assertEqual(logout_response.status_code, 303)
        self.assertEqual(logout_response.headers["location"], "/login?local_signed_out=1")
        self.assertEqual(signed_out_page.status_code, 200)
        self.assertIn("Sign in as local test user", signed_out_page.text)
        self.assertEqual(protected_response.status_code, 200)
        self.assertIn("Sign in or create an account", protected_response.text)
        self.assertEqual(sign_in_response.status_code, 303)
        self.assertEqual(sign_in_response.headers["location"], "/shop")

    def test_local_auth_refreshes_stale_user_after_a_database_reset(self):
        settings = self._settings(Path("unused"), storage="supabase").__class__(
            **{
                **self._settings(Path("unused"), storage="supabase").__dict__,
                "local_auth_email": "test@example.invalid",
                "local_auth_password": "local-password",
                "supabase_service_role_key": "service-role-key",
            }
        )
        store = LocalAuthStore(
            user_ids=[
                "00000000-0000-0000-0000-000000000001",
                "00000000-0000-0000-0000-000000000002",
            ]
        )
        client = TestClient(app_module.create_app(settings=settings, store=store))

        client.get("/login")
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(store.loaded_user_id, "00000000-0000-0000-0000-000000000002")

    def test_invitation_grants_the_signed_in_recipient_access(self):
        settings = self._settings(Path("unused"), storage="supabase").__class__(
            **{
                **self._settings(Path("unused"), storage="supabase").__dict__,
                "local_auth_email": "reader@example.test",
                "local_auth_password": "local-password",
                "supabase_service_role_key": "service-role-key",
            }
        )
        store = InvitationStore()
        client = TestClient(app_module.create_app(settings=settings, store=store))
        token = app_module.create_invitation_token(
            "00000000-0000-0000-0000-000000000001",
            "reader@example.test",
            "editor",
            settings.invitation_token_secret,
        )

        response = client.get(
            f"/invite/00000000-0000-0000-0000-000000000001/editor/{token}",
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            response.headers["location"],
            "/lists?joined=00000000-0000-0000-0000-000000000001",
        )
        self.assertEqual(store.accepted, ("00000000-0000-0000-0000-000000000001", "editor"))

    def test_home_shows_owned_unread_books_as_next_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertIn("Next up", response.text)
            self.assertIn("Ready to read", response.text)
            self.assertIn("Aardvark Book", response.text)
            next_up_html = response.text.split('class="next-up-list"', maxsplit=1)[1].split(
                "</aside>", maxsplit=1
            )[0]
            self.assertIn('name="read"', next_up_html)
            self.assertNotIn('name="wanted"', next_up_html)
            self.assertNotIn('name="owned"', next_up_html)

    def test_home_does_not_recommend_a_book_before_an_unread_predecessor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            state_path = data_dir / "state.yaml"
            with state_path.open(encoding="utf-8") as handle:
                state = yaml.safe_load(handle)
            state["books"]["example-series/second-book"]["read"] = False
            self._write_yaml(state_path, state)
            client = TestClient(self._create_file_app(data_dir))

            response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertNotIn("Aardvark Book", response.text)
            self.assertNotIn('class="next-up-list"', response.text)

    def test_home_series_card_is_a_single_full_card_link(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.get("/")

            self.assertIn('class="wordmark-logo"', response.text)
            self.assertIn("/static/icons/app-icon-1024-square.svg", response.text)
            self.assertIn('class="card series-card-link"', response.text)
            self.assertRegex(
                response.text,
                r'href="(?:https?://[^\"]+)?/series/example-series"',
            )
            self.assertNotRegex(response.text, r"<h3>\s*<a\b")

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

    def test_series_filters_wanted_and_owned_books(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            wanted_response = client.get("/series/example-series?filter=wanted")
            self.assertEqual(wanted_response.status_code, 200)
            self.assertIn("Second Book", wanted_response.text)
            self.assertNotIn("First Book</div>", wanted_response.text)

            owned_response = client.get("/series/example-series?filter=owned")
            self.assertEqual(owned_response.status_code, 200)
            self.assertIn("First Book", owned_response.text)
            self.assertNotIn("Second Book</div>", owned_response.text)

    def test_shop_search_shows_wanted_and_owned_verdicts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            wanted_response = client.get("/shop?q=Second+Book")
            self.assertEqual(wanted_response.status_code, 200)
            self.assertIn("Wanted · buy it", wanted_response.text)
            self.assertIn("Second Book", wanted_response.text)

            owned_response = client.get("/shop?q=First+Book")
            self.assertEqual(owned_response.status_code, 200)
            self.assertIn("Owned · skip", owned_response.text)
            self.assertIn("First Book", owned_response.text)

    def test_book_state_controls_have_automatic_save_endpoints_without_buttons(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            series_response = client.get("/series/example-series")
            shop_response = client.get("/shop")

            self.assertIn("data-book-state-url", series_response.text)
            self.assertIn("data-book-state-url", shop_response.text)
            self.assertNotIn("Save all changes", series_response.text)
            self.assertNotIn(">Save</button>", shop_response.text)

    def test_book_state_endpoint_returns_json_for_automatic_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            self._write_data(data_dir)
            client = TestClient(self._create_file_app(data_dir))

            response = client.post(
                "/books/example-series/second-book/state",
                data={"owned": "on", "read": "on"},
                headers={"accept": "application/json"},
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"saved": True})
            with (data_dir / "state.yaml").open(encoding="utf-8") as handle:
                state = yaml.safe_load(handle)
            self.assertTrue(state["books"]["example-series/second-book"]["owned"])
            self.assertTrue(state["books"]["example-series/second-book"]["read"])
            self.assertFalse(state["books"]["example-series/second-book"]["wanted"])

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
            openai_api_key=None,
            openai_model="test-model",
            local_auth_email=None,
            local_auth_password=None,
            supabase_service_role_key=None,
            resend_api_key=None,
            resend_api_url="https://resend.example.test",
            mail_from="Shelfpath <noreply@example.test>",
            public_url="http://testserver",
            invitation_token_secret="invitation-test-secret",
            sentry_dsn=None,
            sentry_environment="test",
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
                    "example-series/aardvark-book": {"owned": True, "read": False},
                }
            },
        )

    def _write_yaml(self, path: Path, data: dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle)


class LocalAuthStore:
    def __init__(self, user_ids=None):
        self.email = None
        self.loaded_user_id = None
        self.user_ids = user_ids or ["00000000-0000-0000-0000-000000000001"]

    async def local_test_user(self, email, password):
        self.email = email
        self.password = password
        user_id = self.user_ids.pop(0) if len(self.user_ids) > 1 else self.user_ids[0]
        return {
            "id": user_id,
            "email": email,
            "access_token": "service-role-key",
            "refresh_token": "local-testing",
            "expires_at": None,
            "local_auth": True,
        }

    async def load_library(self, user, list_id=None):
        self.loaded_user_id = user["id"]
        return {"current_list": None, "lists": [], "series": [], "warnings": []}


class InvitationStore(LocalAuthStore):
    def __init__(self):
        super().__init__()
        self.accepted = None

    async def accept_list_invitation(self, user, list_id, role):
        self.accepted = (list_id, role)


class FailingStore:
    async def load_library(self, user, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def list_lists(self, user):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def share_list(self, user, list_id, email, role):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def local_test_user(self, email, password):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def can_suggest_series(self, user):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def suggestion_count_today(self, user):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def create_series_suggestion(self, user, prompt, status, proposal=None, error=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def get_series_suggestion(self, user, suggestion_id):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def approve_series_suggestion(self, user, suggestion_id):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def reject_series_suggestion(self, user, suggestion_id):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def save_book_state(self, user, book_key, owned, read, wanted=True, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")

    async def save_book_states(self, user, book_states, list_id=None):
        raise AssertionError("Store should not be called for anonymous Supabase users.")


if __name__ == "__main__":
    unittest.main()
