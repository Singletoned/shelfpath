#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

reset=false
for argument in "$@"; do
	case "$argument" in
	--reset) reset=true ;;
	*)
		echo "Usage: $0 [--reset]" >&2
		exit 2
		;;
	esac
done

compose() {
	docker compose --file compose.yaml "$@"
}

cleanup() {
	compose down 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ "$reset" = true ]; then
	compose down --volumes
fi

compose up --build
