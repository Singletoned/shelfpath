from __future__ import annotations

import json
import os
import re
import unittest
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

from booksequencer.invitations import create_invitation_token

BASE_URL = os.environ.get("SHELFPATH_E2E_BASE_URL", "http://shelfpath:8731")
SUPABASE_URL = os.environ.get("SHELFPATH_E2E_SUPABASE_URL", "http://supabase_kong_shelfpath:8000")
RESEND_URL = os.environ["SHELFPATH_E2E_RESEND_URL"]


class LocalStackE2ETests(unittest.TestCase):
    def test_health_endpoint_is_available(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                response = page.goto(f"{BASE_URL}/health")

                self.assertIsNotNone(response)
                self.assertEqual(response.status, 200)
                self.assertEqual(page.text_content("body"), '{"status":"ok"}')
            finally:
                browser.close()

    def test_series_card_opens_when_its_progress_area_is_clicked(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{BASE_URL}/login?next=/")

                page.locator('a[href$="/series/discworld"] .progress-track').click()

                expect(page).to_have_url(f"{BASE_URL}/series/discworld")
            finally:
                browser.close()

    def test_owning_a_book_removes_its_hunting_tint_immediately(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{BASE_URL}/login?next=/series/discworld")

                first_row = page.locator(".book-row").first
                expect(first_row).to_have_class(re.compile(r".*\bhunting\b.*"))
                first_row.locator('.chip-input[data-status="owned"]').check(force=True)

                expect(first_row).not_to_have_class(re.compile(r".*\bhunting\b.*"))
                expect(first_row.locator("[data-save-status]")).to_have_text("Saved")
            finally:
                browser.close()

    def test_failed_suggestion_is_saved_without_a_privilege_error(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{BASE_URL}/login?next=/suggest")
                page.locator('textarea[name="prompt"]').fill("A test series")
                page.get_by_role("button", name="Investigate series").click()

                expect(page.get_by_role("heading", name="Series suggestion")).to_be_visible()
                expect(page.get_by_text("Investigation failed")).to_be_visible()
                self.assertNotIn("Supabase request failed", page.content())
            finally:
                browser.close()

    def test_owner_can_invite_a_new_user_who_receives_email_and_accepts_the_list(self):
        recipient_email = "shared-list-recipient@shelfpath.test"
        recipient_password = "recipient-password"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                owner = browser.new_page()
                owner.goto(f"{BASE_URL}/login?next=/lists")
                owner.get_by_role("link", name="Manage people").click()
                expect(owner.get_by_role("heading", name="People")).to_be_visible()
                list_id = owner.locator('input[name="list_id"]').input_value()
                owner.get_by_label("Email address").fill(recipient_email)
                owner.get_by_label("Access").select_option("editor")
                owner.get_by_role("button", name="Send invite").click()

                expect(owner.get_by_text(f"Invitation sent to {recipient_email}.")).to_be_visible()
                messages = _json_get(f"{RESEND_URL}/messages")
                self.assertIn(recipient_email, json.dumps(messages))
                self.assertIn("You were invited", json.dumps(messages))

                session = _create_recipient_session(recipient_email, recipient_password)
                token = create_invitation_token(
                    list_id,
                    recipient_email,
                    "editor",
                    os.environ["SHELFPATH_INVITATION_TOKEN_SECRET"],
                )
                recipient_context = browser.new_context()
                recipient = recipient_context.new_page()
                recipient.request.post(f"{BASE_URL}/logout")
                session_response = recipient.request.post(
                    f"{BASE_URL}/auth/session",
                    data={
                        "access_token": session["access_token"],
                        "refresh_token": session["refresh_token"],
                        "expires_at": session["expires_at"],
                    },
                )
                self.assertEqual(session_response.status, 200)
                recipient.goto(f"{BASE_URL}/invite/{list_id}/editor/{token}")

                expect(recipient).to_have_url(f"{BASE_URL}/lists?joined={list_id}")
                expect(
                    recipient.get_by_text("You now have access to this shared list.")
                ).to_be_visible()
                expect(recipient.get_by_text("Role: editor")).to_be_visible()
                recipient_context.close()
            finally:
                browser.close()

    def test_local_login_can_open_allowed_suggestions_page(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{BASE_URL}/login?next=/suggest")

                expect(page).to_have_url(f"{BASE_URL}/suggest")
                expect(page.get_by_role("heading", name="Suggest a series")).to_be_visible()
                expect(page.get_by_role("button", name="Investigate series")).to_be_visible()
            finally:
                browser.close()


def _create_recipient_session(email: str, password: str) -> dict:
    service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    _json_post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        {"email": email, "password": password, "email_confirm": True},
        {"apikey": service_role_key, "Authorization": f"Bearer {service_role_key}"},
    )
    return _json_post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        {"email": email, "password": password},
        {"apikey": os.environ["SUPABASE_PUBLISHABLE_KEY"]},
    )


def _json_get(url: str) -> dict:
    with urlopen(url, timeout=20) as response:
        return json.load(response)


def _json_post(url: str, payload: dict, headers: dict[str, str]) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


if __name__ == "__main__":
    unittest.main()
