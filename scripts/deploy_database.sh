#!/usr/bin/env bash
set -euo pipefail

PROJECT_REF="pkrxfruhnjsifclnhjyc"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$SCRIPT_DIR/require_supabase_cli.sh"
cd "$PROJECT_DIR"

if [ ! -f "supabase/.temp/project-ref" ] || [ "$(cat supabase/.temp/project-ref 2>/dev/null || true)" != "$PROJECT_REF" ]; then
	supabase link --project-ref "$PROJECT_REF"
fi

supabase db push
