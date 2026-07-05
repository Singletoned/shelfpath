# Shelfpath

Shelfpath is a checklist for ordered book series and shared collecting lists. It helps answer two questions while browsing second-hand book shops:

- Do I currently own this book?
- Have I already read it?

The app is moving to the deployed architecture: Supabase Auth for users, Supabase Postgres for shared lists and owned/read state, and this Starlette app for the web UI. The separate `data/` repository remains the import/source-data workspace for catalogue YAML.

The intended public app/domain name is `shelfpath.app`.

## Setup

Install dependencies:

```sh
uv sync
```

Copy the environment template:

```sh
cp .env.example .env
```

Set a random `SHELFPATH_SESSION_SECRET` in `.env`. For Supabase-backed local development, set:

```sh
SHELFPATH_STORAGE=supabase
SUPABASE_URL=https://pkrxfruhnjsifclnhjyc.supabase.co
SUPABASE_PUBLISHABLE_KEY=...
```

For file-backed development or tests against local YAML, set:

```sh
SHELFPATH_STORAGE=file
```

Run the app:

```sh
uv run --env-file .env uvicorn app:app --reload --port 8731
```

Open <http://127.0.0.1:8731/>.

This project uses port `8731` for local development to avoid common defaults such as `8000` and `8080`.

## Supabase setup

Supabase schema changes are managed from this repository. Do not paste migrations into the dashboard for normal development. On GitHub, `.github/workflows/supabase.yml` pushes migrations automatically when `supabase/**` changes on `main`, once the required repository secrets are configured.

Install and authenticate the Supabase CLI once:

```sh
brew install supabase/tap/supabase
supabase login
```

Link this checkout to the Shelfpath Supabase project once:

```sh
just supabase-link
```

Apply database migrations with:

```sh
just db-push
```

Import catalogue data from the separate `data/` repository with:

```sh
just catalogue-import
```

`just catalogue-import` requires `SUPABASE_SERVICE_ROLE_KEY` in your local `.env` or shell. Do not commit it. The app itself uses the user's Supabase access token for normal runtime database reads/writes, so row-level security policies apply to list and book-state access.

To apply both database migrations and catalogue import locally:

```sh
just supabase-deploy
```

For automated GitHub migration deploys, configure repository secrets:

```text
SUPABASE_ACCESS_TOKEN
SUPABASE_DB_PASSWORD
```

`SUPABASE_ACCESS_TOKEN` comes from your Supabase account access tokens. `SUPABASE_DB_PASSWORD` is the database password for the Supabase project. Catalogue import is not part of this GitHub workflow because the catalogue YAML lives in the separate private `data/` repository.

## Data files

Catalogue source/import data lives in the separate `data/` repository. Series YAML files live in `data/series/*.yaml`:

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

Legacy file-backed personal state lives in `data/state.yaml`:

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

## Deployment

`render.yaml` defines a Render web service for the Starlette app. Render deployment should be connected to the repository once, then normal app changes deploy from git. Configure these environment variables in Render:

```text
SHELFPATH_STORAGE=supabase
SHELFPATH_DEBUG=false
SHELFPATH_SESSION_SECRET=<generated secret>
SUPABASE_URL=https://pkrxfruhnjsifclnhjyc.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable key>
```

In Supabase Auth URL configuration, add the deployed Render URL and later `https://shelfpath.app` as allowed redirect URLs, including `/auth/callback`. This is one-time provider setup, not a per-change step.

## Views

- `/login` signs in with Supabase magic-link auth.
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
