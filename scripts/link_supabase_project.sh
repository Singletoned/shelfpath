#!/usr/bin/env bash
set -euo pipefail

PROJECT_REF="pkrxfruhnjsifclnhjyc"

"$(dirname "$0")/require_supabase_cli.sh"

if [ -n "${SUPABASE_DB_PASSWORD:-}" ]; then
	supabase link --project-ref "$PROJECT_REF" --password "$SUPABASE_DB_PASSWORD"
else
	supabase link --project-ref "$PROJECT_REF"
fi
