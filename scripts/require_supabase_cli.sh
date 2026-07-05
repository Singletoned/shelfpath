#!/usr/bin/env bash
set -euo pipefail

if ! command -v supabase >/dev/null 2>&1; then
	cat >&2 <<'EOF'
The Supabase CLI is required.

Install it with one of:
  brew install supabase/tap/supabase
  npm install -g supabase

Then authenticate once with:
  supabase login
EOF
	exit 1
fi
