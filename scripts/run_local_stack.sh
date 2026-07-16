#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

cleanup() {
	docker compose --env-file local-supabase.env down 2>/dev/null || true
	supabase stop 2>/dev/null || true
}

run_with_local_env() {
	env \
		-u SUPABASE_URL \
		-u SUPABASE_PUBLISHABLE_KEY \
		-u SUPABASE_ANON_KEY \
		-u SUPABASE_SERVICE_ROLE_KEY \
		-u SHELFPATH_LOCAL_AUTH_EMAIL \
		-u SHELFPATH_LOCAL_AUTH_PASSWORD \
		-u SHELFPATH_STORAGE \
		PYTHONPATH=. \
		uv run --env-file local-supabase.env "$@"
}

if [ "${1:-}" = "--reset" ]; then
	reset_catalogue=true
elif [ "$#" -eq 0 ]; then
	reset_catalogue=false
else
	echo "Usage: $0 [--reset]" >&2
	exit 2
fi

trap cleanup EXIT INT TERM

supabase start
PYTHONPATH=. uv run python scripts/write_local_supabase_env.py

if [ "$reset_catalogue" = true ]; then
	supabase db reset
	PYTHONPATH=. uv run python scripts/write_local_supabase_env.py
fi

run_with_local_env python scripts/seed_local_supabase.py

if [ "$reset_catalogue" = true ]; then
	run_with_local_env python scripts/import_catalogue_to_supabase.py
fi

docker compose --env-file local-supabase.env up --build
