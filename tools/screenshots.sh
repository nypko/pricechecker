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
if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then echo "port $PORT is already in use (set PORT=...)" >&2; exit 1; fi
.venv/bin/python -m pricechecker.serve "$PORT" >/dev/null 2>&1 &
SRV=$!
trap 'kill $SRV 2>/dev/null || true' EXIT
up=0
for _ in $(seq 50); do
  if curl -sf "http://127.0.0.1:$PORT/" >/dev/null; then up=1; break; fi
  sleep 0.2
done
if [ "$up" != 1 ] || ! kill -0 "$SRV" 2>/dev/null; then echo "server did not start" >&2; exit 1; fi

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
      png="$OUT/$name-${size%%x*}-$mode.png"
      rm -f "$png"
      "$CHROME" "${flags[@]}" --screenshot="$png" "http://127.0.0.1:$PORT${PAGES[$name]}" >/dev/null 2>&1 || true
      if [ ! -s "$png" ]; then echo "screenshot failed: $png" >&2; exit 1; fi
      n=$((n+1))
    done
  done
done
echo "$n screenshots in $OUT"
