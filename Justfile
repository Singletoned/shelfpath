set dotenv-load := true

check:
    uv lock
    ruff format .
    ruff check . --fix
    taidy .
    python -m unittest discover -s tests

supabase-link:
    ./scripts/link_supabase_project.sh

db-push:
    ./scripts/deploy_database.sh

catalogue-import:
    PYTHONPATH=. uv run --env-file .env python scripts/import_catalogue_to_supabase.py

supabase-deploy: db-push catalogue-import
