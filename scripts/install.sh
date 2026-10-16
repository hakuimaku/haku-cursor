#!/usr/bin/env sh
# Install built themes into ~/.local/share/icons (no root needed).
#   scripts/install.sh            install every theme found in dist/
#   scripts/install.sh blue       palette key (-> Haku-Blue)
#   scripts/install.sh Haku-Tokyo exact theme directory name in dist/
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
dest=${XDG_DATA_HOME:-$HOME/.local/share}/icons
arg=${1:-all}

resolve() {  # palette key or theme name -> directory name inside dist/
    if [ -d "$root/dist/$1" ]; then printf '%s\n' "$1"; return; fi
    first=$(printf '%s' "$1" | cut -c1 | tr '[:lower:]' '[:upper:]')
    rest=$(printf '%s' "$1" | cut -c2-)
    printf 'Haku-%s%s\n' "$first" "$rest"
}

if [ "$arg" = "all" ]; then
    set --
    for d in "$root"/dist/*/; do
        [ -d "${d}cursors" ] && set -- "$@" "$(basename "$d")"
    done
    [ "$#" -gt 0 ] || { echo "nothing built yet: run 'make' first" >&2; exit 1; }
else
    set -- "$(resolve "$arg")"
fi

mkdir -p "$dest"
for name in "$@"; do
    src="$root/dist/$name"
    [ -d "$src/cursors" ] || { echo "error: $src not built (run 'make ${arg}')" >&2; exit 1; }
    rm -rf "${dest:?}/$name"
    cp -a "$src" "$dest/$name"          # -a keeps the alias symlinks as symlinks
    echo "installed $name -> $dest/$name"
done

cat <<EOF

Activate (pick one):
  gsettings set org.gnome.desktop.interface cursor-theme '$1'
  XCURSOR_THEME=$1 XCURSOR_SIZE=24   (environment; see README for compositors)
EOF
