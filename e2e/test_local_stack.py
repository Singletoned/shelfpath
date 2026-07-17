from __future__ import annotations

import os
import re
import unittest

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("SHELFPATH_E2E_BASE_URL", "http://shelfpath:8731")


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

                page.locator(".series-card-link .progress-track").first.click()

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


if __name__ == "__main__":
    unittest.main()
