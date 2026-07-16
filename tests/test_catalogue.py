from __future__ import annotations

import unittest

from booksequencer.catalogue import sanitize_book_author


class CatalogueTests(unittest.TestCase):
    def test_sanitize_book_author_removes_biographical_suffix(self):
        self.assertEqual(
            sanitize_book_author("Peter Clayton, co-author of The Bluffer's Guide to Jazz."),
            "Peter Clayton",
        )

    def test_sanitize_book_author_keeps_normal_byline(self):
        self.assertEqual(sanitize_book_author("Terry Pratchett"), "Terry Pratchett")
        self.assertIsNone(sanitize_book_author(None))


if __name__ == "__main__":
    unittest.main()
