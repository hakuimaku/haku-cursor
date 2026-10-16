#!/usr/bin/env sh
# Install built themes into ~/.icons/ (no root needed).
#   scripts/install.sh               Haku-Dark and Haku-Light only
#   scripts/install.sh dark|light    only the default dark or light theme
#   scripts/install.sh all           every theme found in dist/
#   scripts/install.sh blue          Haku-Blue and Haku-Blue-Light (whichever are built)
#   scripts/install.sh blue-light    only Haku-Blue-Light
#   scripts/install.sh Haku-Tokyo    exact theme directory name in dist/
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
dest=$HOME/.icons
arg=${1:-default}

cap() {  # blue -> Blue
    first=$(printf '%s' "$1" | cut -c1 | tr '[:lower:]' '[:upper:]')
    rest=$(printf '%s' "$1" | cut -c2-)
    printf '%s%s' "$first" "$rest"
}

if [ "$arg" = "all" ]; then
    names=""
    for d in "$root"/dist/*/; do
        [ -d "${d}cursors" ] && names="$names $(basename "$d")"
    done
elif [ -d "$root/dist/$arg" ]; then
    names=$arg
else
    case "$arg" in
        default) names="Haku-Dark Haku-Light" ;;
        dark)    names="Haku-Dark" ;;
        light)   names="Haku-Light" ;;
        *-light) names="Haku-$(cap "${arg%-light}")-Light" ;;
        *)       names="Haku-$(cap "$arg") Haku-$(cap "$arg")-Light" ;;
    esac
fi

mkdir -p "$dest"
installed=""
for name in $names; do
    src="$root/dist/$name"
    [ -d "$src/cursors" ] || continue
    rm -rf "${dest:?}/$name"
    cp -a "$src" "$dest/$name"          # -a keeps the alias symlinks as symlinks
    echo "installed $name -> $dest/$name"
    installed="${installed:-$name}"
done
[ -n "$installed" ] || { echo "nothing to install for '$arg': run 'make' first" >&2; exit 1; }

cat <<EOF

Activate (pick one):
  gsettings set org.gnome.desktop.interface cursor-theme '$installed'
  XCURSOR_THEME=$installed XCURSOR_SIZE=24   (environment; see README for compositors)
EOF
