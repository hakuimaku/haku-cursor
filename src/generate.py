#!/usr/bin/env python3
"""Haku Cursor generator: geometry (code) -> SVG -> PNG -> xcursorgen -> XCursor theme.

Examples
--------
    python src/generate.py --palette blue
    python src/generate.py --all
    python src/generate.py --accent "#7aa2f7" --name Haku-Tokyo
    python src/generate.py --preview
"""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import palettes
import raster
import xcursor
from cursors import ALIASES, CURSORS, CursorSpec
from geometry import CANVAS
from palettes import Theme
from preview import build_preview
from svg import Group, document, document_wh

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIZES = (24, 32, 48, 64, 96)
EXTENDED_SIZES = (16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96)


# --------------------------------------------------------------------------- #
# Renderers (SVG -> PNG).  Binaries are always resolved through PATH (NixOS friendly).
# --------------------------------------------------------------------------- #
@dataclass
class Renderer:
    name: str
    binary: str | None = None

    def render(self, scene: Group, svg_path: Path, size: int, png_path: Path) -> None:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        s = str(size)
        if self.name == "rsvg-convert":
            cmd = [self.binary, "-w", s, "-h", s, "-o", str(png_path), str(svg_path)]
        elif self.name == "resvg":
            cmd = [self.binary, "-w", s, "-h", s, str(svg_path), str(png_path)]
        elif self.name == "inkscape":
            cmd = [self.binary, str(svg_path), "--export-type=png", f"--export-filename={png_path}",
                   "-w", s, "-h", s]
        else:  # pillow: rasterise the same scene graph directly
            raster.render(scene, size, CANVAS).save(png_path)
            return
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def detect_renderer(preference: str = "auto") -> Renderer:
    order = ["rsvg-convert", "resvg", "inkscape"] if preference == "auto" else [preference]
    for name in order:
        if name == "pillow":
            break
        binary = shutil.which(name)
        if binary:
            return Renderer(name, binary)
        if preference != "auto":
            raise SystemExit(f"error: renderer {name!r} not found in PATH")
    if raster.available():
        print("note: no SVG renderer in PATH (rsvg-convert / resvg / inkscape); "
              "falling back to the built-in Pillow rasteriser", file=sys.stderr)
        return Renderer("pillow")
    raise SystemExit("error: no SVG renderer found. Install librsvg (rsvg-convert), resvg or inkscape "
                     "(NixOS: `nix-shell` with the provided shell.nix).")


# --------------------------------------------------------------------------- #
# Pipeline helpers
# --------------------------------------------------------------------------- #
def hotspot_px(spec: CursorSpec, size: int) -> tuple[int, int]:
    """Pixel containing the canvas-space hotspot at this size."""
    k = size / CANVAS
    return (min(size - 1, max(0, math.floor(spec.hotspot[0] * k))),
            min(size - 1, max(0, math.floor(spec.hotspot[1] * k))))


def frame_stem(spec: CursorSpec, index: int) -> str:
    return f"{spec.name}-{index:02d}" if spec.animated else spec.name


def write_conf(spec: CursorSpec, sizes: tuple[int, ...], conf_path: Path) -> None:
    """xcursorgen config: ``size xhot yhot file [delay]`` (frames grouped per size)."""
    lines = []
    for size in sizes:
        xh, yh = hotspot_px(spec, size)
        for i in range(spec.frames):
            line = f"{size} {xh} {yh} {frame_stem(spec, i)}-{size}.png"
            if spec.animated:
                line += f" {spec.delay_ms}"
            lines.append(line)
    conf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_builtin(spec: CursorSpec, sizes: tuple[int, ...], png_dir: Path, out: Path) -> None:
    from PIL import Image  # PNG decoding for the fallback writer

    frames = []
    for size in sizes:
        xh, yh = hotspot_px(spec, size)
        for i in range(spec.frames):
            with Image.open(png_dir / f"{frame_stem(spec, i)}-{size}.png") as im:
                im = im.convert("RGBA")
                argb = xcursor.premultiply_rgba(im.tobytes())
                frames.append(xcursor.Frame(size, im.width, im.height, xh, yh, spec.delay_ms if spec.animated else 0, argb))
    xcursor.write(out, frames)


