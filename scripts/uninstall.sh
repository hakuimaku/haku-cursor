#!/usr/bin/env sh
# Remove Haku themes from ~/.local/share/icons.  Usage: scripts/uninstall.sh [all|blue|Haku-Tokyo]
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
dest=${XDG_DATA_HOME:-$HOME/.local/share}/icons
arg=${1:-all}

remove() {
    if [ -d "$dest/$1" ] && [ -f "$dest/$1/index.theme" ]; then
        rm -rf "${dest:?}/$1"
        echo "removed $dest/$1"
    fi
}

if [ "$arg" = "all" ]; then
    for d in "$dest"/Haku-*/; do
        [ -d "$d" ] && remove "$(basename "$d")"
    done
else
    first=$(printf '%s' "$arg" | cut -c1 | tr '[:lower:]' '[:upper:]')
    rest=$(printf '%s' "$arg" | cut -c2-)
    case "$arg" in Haku-*) remove "$arg" ;; *) remove "Haku-$first$rest" ;; esac
fi
