#!/usr/bin/env sh
# Delete every generated artifact (SVG, PNG, xcursorgen configs, finished themes, previews).
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
for dir in generated build dist; do
    find "$root/$dir" -mindepth 1 -not -name '.gitkeep' -delete 2>/dev/null || true
done
find "$root/src" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "cleaned generated/, build/, dist/"
