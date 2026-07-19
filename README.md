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
just run
```

Open <http://127.0.0.1:8731/>.

This project hardcodes port `8731` in the local `just run` task and Supabase local redirect configuration to avoid common defaults such as `8000` and `8080`.

For local Supabase-backed testing without touching live data or waiting for magic-link email, Docker Desktop must be running. Start the entire local stack with one command:

```sh
just local-run
```

This starts Supabase, joins the Shelfpath Compose service to Supabase’s Docker network, and runs the app in the foreground at <http://127.0.0.1:8731/>. It watches the checkout for changes and initially logs in immediately through `/login` using the local test user. Signing out leaves you on the sign-in page, where **Sign in as local test user** lets you test the complete local sign-out/sign-in flow without email. `Ctrl-C` stops both the app and local Supabase stack.

For a completely fresh local database with current migrations, catalogue data, and local test user, run instead:

```sh
just local-reset-and-run
```

The sandbox data persists between normal `just local-run` sessions. Run Docker-backed browser end-to-end tests against a clean local Supabase database with:

```sh
just local-e2e
```

This starts the local stack, applies migrations, imports the catalogue, allows the local test user to access AI suggestions, runs the Playwright test container from `tests/compose.yaml`, and tears the stack down. The normal local app uses the separate root `compose.yaml`, so test containers and networks cannot be reused accidentally by interactive development.

If a terminal is interrupted before cleanup, run:

```sh
just local-run-stop
```

The Supabase CLI owns its official local service containers. Both Compose setups share their `supabase_network_shelfpath` network and talk to the local Kong API by container name: root `compose.yaml` runs interactive development, while `tests/compose.yaml` runs the isolated browser-test app and runner. No app traffic goes to live Supabase.

The local sandbox is a separate database from live Supabase, so random clicking and state changes cannot affect production data. The first `supabase start` may need internet access to download Docker images; after that it can run offline while the images and Docker volume remain on the machine. Run `just local-covers-fetch` while online to populate local Open Library cover IDs and cache cover images for offline design checks.

For hosted Supabase-backed testing without magic-link email, you can set these in `.env` instead:

```sh
SHELFPATH_LOCAL_AUTH_EMAIL=you@example.com
SUPABASE_SERVICE_ROLE_KEY=<secret key>
```

With `SHELFPATH_DEBUG=true`, visiting `/login` initially signs in as that existing Supabase user and redirects immediately. After signing out, the sign-in page offers **Sign in as local test user** so you can test the local sign-in flow without email. This bypass is deliberately local/debug-only and requires the service-role key; do not configure it in Fly.io.

## Sharing lists

List owners open **Lists**, choose **Manage people**, then enter an email address and choose **Can update** or **View only**. Shelfpath emails a signed, seven-day invitation link. The recipient opens that link and signs in with the invited email address; only then does Shelfpath grant access and select the shared list. Owners can change an active member’s access or remove them. Stateless invitation links cannot be individually cancelled or tracked before acceptance.

Sending invitations uses the Resend API and requires `RESEND_API_KEY` plus `SHELFPATH_INVITATION_TOKEN_SECRET`. Local Docker stacks use a Resend-compatible test stub; production requires `RESEND_API_KEY`, `SHELFPATH_MAIL_FROM`, `SHELFPATH_PUBLIC_URL`, `SHELFPATH_INVITATION_TOKEN_SECRET`, and `SUPABASE_SERVICE_ROLE_KEY`. These credentials belong only in Fly.io secrets, never in the repository.

## Fly.io deployment

`fly.toml` is the committed production configuration. The production container listens on port 8080 and Fly checks `GET /health`. Deploy manually with `just fly-deploy`; GitHub deploys `main` automatically through `.github/workflows/fly.yml`.

Set these Fly secrets before the first deploy:

```text
SHELFPATH_SESSION_SECRET
SUPABASE_PUBLISHABLE_KEY
OPENAI_API_KEY
RESEND_API_KEY
SHELFPATH_INVITATION_TOKEN_SECRET
SUPABASE_SERVICE_ROLE_KEY
```

`fly.toml` holds non-secret production settings, including the Supabase URL, public Shelfpath URL, and mail sender. Do not add secrets to it. Configure `FLY_API_TOKEN` as a GitHub Actions repository secret for automated deploys.

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

Fetch Open Library cover IDs for books that do not have one yet and cache the corresponding cover images locally with:

```sh
just covers-fetch
```

If the IDs are already populated and you only need to refresh the gitignored local image cache, run:

```sh
just covers-cache
```

Local Supabase has equivalent commands:

```sh
just local-covers-fetch
just local-covers-cache
```

Cached images live under gitignored `static/covers/` and are served from `/covers/`. Shelfpath falls back to Open Library when a cached image is not present.

`just catalogue-import`, `just covers-fetch`, and hosted local test auth require `SUPABASE_SERVICE_ROLE_KEY` in your local `.env` or shell. Do not commit it. The app itself uses the user's Supabase access token for normal runtime database reads/writes, so row-level security policies apply to list and book-state access outside service-role fallback auth. The local Supabase sandbox stores its own generated local-only service key in gitignored `local-supabase.env`.

To apply both database migrations and catalogue import locally:

```sh
just supabase-deploy
```

To allow a trusted user to use AI-assisted series suggestions:

```sh
just ai-allow user@example.com
```

`just ai-allow` requires `SUPABASE_SERVICE_ROLE_KEY` in your local `.env` or shell.

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
    wanted: true
  example-series/second-book:
    owned: false
    read: true
    wanted: true
```

