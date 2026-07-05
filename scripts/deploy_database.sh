#!/usr/bin/env bash
set -euo pipefail

PROJECT_REF="pkrxfruhnjsifclnhjyc"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$SCRIPT_DIR/require_supabase_cli.sh"
cd "$PROJECT_DIR"

if [ ! -f "supabase/.temp/project-ref" ] || [ "$(cat supabase/.temp/project-ref 2>/dev/null || true)" != "$PROJECT_REF" ]; then
	if [ -n "${SUPABASE_DB_PASSWORD:-}" ]; then
		supabase link --project-ref "$PROJECT_REF" --password "$SUPABASE_DB_PASSWORD"
	else
		supabase link --project-ref "$PROJECT_REF"
	fi
fi

if [ -n "${SUPABASE_DB_PASSWORD:-}" ]; then
	supabase db push --linked --password "$SUPABASE_DB_PASSWORD"
else
	supabase db push --linked
fi
