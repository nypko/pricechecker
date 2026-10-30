#!/usr/bin/env bash
# Screenshots of the main page types, light and dark, phone and desktop width.
# Usage: tools/screenshots.sh [outdir] [store]   (build first: python -m pricechecker.run --build-only --offline)
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-${TMPDIR:-/tmp}/doorprice-shots}"
STORE="${2:-giztop}"
PORT="${PORT:-8791}"
CHROME="${CHROME:-chromium}"
PHONE=oppo-find-x9-ultra
mkdir -p "$OUT"
.venv/bin/python -m pricechecker.serve "$PORT" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
for _ in $(seq 50); do curl -sf "http://127.0.0.1:$PORT/" >/dev/null && break; sleep 0.2; done

declare -A PAGES=(
  [home]="/" [phone]="/phones/$PHONE" [specs]="/phones/$PHONE/specs" [drops]="/drops"
  [compare]="/compare#$PHONE,oneplus-16,google-pixel-11-pro" [history]="/history/$PHONE"
  [store]="/stores/$STORE" [404]="/404"
)
n=0
for name in "${!PAGES[@]}"; do
  for size in 390x2400 1280x1600; do
    for mode in light dark; do
      flags=(--headless=new --disable-gpu --hide-scrollbars --window-size="${size/x/,}" --virtual-time-budget=4000)
      [ "$mode" = dark ] && flags+=(--force-dark-mode --blink-settings=preferredColorScheme=0)
      "$CHROME" "${flags[@]}" --screenshot="$OUT/$name-${size%%x*}-$mode.png" "http://127.0.0.1:$PORT${PAGES[$name]}" >/dev/null 2>&1
      n=$((n+1))
    done
  done
done
echo "$n screenshots in $OUT"