def compile_cursor(spec: CursorSpec, sizes: tuple[int, ...], conf: Path, png_dir: Path, out: Path,
                   xcursorgen: str | None) -> None:
    if xcursorgen:
        subprocess.run([xcursorgen, "-p", str(png_dir), str(conf), str(out)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        compile_builtin(spec, sizes, png_dir, out)


def make_aliases(cursors_dir: Path) -> int:
    """Relative symlinks alias -> real cursor (never duplicates the binaries)."""
    for alias, target in ALIASES.items():
        link = cursors_dir / alias
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(target, link)
    return len(ALIASES)


def write_index_theme(theme: Theme, theme_dir: Path, inherits: str) -> None:
    (theme_dir / "index.theme").write_text(
        "[Icon Theme]\n"
        f"Name={theme.display_name}\n"
        f"Comment={theme.comment}\n"
        f"Inherits={inherits}\n", encoding="utf-8")


def _parallel(jobs: int, func, items) -> None:
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for _ in pool.map(func, items):
            pass


# --------------------------------------------------------------------------- #
# Theme build
# --------------------------------------------------------------------------- #
def build_theme(theme: Theme, sizes: tuple[int, ...], renderer: Renderer, xcursorgen: str | None,
                out_dir: Path, inherits: str, jobs: int) -> Path:
    gen_dir = ROOT / "generated" / theme.name
    conf_dir = ROOT / "build" / theme.name
    theme_dir = out_dir / theme.name
    for d in (gen_dir, conf_dir, theme_dir):
        shutil.rmtree(d, ignore_errors=True)
    svg_dir, png_dir, cursors_dir = gen_dir / "svg", gen_dir / "png", theme_dir / "cursors"
    for d in (svg_dir, png_dir, conf_dir, cursors_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1) geometry -> SVG (one vector file per frame, shared by every pixel size)
    render_jobs = []
    for spec in CURSORS.values():
        for i in range(spec.frames):
            scene = spec.draw(theme, i / spec.frames)
            svg_path = svg_dir / f"{frame_stem(spec, i)}.svg"
            svg_path.write_text(document(scene, CANVAS, title=spec.name), encoding="utf-8")
            render_jobs.append((scene, svg_path, i, spec))

    # 2) SVG -> PNG, re-rasterised from the vector at every size
    tasks = [(scene, svg, size, png_dir / f"{svg.stem}-{size}.png")
             for scene, svg, _i, _spec in render_jobs for size in sizes]
    _parallel(jobs, lambda t: renderer.render(t[0], t[1], t[2], t[3]), tasks)

    # 3) xcursorgen config + compile
    def compile_one(spec: CursorSpec) -> None:
        conf = conf_dir / f"{spec.name}.conf"
        write_conf(spec, sizes, conf)
        compile_cursor(spec, sizes, conf, png_dir, cursors_dir / spec.name, xcursorgen)

    _parallel(jobs, compile_one, list(CURSORS.values()))

    # 4) aliases + index.theme
    n_alias = make_aliases(cursors_dir)
    write_index_theme(theme, theme_dir, inherits)
    print(f"  {theme.name}: {len(CURSORS)} cursors, {n_alias} aliases, sizes {','.join(map(str, sizes))} -> {theme_dir}")
    return theme_dir


def build_preview_files(theme: Theme, renderer: Renderer, out_dir: Path, width_px: int = 1984) -> None:
    scene, w, h = build_preview(theme)
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path, png_path = out_dir / "preview.svg", out_dir / "preview.png"
    svg_path.write_text(document_wh(scene, w, h), encoding="utf-8")
    if renderer.name == "pillow":
        raster.render(scene, width_px, w, round(h * width_px / w), h).save(png_path)
    else:
        cmd = {"rsvg-convert": [renderer.binary, "-w", str(width_px), "-o", str(png_path), str(svg_path)],
               "resvg": [renderer.binary, "-w", str(width_px), str(svg_path), str(png_path)],
               "inkscape": [renderer.binary, str(svg_path), "--export-type=png",
                            f"--export-filename={png_path}", "-w", str(width_px)]}[renderer.name]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(f"  preview: {svg_path}  {png_path}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_sizes(text: str) -> tuple[int, ...]:
    if text == "default":
        return DEFAULT_SIZES
    if text == "extended":
        return EXTENDED_SIZES
    try:
        sizes = tuple(sorted({int(p) for p in text.split(",") if p.strip()}))
    except ValueError:
        raise argparse.ArgumentTypeError("sizes must be 'default', 'extended' or a comma list like 24,32,48")
    if not sizes or min(sizes) < 8:
        raise argparse.ArgumentTypeError("sizes must be integers >= 8")
    return sizes


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate Haku Cursor XCursor themes from code.")
    p.add_argument("--palette", "-p", nargs="+", metavar="NAME", help=f"preset(s): {', '.join(palettes.PALETTES)}")
    p.add_argument("--all", action="store_true", help="build every preset palette")
    p.add_argument("--name", help="theme name (custom variants), e.g. Haku-Tokyo")
    p.add_argument("--accent", help="custom accent colour, e.g. '#7aa2f7'")
    p.add_argument("--base", help="override base colour (default from config/palettes.json)")
    p.add_argument("--outline", help="override outline colour")
    p.add_argument("--sizes", type=parse_sizes, default=DEFAULT_SIZES,
                   help="'default' (24,32,48,64,96), 'extended', or a comma list")
    p.add_argument("--inherits", default="Adwaita", help="fallback theme written to index.theme")
    p.add_argument("--out-dir", type=Path, default=ROOT / "dist", help="where finished themes go (default: dist/)")
    p.add_argument("--renderer", default="auto", choices=["auto", "rsvg-convert", "resvg", "inkscape", "pillow"])
    p.add_argument("--xcursorgen", default="auto", choices=["auto", "xcursorgen", "builtin"],
                   help="use the xcursorgen binary from PATH or the built-in pure-Python writer")
    p.add_argument("--jobs", "-j", type=int, default=os.cpu_count() or 2)
    p.add_argument("--preview", action="store_true", help="only write generated/preview.svg + preview.png")
    p.add_argument("--list", action="store_true", help="list palettes and cursors, then exit")
    return p


def select_themes(args: argparse.Namespace) -> list[Theme]:
    custom = any((args.accent, args.base, args.outline))
    if args.all:
        if custom or args.name:
            raise SystemExit("error: --all cannot be combined with --accent/--base/--outline/--name")
        return palettes.all_preset_themes()
    keys = args.palette or ["blue"]
    if len(keys) > 1 and (custom or args.name):
        raise SystemExit("error: --name/--accent/--base/--outline need a single --palette")
    try:
        return [palettes.make_theme(k, name=args.name, accent=args.accent, base=args.base, outline=args.outline)
                for k in keys]
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"error: {exc}")


def resolve_xcursorgen(mode: str) -> str | None:
    if mode == "builtin":
        return None
    binary = shutil.which("xcursorgen")
    if binary or mode == "xcursorgen":
        if not binary:
            raise SystemExit("error: xcursorgen not found in PATH (NixOS: add `xcursorgen` / `xorg.xcursorgen`)")
        return binary
    if not raster.available():
        raise SystemExit("error: xcursorgen not found in PATH and Pillow is unavailable for the fallback writer")
    print("note: xcursorgen not found in PATH; using the built-in pure-Python XCursor writer", file=sys.stderr)
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        print("palettes:", ", ".join(f"{k}={v}" for k, v in palettes.PALETTES.items()))
        print("cursors :", ", ".join(CURSORS))
        print(f"aliases : {len(ALIASES)}")
        return 0
    themes = select_themes(args)
    renderer = detect_renderer(args.renderer)
    if args.preview:
        build_preview_files(themes[0], renderer, ROOT / "generated")
        return 0
    xcursorgen = resolve_xcursorgen(args.xcursorgen)
    print(f"renderer: {renderer.name}   compiler: {'xcursorgen' if xcursorgen else 'builtin'}")
    for theme in themes:
        build_theme(theme, args.sizes, renderer, xcursorgen, args.out_dir, args.inherits, max(1, args.jobs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
