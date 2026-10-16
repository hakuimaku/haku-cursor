#!/usr/bin/env sh
# Build default dark + light themes. Usage: scripts/build.sh [palette|all] [extra generate.py flags]
# Binaries are resolved through PATH only (works on NixOS).
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
py=${PYTHON:-python3}
command -v "$py" >/dev/null 2>&1 || { echo "error: $py not found in PATH" >&2; exit 1; }

if [ "$#" -eq 0 ]; then
    exec "$py" "$root/src/generate.py"
fi
if [ "$1" = "all" ]; then
    shift
    exec "$py" "$root/src/generate.py" --all "$@"
fi
case "$1" in
    -*) exec "$py" "$root/src/generate.py" "$@" ;;
    *)  palette=$1; shift; exec "$py" "$root/src/generate.py" --palette "$palette" "$@" ;;
esac
