#!/usr/bin/env bash
set -euo pipefail

PROJECT_REF="pkrxfruhnjsifclnhjyc"

"$(dirname "$0")/require_supabase_cli.sh"

supabase link --project-ref "$PROJECT_REF"
