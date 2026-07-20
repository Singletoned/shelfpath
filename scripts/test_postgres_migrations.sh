#!/usr/bin/env bash
set -euo pipefail

compose=(docker compose --file tests/postgres-migrations.compose.yaml)
trap '"${compose[@]}" down --volumes' EXIT
"${compose[@]}" up --build --abort-on-container-exit --exit-code-from migrate
