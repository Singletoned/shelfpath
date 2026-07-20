# Clerk and Postgres Migration Plan

## Decision

Shelfpath will replace Supabase Auth and Supabase PostgREST with Clerk authentication and direct Postgres access. Docker Compose runs Postgres for development and browser tests; Neon hosts production Postgres. This is a fresh start: catalogue YAML is imported into the new database, while existing Supabase accounts, lists, memberships, invitations, suggestions, and book state are intentionally not migrated.

## Target architecture

- Clerk owns identity and sign-in. The browser uses the Clerk publishable key; the Starlette server verifies Clerk session tokens before reading or writing user data.
- `clerk_user_id` is the stable user identifier in Postgres. Email is display/contact data only and is refreshed from Clerk when needed.
- The app accesses Postgres through a server-side `DATABASE_URL`; no database credential reaches the browser.
- Docker Compose owns the local app, Postgres, and Resend test stub as one lifecycle. Clerk development authentication still requires Clerk's hosted development service.
- Neon is the production database. Fly receives `DATABASE_URL`, Clerk production keys, and existing app secrets as Fly secrets.
- Committed SQL migrations under `db/migrations/` are applied by a repeatable repository command locally, in CI, and before production deployment.

## Migration phases

1. **Foundation**: add Postgres driver/migration runner, initial schema, Docker Postgres, Neon migration command, and catalogue import.
2. **Identity**: replace Supabase magic-link/session handling with Clerk sign-in/sign-up UI and verified Clerk sessions.
3. **Storage**: replace `SupabaseStore` with Postgres queries for catalogue, lists, memberships, book state, suggestions, and invitations.
4. **Workflows**: restore sharing, role enforcement, Clerk-bound invitation acceptance, AI allow-list/rate-limit/audit, and cover fetching against Postgres.
5. **Cutover**: move Fly secrets/configuration to Clerk and Neon, run the empty production schema plus catalogue import, remove Supabase deployment/CI/local-stack assets, and validate Docker E2E plus Fly health/auth flows.

## Acceptance criteria

- `just local-run` starts a disposable/local Docker Postgres and Shelfpath without contacting Supabase.
- A Clerk development user can sign in locally, create a list, update state, share a list, and use the approved AI workflow.
- `just db-migrate` is idempotent for both Docker Postgres and Neon.
- Production Shelfpath uses Clerk production on `shelfpath.app` and Neon only; no Supabase URL/key/service-role secret remains in deployed configuration.
- Fresh production catalogue import succeeds from the private `data/` repository, with no Supabase user/list/state migration.
