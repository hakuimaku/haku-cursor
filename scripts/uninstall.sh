#!/usr/bin/env sh
# Remove Haku themes from ~/.icons/.
#   scripts/uninstall.sh              Haku-Dark and Haku-Light only
#   scripts/uninstall.sh dark|light   only the default dark or light theme
#   scripts/uninstall.sh all          every Haku-* theme
#   scripts/uninstall.sh blue         Haku-Blue and Haku-Blue-Light
#   scripts/uninstall.sh blue-light   only Haku-Blue-Light
set -eu
dest=$HOME/.icons
arg=${1:-default}

cap() {
    first=$(printf '%s' "$1" | cut -c1 | tr '[:lower:]' '[:upper:]')
    rest=$(printf '%s' "$1" | cut -c2-)
    printf '%s%s' "$first" "$rest"
}

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
    case "$arg" in
        default) remove "Haku-Dark"; remove "Haku-Light" ;;
        dark)    remove "Haku-Dark" ;;
        light)   remove "Haku-Light" ;;
        Haku-*)  remove "$arg" ;;
        *-light) remove "Haku-$(cap "${arg%-light}")-Light" ;;
        *)       remove "Haku-$(cap "$arg")"; remove "Haku-$(cap "$arg")-Light" ;;
    esac
fi
