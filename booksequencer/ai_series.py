from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
MAX_PROMPT_LENGTH = 4000


@dataclass(frozen=True)
class SeriesProposal:
    series_id: str
    title: str
    author: str | None
    order: str
    source: dict[str, Any]
    books: list[dict[str, Any]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "title": self.title,
            "author": self.author,
            "order": self.order,
            "source": self.source,
            "books": self.books,
            "warnings": self.warnings,
        }


class OpenAISeriesInvestigator:
    def __init__(self, api_key: str | None, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def investigate(self, prompt: str) -> SeriesProposal:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for AI series suggestions.")
        normalized_prompt = _clean_prompt(prompt)
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "tools": [{"type": "web_search_preview"}],
                    "input": _build_prompt(normalized_prompt),
                },
            )
        if response.status_code >= 400:
            raise RuntimeError(f"OpenAI request failed: {response.status_code} {response.text}")
        payload = response.json()
        return parse_openai_response(payload)


class FakeSeriesInvestigator:
    def __init__(self, proposal: dict[str, Any] | None = None) -> None:
        self.proposal = proposal or {
            "series_id": "fake-series",
            "title": "Fake Series",
            "author": "Fake Author",
            "order": "publication",
            "source": {
                "name": "Fake Source",
                "url": "https://example.invalid/fake-series",
                "accessed": date.today().isoformat(),
                "notes": "Fake proposal for tests.",
            },
            "books": [
                {"id": "first-book", "title": "First Book", "author": "Fake Author", "position": 1}
            ],
            "warnings": [],
        }

    async def investigate(self, prompt: str) -> SeriesProposal:
        return validate_proposal(self.proposal)


def parse_openai_response(payload: dict[str, Any]) -> SeriesProposal:
    output_text = payload.get("output_text")
    if not isinstance(output_text, str) or not output_text.strip():
        output_text = _extract_output_text(payload)
    proposal = _parse_json_object(output_text)
    return validate_proposal(proposal)


def validate_proposal(proposal: dict[str, Any]) -> SeriesProposal:
    series_id = _required_string(proposal, "series_id")
    title = _required_string(proposal, "title")
    order = _required_string(proposal, "order")
    source = proposal.get("source")
    if not isinstance(source, dict):
        raise ValueError("AI proposal source must be an object.")
    books = proposal.get("books")
    if not isinstance(books, list) or not books:
        raise ValueError("AI proposal books must be a non-empty list.")
    normalized_books = [_normalize_book(book, index + 1) for index, book in enumerate(books)]
    warnings = proposal.get("warnings", [])
    if not isinstance(warnings, list) or not all(isinstance(warning, str) for warning in warnings):
        raise ValueError("AI proposal warnings must be a list of strings.")
    author = proposal.get("author")
    if author is not None and not isinstance(author, str):
        raise ValueError("AI proposal author must be a string or null.")
    return SeriesProposal(
        series_id=_slug(series_id),
        title=title,
        author=author,
        order=order,
        source=_normalize_source(source),
        books=normalized_books,
        warnings=warnings,
    )


def _clean_prompt(prompt: str) -> str:
    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise ValueError("Series suggestion prompt is required.")
    if len(normalized_prompt) > MAX_PROMPT_LENGTH:
        raise ValueError(
            f"Series suggestion prompt must be at most {MAX_PROMPT_LENGTH} characters."
        )
    return normalized_prompt


def _build_prompt(user_prompt: str) -> str:
    return f"""
Investigate this Shelfpath user request and produce one ordered sequence of books or
book-like objects.

User request:
{user_prompt}

Rules:
- Search the web for reliable sources.
- If the user did not specify an ordering, use publication order.
- If the user requested a particular ordering, use that ordering.
- Return only JSON. Do not use markdown.
- Include provenance for the sources you used.
- Include warnings when sources conflict or confidence is limited.
- Use stable lowercase kebab-case ids.
- Do not invent books that are not supported by your sources.

JSON shape:
{{
  "series_id": "lowercase-kebab-case-id",
  "title": "Series or collection title",
  "author": "Author, editor, publisher, Various, or null",
  "order": "publication|chronological|publisher|other short description",
  "source": {{
    "name": "Primary source name",
    "url": "https://source.example/path",
    "accessed": "{date.today().isoformat()}",
    "notes": "Primary and cross-check sources used, including URLs and any conflicts."
  }},
  "books": [
    {{"id": "book-id", "title": "Book title", "author": "Book author or null", "position": 1}}
  ],
  "warnings": ["Any source conflicts or uncertainty"]
}}
""".strip()


def _extract_output_text(payload: dict[str, Any]) -> str:
    parts = []
    for output in payload.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    if not parts:
        raise ValueError("OpenAI response did not include output text.")
    return "\n".join(parts)


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ValueError(f"OpenAI did not return valid proposal JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI proposal JSON must be an object.")
    return parsed


def _required_string(proposal: dict[str, Any], key: str) -> str:
    value = proposal.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"AI proposal {key} must be a non-empty string.")
    return value.strip()


def _normalize_book(book: Any, fallback_position: int) -> dict[str, Any]:
    if not isinstance(book, dict):
        raise ValueError("AI proposal book entries must be objects.")
    title = _required_string(book, "title")
    book_id = book.get("id")
    if not isinstance(book_id, str) or not book_id.strip():
        book_id = title
    position = book.get("position", fallback_position)
    if not isinstance(position, int):
        raise ValueError("AI proposal book position must be an integer.")
    author = book.get("author")
    if author is not None and not isinstance(author, str):
        raise ValueError("AI proposal book author must be a string or null.")
    return {"id": _slug(book_id), "title": title, "author": author, "position": position}


def _normalize_source(source: dict[str, Any]) -> dict[str, Any]:
    name = source.get("name")
    url = source.get("url")
    accessed = source.get("accessed", date.today().isoformat())
    notes = source.get("notes", "")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("AI proposal source.name must be a non-empty string.")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("AI proposal source.url must be a non-empty string.")
    if not isinstance(accessed, str) or not accessed.strip():
        raise ValueError("AI proposal source.accessed must be a non-empty string.")
    if not isinstance(notes, str):
        raise ValueError("AI proposal source.notes must be a string.")
    return {"name": name.strip(), "url": url.strip(), "accessed": accessed.strip(), "notes": notes}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("AI proposal id could not be normalized.")
    return slug
