#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

cleanup() {
	docker compose --env-file local-supabase.env --profile e2e down 2>/dev/null || true
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

reset_catalogue=false
run_e2e=false
for argument in "$@"; do
	case "$argument" in
	--reset) reset_catalogue=true ;;
	--e2e) run_e2e=true ;;
	*)
		echo "Usage: $0 [--reset] [--e2e]" >&2
		exit 2
		;;
	esac
done

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

if [ "$run_e2e" = true ]; then
	run_with_local_env python scripts/allow_ai_suggestion_user.py local@shelfpath.test
	docker compose --env-file local-supabase.env --profile e2e up --build \
		--abort-on-container-exit --exit-code-from e2e e2e
else
	docker compose --env-file local-supabase.env up --build
fi
