from __future__ import annotations

import unittest

from booksequencer.ai_series import parse_openai_response, validate_proposal


class AiSeriesTests(unittest.TestCase):
    def test_validate_proposal_normalizes_ids(self):
        proposal = validate_proposal(
            {
                "series_id": "Example Series!",
                "title": "Example Series",
                "author": "Example Author",
                "order": "publication",
                "source": {
                    "name": "Example",
                    "url": "https://example.invalid",
                    "accessed": "2026-07-11",
                    "notes": "Used as a test source.",
                },
                "books": [
                    {
                        "id": "First Book!",
                        "title": "First Book",
                        "author": "Example Author",
                        "position": 1,
                    }
                ],
                "warnings": [],
            }
        )

        self.assertEqual(proposal.series_id, "example-series")
        self.assertEqual(proposal.books[0]["id"], "first-book")

    def test_parse_openai_response_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            parse_openai_response({"output_text": "not json"})


if __name__ == "__main__":
    unittest.main()
