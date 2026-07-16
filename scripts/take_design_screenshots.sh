#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SHELFPATH_SCREENSHOT_URL:-http://127.0.0.1:8731}"
OUTPUT_DIR="${SHELFPATH_SCREENSHOT_DIR:-screenshots/playwright/latest}"

mkdir -p "$OUTPUT_DIR"

curl --fail --silent --show-error --output /dev/null "$BASE_URL/login?next=/" || {
	printf 'Shelfpath is not reachable at %s. Start it with `just local-run` or `just run`.\n' "$BASE_URL" >&2
	exit 1
}

playwright-cli open "$BASE_URL/login?next=/"
playwright-cli resize 390 844
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/01-home-mobile.png"
playwright-cli goto "$BASE_URL/shop"
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/02-shop-mobile.png"
playwright-cli goto "$BASE_URL/shop?q=The%20Colour%20of%20Magic"
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/06-shop-search-mobile.png"
playwright-cli goto "$BASE_URL/series/discworld"
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/03-discworld-mobile.png"
playwright-cli resize 1280 900
playwright-cli goto "$BASE_URL/"
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/04-home-desktop.png"
playwright-cli goto "$BASE_URL/series/discworld"
playwright-cli run-code "async page => page.waitForTimeout(750)"
playwright-cli screenshot --filename="$OUTPUT_DIR/05-discworld-desktop.png"
playwright-cli close

printf 'Saved Shelfpath design screenshots to %s\n' "$OUTPUT_DIR"