`source` records provenance for future review. It is optional but recommended for real series data.

`read: true` and `owned: false` is valid: you may have read a book and given it away. `wanted` is also independent; missing/hunting books are derived from `wanted: true` and `owned: false`. In the UI, newly checking OWN or READ clears WANT as a helpful default; you can turn WANT back on deliberately.

## Deployment

`render.yaml` defines a Render web service for the Starlette app. Render deployment should be connected to the repository once, then normal app changes deploy from git. Configure these environment variables in Render:

```text
SHELFPATH_STORAGE=supabase
SHELFPATH_DEBUG=false
SHELFPATH_SESSION_SECRET=<generated secret>
SUPABASE_URL=https://pkrxfruhnjsifclnhjyc.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable key>
OPENAI_API_KEY=<OpenAI API key for AI-assisted series suggestions>
OPENAI_MODEL=gpt-4.1-mini
```

In Supabase Auth URL configuration, add the deployed Render URL and later `https://shelfpath.app` as allowed redirect URLs, including `/auth/callback`. This is one-time provider setup, not a per-change step.

## Views

- `/health` is an unauthenticated container health endpoint.
- `/login` signs in with Supabase magic-link auth.
- `/lists` chooses the active collecting list and lets owners email signed seven-day invitations with editor or viewer access. The recipient must open the link while signed in as the invited email address before access is granted.
- `/suggest` lets allow-listed logged-in users ask OpenAI to investigate a new ordered series, review the proposed books and provenance, then approve or reject the proposal.
- Book rows show cached Open Library covers when `books.openlibrary_cover_id` is populated and the image has been downloaded to `static/covers/`, fall back to Open Library when uncached, and show a striped placeholder otherwise.
- `/` lists series and progress.
- `/series/{series_id}` shows a series in order with working All, Wanted, and Owned filters plus wanted/owned/read controls.
- `/shop` shows wanted books that are not currently owned when empty. Searching a title returns fuzzy all-series matches with a verdict-first Wanted · buy it or Owned · skip card.

## Manual check

After changing the app, check:

1. The homepage loads.
2. A series page loads.
3. Status-chip changes save automatically; newly checking OWN or READ clears WANT, and explicitly re-enabling WANT remains possible.
4. Series All, Wanted, and Owned filters show the intended rows.
5. `/shop` omits owned books when browsing, and a searched owned title returns an Owned · skip verdict.
6. A searched wanted title returns a Wanted · buy it verdict.
7. Read-but-not-owned books still appear in `/shop`.
8. `/lists` shows the current list and allows owners to share Supabase-backed lists.
9. `/suggest` shows a friendly access message for users who are not allow-listed.
10. Allow-listed users can generate, reject, and approve AI-assisted series proposals.
11. Series and shop rows render Open Library covers when available and placeholders otherwise.
12. Broken YAML produces a clear traceback in development.
