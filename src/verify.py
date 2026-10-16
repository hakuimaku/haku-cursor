#!/usr/bin/env python3
"""Sanity-check built themes: required names, XCursor structure, hotspots, animation, symlinks.

    python src/verify.py                 # every theme in dist/
    python src/verify.py dist/Haku-Blue  # one theme
"""

from __future__ import annotations

import argparse
import json
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


COLOR_CHECK_SIZE = 32      # one size is enough to catch stray colours
COLOR_TOLERANCE = 16       # max RGB distance from the base-accent line (anti-aliasing blends)


def _hex_rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def off_palette_pixels(frame: xcursor.Frame, base: str, accent: str) -> int:
    """Count opaque-ish pixels whose colour is not a blend of base and accent."""
    b, a = _hex_rgb(base), _hex_rgb(accent)
    d = tuple(a[i] - b[i] for i in range(3))
    denom = sum(v * v for v in d) or 1
    px, bad = frame.argb, 0
    for i in range(0, len(px), 4):
        alpha = px[i + 3]
        if alpha < 160:
            continue
        c = (px[i + 2] * 255 // alpha, px[i + 1] * 255 // alpha, px[i] * 255 // alpha)
        u = max(0.0, min(1.0, sum((c[k] - b[k]) * d[k] for k in range(3)) / denom))
        if sum((c[k] - (b[k] + u * d[k])) ** 2 for k in range(3)) > COLOR_TOLERANCE ** 2:
            bad += 1
    return bad


def load_colors(theme_dir: Path) -> tuple[str, str] | None:
    info = ROOT / "build" / theme_dir.name / "theme.json"
    if not info.is_file():
        return None
    data = json.loads(info.read_text(encoding="utf-8"))
    return data["base"], data["accent"]


def verify_theme(theme_dir: Path) -> list[str]:
    errors: list[str] = []
    colors = load_colors(theme_dir)
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
        counts = {size: sum(1 for f in frames if f.size == size) for size in sizes}
        if len(set(counts.values())) > 1:
            errors.append(f"{name}: frame count differs between sizes {counts}")
        for size in sizes:
            of_size = [f for f in frames if f.size == size]
            if len(of_size) not in (1, spec.frames):      # 1 = built with --animations loading|none
                errors.append(f"{name}@{size}: {len(of_size)} frames, expected {spec.frames} (or 1)")
            for f in of_size:
                if (f.width, f.height) != (size, size):
                    errors.append(f"{name}@{size}: image is {f.width}x{f.height}")
                if (f.xhot, f.yhot) != expected_hotspot(name, size):
                    errors.append(f"{name}@{size}: hotspot {(f.xhot, f.yhot)} != {expected_hotspot(name, size)}")
                if len(of_size) > 1 and f.delay != spec.delay_ms:
                    errors.append(f"{name}@{size}: delay {f.delay} != {spec.delay_ms}")
                if colors and size == COLOR_CHECK_SIZE:
                    stray = off_palette_pixels(f, *colors)
                    if stray:
                        errors.append(f"{name}@{size}: {stray} pixels use a colour other than base/accent")
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

    if colors is None:
        print(f"     (no build/{theme_dir.name}/theme.json: two-colour check skipped)")
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
