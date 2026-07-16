from __future__ import annotations

import re

AUTHOR_BIO_SUFFIX = re.compile(
    r",\s*(?:co-?author|author|editor|writer|journalist|broadcaster)\b.*$",
    flags=re.IGNORECASE,
)


def sanitize_book_author(author: str | None) -> str | None:
    """Keep author bylines; discard publisher biography appended to them."""
    if author is None:
        return None
    cleaned = AUTHOR_BIO_SUFFIX.sub("", author).strip()
    return cleaned or None
