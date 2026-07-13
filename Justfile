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
    PYTHONPATH=. uv run --env-file local-supabase.env python scripts/seed_local_supabase.py

local-supabase-reset:
    supabase db reset
    PYTHONPATH=. uv run python scripts/write_local_supabase_env.py
    PYTHONPATH=. uv run --env-file local-supabase.env python scripts/seed_local_supabase.py
    PYTHONPATH=. uv run --env-file local-supabase.env python scripts/import_catalogue_to_supabase.py

local-run:
    uv run --env-file local-supabase.env uvicorn app:app --reload --host 127.0.0.1 --port 8731

local-covers-fetch:
    PYTHONPATH=. uv run --env-file local-supabase.env python scripts/fetch_openlibrary_covers.py

supabase-link:
    ./scripts/link_supabase_project.sh

db-push:
    ./scripts/deploy_database.sh

catalogue-import:
    PYTHONPATH=. uv run --env-file .env python scripts/import_catalogue_to_supabase.py

covers-fetch:
    PYTHONPATH=. uv run --env-file .env python scripts/fetch_openlibrary_covers.py

ai-allow email:
    PYTHONPATH=. uv run --env-file .env python scripts/allow_ai_suggestion_user.py {{ email }}

supabase-deploy: db-push catalogue-import
