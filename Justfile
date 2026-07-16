set dotenv-load

check:
    uv lock
    ruff format .
    ruff check . --fix
    taidy .
    python -m unittest discover -s tests

run:
    uv run --env-file .env uvicorn app:app --reload --host 127.0.0.1 --port 8731

local-supabase-start:
    supabase start
    PYTHONPATH=. uv run python scripts/write_local_supabase_env.py
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/seed_local_supabase.py

local-supabase-reset:
    supabase db reset
    PYTHONPATH=. uv run python scripts/write_local_supabase_env.py
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/seed_local_supabase.py
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/import_catalogue_to_supabase.py

local-supabase-stop:
    supabase stop

local-run:
    ./scripts/run_local_stack.sh

local-reset-and-run:
    ./scripts/run_local_stack.sh --reset

local-e2e:
    ./scripts/run_local_stack.sh --reset --e2e

local-run-stop:
    docker compose --env-file local-supabase.env --file tests/compose.yaml down
    docker compose --env-file local-supabase.env --file compose.yaml down
    supabase stop

local-covers-fetch:
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/fetch_openlibrary_covers.py
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/cache_openlibrary_covers.py

local-covers-cache:
    env -u SUPABASE_URL -u SUPABASE_PUBLISHABLE_KEY -u SUPABASE_ANON_KEY -u SUPABASE_SERVICE_ROLE_KEY -u SHELFPATH_LOCAL_AUTH_EMAIL -u SHELFPATH_LOCAL_AUTH_PASSWORD -u SHELFPATH_STORAGE PYTHONPATH=. uv run --env-file local-supabase.env python scripts/cache_openlibrary_covers.py

screenshots:
    ./scripts/take_design_screenshots.sh

supabase-link:
    ./scripts/link_supabase_project.sh

db-push:
    ./scripts/deploy_database.sh

catalogue-import:
    PYTHONPATH=. uv run --env-file .env python scripts/import_catalogue_to_supabase.py

covers-fetch:
    PYTHONPATH=. uv run --env-file .env python scripts/fetch_openlibrary_covers.py
    PYTHONPATH=. uv run --env-file .env python scripts/cache_openlibrary_covers.py

covers-cache:
    PYTHONPATH=. uv run --env-file .env python scripts/cache_openlibrary_covers.py

ai-allow email:
    PYTHONPATH=. uv run --env-file .env python scripts/allow_ai_suggestion_user.py {{ email }}

supabase-deploy: db-push catalogue-import
