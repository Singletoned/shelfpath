# Shelfpath

Shelfpath is a checklist for ordered book series and shared collecting lists. It helps answer two questions while browsing second-hand book shops:

- Do I currently own this book?
- Have I already read it?

The app is file-backed for now. Real book data and personal state live in the separate `data/` repository rather than in this app repository.

The intended public app/domain name is `shelfpath.app`.

## Setup

Install dependencies:

```sh
uv sync
```

Create private local data from the committed example:

```sh
cp -R data.example data
```

Edit files under `data/` for your real series and state. The `data/` directory is gitignored by this app repository because it is managed as its own git repository.

Run the app:

```sh
uv run uvicorn app:app --reload --port 8731
```

Open <http://127.0.0.1:8731/>.

This project uses port `8731` for local development to avoid common defaults such as `8000` and `8080`.

## Data files

Series live in `data/series/*.yaml`:

```yaml
id: example-series
title: Example Series
author: Example Author
order: publication
source:
  name: Example Source
  url: https://example.invalid/example-series
  accessed: 2026-06-23
  notes: Example provenance for the ordered list.
books:
  - id: first-book
    title: First Book
    position: 1
  - id: second-book
    title: Second Book
    position: 2
```

Personal state lives in `data/state.yaml`:

```yaml
books:
  example-series/first-book:
    owned: true
    read: true
  example-series/second-book:
    owned: false
    read: true
```

`source` records provenance for future review. It is optional but recommended for real series data.

`read: true` and `owned: false` is valid: you may have read a book and given it away.

## Views

- `/` lists series and progress.
- `/series/{series_id}` shows a series in order with owned/read controls.
- `/shop` shows books that are not currently owned, grouped by series.

## Manual check

After changing the app, check:

1. The homepage loads.
2. A series page loads.
3. Owned/read checkboxes save and persist after refresh.
4. `/shop` omits owned books.
5. Read-but-not-owned books still appear in `/shop`.
6. Broken YAML produces a clear traceback in development.
