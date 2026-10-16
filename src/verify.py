#!/usr/bin/env python3
"""Sanity-check built themes: required names, XCursor structure, hotspots, animation, symlinks.

    python src/verify.py                 # every theme in dist/
    python src/verify.py dist/Haku-Blue  # one theme
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import xcursor
from cursors import ALIASES, CURSORS
from geometry import CANVAS

ROOT = Path(__file__).resolve().parent.parent

# Every name requested in the project brief (real asset or alias).
REQUIRED = """
default arrow left_ptr  pointer hand hand2  text xterm ibeam vertical-text  crosshair cross cell
move all-scroll fleur  n-resize s-resize e-resize w-resize  ne-resize nw-resize se-resize sw-resize
ns-resize ew-resize nesw-resize nwse-resize  grab grabbing dnd-move dnd-copy dnd-link
not-allowed forbidden no-drop help context-menu  wait watch progress left_ptr_watch  zoom-in zoom-out
""".split()


def expected_hotspot(name: str, size: int) -> tuple[int, int]:
    hx, hy = CURSORS[name].hotspot
    k = size / CANVAS
    return min(size - 1, math.floor(hx * k)), min(size - 1, math.floor(hy * k))


def verify_theme(theme_dir: Path) -> list[str]:
    errors: list[str] = []
    cursors_dir = theme_dir / "cursors"
    if not (theme_dir / "index.theme").is_file():
        errors.append("missing index.theme")
    for name in REQUIRED:
        if not (cursors_dir / name).exists():
            errors.append(f"required cursor name missing: {name}")

    sizes_seen: set[tuple[int, ...]] = set()
    for name, spec in CURSORS.items():
        path = cursors_dir / name
        if path.is_symlink() or not path.is_file():
            errors.append(f"{name}: not a regular file")
            continue
        try:
            frames = xcursor.read(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: unreadable ({exc})")
            continue
        sizes = tuple(sorted({f.size for f in frames}))
        sizes_seen.add(sizes)
        for size in sizes:
            of_size = [f for f in frames if f.size == size]
            if len(of_size) != spec.frames:
                errors.append(f"{name}@{size}: {len(of_size)} frames, expected {spec.frames}")
            for f in of_size:
                if (f.width, f.height) != (size, size):
                    errors.append(f"{name}@{size}: image is {f.width}x{f.height}")
                if (f.xhot, f.yhot) != expected_hotspot(name, size):
                    errors.append(f"{name}@{size}: hotspot {(f.xhot, f.yhot)} != {expected_hotspot(name, size)}")
                if spec.animated and f.delay != spec.delay_ms:
                    errors.append(f"{name}@{size}: delay {f.delay} != {spec.delay_ms}")
                if not any(f.argb[3::4]):
                    errors.append(f"{name}@{size}: fully transparent frame")
                # premultiplied data must satisfy colour <= alpha
                if any(max(f.argb[i], f.argb[i + 1], f.argb[i + 2]) > f.argb[i + 3] for i in range(0, len(f.argb), 4)):
                    errors.append(f"{name}@{size}: pixels are not premultiplied")

    if len(sizes_seen) > 1:
        errors.append(f"inconsistent size sets between cursors: {sorted(sizes_seen)}")

    for alias, target in ALIASES.items():
        link = cursors_dir / alias
        if not link.is_symlink():
            errors.append(f"alias {alias}: not a symlink")
        elif link.readlink() != Path(target):
            errors.append(f"alias {alias}: points to {link.readlink()}, expected {target}")
        elif not (cursors_dir / target).is_file():
            errors.append(f"alias {alias}: dangling")

    known = set(CURSORS) | set(ALIASES)
    for entry in cursors_dir.iterdir():
        if entry.name not in known:
            errors.append(f"unexpected file in cursors/: {entry.name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("themes", nargs="*", type=Path, help="theme directories (default: all in dist/)")
    args = ap.parse_args(argv)
    themes = args.themes or sorted(p for p in (ROOT / "dist").glob("*") if (p / "cursors").is_dir())
    if not themes:
        print("no built themes found; run `make` first", file=sys.stderr)
        return 2
    failed = 0
    for theme in themes:
        errors = verify_theme(theme)
        status = "OK  " if not errors else "FAIL"
        print(f"{status} {theme.name}" + (f" ({len(errors)} problems)" if errors else ""))
        for e in errors[:20]:
            print(f"     - {e}")
        failed += bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
