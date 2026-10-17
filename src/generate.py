#!/usr/bin/env python3
"""Haku Cursor generator: geometry (code) -> SVG -> PNG -> xcursorgen -> XCursor theme.

Examples
--------
    python src/generate.py                                # Haku-Dark + Haku-Light
    python src/generate.py --palette blue                 # Haku-Blue + Haku-Blue-Light
    python src/generate.py --palette blue --style light
    python src/generate.py --all
    python src/generate.py --accent "#7aa2f7" --name Haku-Tokyo
    python src/generate.py --palette blue --animations loading
    python src/generate.py --preview
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import palettes
import raster
import xcursor
from cursors import ALIASES, CURSORS, CursorSpec
from geometry import CANVAS
from palettes import Theme
from preview import build_filmstrip, build_preview
from svg import Group, document, document_wh

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SIZES = (24, 32, 48, 64, 96)
EXTENDED_SIZES = (16, 20, 24, 28, 32, 40, 48, 56, 64, 72, 96)
ANIMATION_MODES = ("all", "loading", "none")


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

    def render_wide(self, scene: Group, svg_path: Path, png_path: Path, width_px: int,
                    units_w: float, units_h: float) -> None:
        """Non-square sheet (preview / filmstrip)."""
        w = str(width_px)
        if self.name == "pillow":
            raster.render(scene, width_px, units_w, round(units_h * width_px / units_w), units_h).save(png_path)
            return
        cmd = {"rsvg-convert": [self.binary, "-w", w, "-o", str(png_path), str(svg_path)],
               "resvg": [self.binary, "-w", w, str(svg_path), str(png_path)],
               "inkscape": [self.binary, str(svg_path), "--export-type=png",
                            f"--export-filename={png_path}", "-w", w]}[self.name]
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
def frame_count(spec: CursorSpec, mode: str) -> int:
    """How many frames this cursor gets under the chosen ``--animations`` mode."""
    if mode == "all" or (mode == "loading" and spec.group == "Loading"):
        return spec.frames
    return 1


def hotspot_px(spec: CursorSpec, size: int) -> tuple[int, int]:
    """Pixel containing the canvas-space hotspot at this size."""
    k = size / CANVAS
    return (min(size - 1, max(0, math.floor(spec.hotspot[0] * k))),
            min(size - 1, max(0, math.floor(spec.hotspot[1] * k))))


def frame_stem(spec: CursorSpec, index: int, frames: int) -> str:
    return f"{spec.name}-{index:02d}" if frames > 1 else spec.name


def write_conf(spec: CursorSpec, frames: int, sizes: tuple[int, ...], conf_path: Path) -> None:
    """xcursorgen config: ``size xhot yhot file [delay]`` (frames grouped per size)."""
    lines = []
    for size in sizes:
        xh, yh = hotspot_px(spec, size)
        for i in range(frames):
            line = f"{size} {xh} {yh} {frame_stem(spec, i, frames)}-{size}.png"
            if frames > 1:
                line += f" {spec.delay_ms}"
            lines.append(line)
    conf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_builtin(spec: CursorSpec, frames: int, sizes: tuple[int, ...], png_dir: Path, out: Path) -> None:
    from PIL import Image  # PNG decoding for the fallback writer

    result = []
    for size in sizes:
        xh, yh = hotspot_px(spec, size)
        for i in range(frames):
            with Image.open(png_dir / f"{frame_stem(spec, i, frames)}-{size}.png") as im:
                im = im.convert("RGBA")
                argb = xcursor.premultiply_rgba(im.tobytes())
                result.append(xcursor.Frame(size, im.width, im.height, xh, yh,
                                            spec.delay_ms if frames > 1 else 0, argb))
    xcursor.write(out, result)


def compile_cursor(spec: CursorSpec, frames: int, sizes: tuple[int, ...], conf: Path, png_dir: Path,
                   out: Path, xcursorgen: str | None) -> None:
    if xcursorgen:
        subprocess.run([xcursorgen, "-p", str(png_dir), str(conf), str(out)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    else:
        compile_builtin(spec, frames, sizes, png_dir, out)


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
                out_dir: Path, inherits: str, jobs: int, animations: str = "all") -> Path:
    gen_dir = ROOT / "generated" / theme.name
    conf_dir = ROOT / "build" / theme.name
    theme_dir = out_dir / theme.name
    for d in (gen_dir, conf_dir, theme_dir):
        shutil.rmtree(d, ignore_errors=True)
    svg_dir, png_dir, cursors_dir = gen_dir / "svg", gen_dir / "png", theme_dir / "cursors"
    for d in (svg_dir, png_dir, conf_dir, cursors_dir):
        d.mkdir(parents=True, exist_ok=True)

    counts = {spec.name: frame_count(spec, animations) for spec in CURSORS.values()}

    # 1) geometry -> SVG (one vector file per frame, shared by every pixel size)
    render_jobs = []
    for spec in CURSORS.values():
        n = counts[spec.name]
        for i in range(n):
            scene = spec.draw(theme, i / n if n > 1 else None)
            svg_path = svg_dir / f"{frame_stem(spec, i, n)}.svg"
            svg_path.write_text(document(scene, CANVAS, title=spec.name), encoding="utf-8")
            render_jobs.append((scene, svg_path))

    # 2) SVG -> PNG, re-rasterised from the vector at every size
    tasks = [(scene, svg, size, png_dir / f"{svg.stem}-{size}.png")
             for scene, svg in render_jobs for size in sizes]
    _parallel(jobs, lambda t: renderer.render(t[0], t[1], t[2], t[3]), tasks)

    # 3) xcursorgen config + compile
    def compile_one(spec: CursorSpec) -> None:
        n = counts[spec.name]
        conf = conf_dir / f"{spec.name}.conf"
        write_conf(spec, n, sizes, conf)
        compile_cursor(spec, n, sizes, conf, png_dir, cursors_dir / spec.name, xcursorgen)

    _parallel(jobs, compile_one, list(CURSORS.values()))

    # 4) aliases + index.theme (+ machine-readable description for verify.py)
    n_alias = make_aliases(cursors_dir)
    write_index_theme(theme, theme_dir, inherits)
    (conf_dir / "theme.json").write_text(json.dumps({
        "name": theme.name, "style": theme.style, "base": theme.base, "accent": theme.accent,
        "sizes": list(sizes), "animations": animations,
    }, indent=2) + "\n", encoding="utf-8")
    animated = sum(1 for n in counts.values() if n > 1)
    print(f"  {theme.name}: {len(CURSORS)} cursors ({animated} animated), {n_alias} aliases, "
          f"sizes {','.join(map(str, sizes))} -> {theme_dir}")
    return theme_dir


def build_preview_files(theme: Theme, renderer: Renderer, out_dir: Path) -> None:
    """Write static sheets, filmstrips and a timed GIF for the README."""
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "" if theme.style == "dark" else f"-{theme.style}"
    for stem, (scene, w, h) in ((f"preview{suffix}", build_preview(theme)),
                                (f"animations{suffix}", build_filmstrip(theme))):
        svg_path, png_path = out_dir / f"{stem}.svg", out_dir / f"{stem}.png"
        svg_path.write_text(document_wh(scene, w, h), encoding="utf-8")
        renderer.render_wide(scene, svg_path, png_path, int(w), w, h)
        print(f"  {svg_path}  {png_path}")
    build_preview_gif(theme, renderer, out_dir / f"preview{suffix}.gif")


def build_preview_gif(theme: Theme, renderer: Renderer, gif_path: Path) -> None:
    """Encode a 4.8-second preview using the installed renderer and Pillow."""
    from PIL import Image  # GIF encoding; normal theme builds do not need Pillow

    frames = []  # opaque frames preserve the dark and light preview backgrounds
    with tempfile.TemporaryDirectory() as tmp:
        svg_path, png_path = Path(tmp) / "frame.svg", Path(tmp) / "frame.png"
        for elapsed_ms in range(0, 4800, 40):
            scene, w, h = build_preview(theme, elapsed_ms)
            svg_path.write_text(document_wh(scene, w, h), encoding="utf-8")
            renderer.render_wide(scene, svg_path, png_path, int(w / 2), w, h)
            with Image.open(png_path) as frame:
                frames.append(frame.convert("RGB").quantize(colors=128))
    frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=40, loop=0)
    print(f"  {gif_path}")


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
    p.add_argument("--palette", "-p", nargs="+", metavar="NAME", help=f"preset(s): {', '.join(palettes.PALETTE_KEYS)} (default: default)")
    p.add_argument("--all", action="store_true", help="build every preset palette")
    p.add_argument("--style", choices=["dark", "light", "both"], default="both",
                   help="dark = dark fill, light = light fill (theme name gets a -Light suffix); default: both")
    p.add_argument("--animations", choices=ANIMATION_MODES, default="all",
                   help="all (default), loading (only wait/progress animate) or none (all static)")
    p.add_argument("--name", help="theme name without style suffix (custom variants), e.g. Haku-Tokyo")
    p.add_argument("--accent", help="custom accent (border + glyph) colour, e.g. '#7aa2f7'")
    p.add_argument("--base", help="override the fill colour (default from config/palettes.json)")
    p.add_argument("--sizes", type=parse_sizes, default=DEFAULT_SIZES,
                   help="'default' (24,32,48,64,96), 'extended', or a comma list")
    p.add_argument("--inherits", default="Adwaita", help="fallback theme written to index.theme")
    p.add_argument("--out-dir", type=Path, default=ROOT / "dist", help="where finished themes go (default: dist/)")
    p.add_argument("--renderer", default="auto", choices=["auto", "rsvg-convert", "resvg", "inkscape", "pillow"])
    p.add_argument("--xcursorgen", default="auto", choices=["auto", "xcursorgen", "builtin"],
                   help="use the xcursorgen binary from PATH or the built-in pure-Python writer")
    p.add_argument("--jobs", "-j", type=int, default=os.cpu_count() or 2)
    p.add_argument("--preview", action="store_true",
                   help="only write generated/preview*.svg/png/gif and animations*.svg/png (needs Pillow)")
    p.add_argument("--list", action="store_true", help="list palettes and cursors, then exit")
    return p


def select_themes(args: argparse.Namespace) -> list[Theme]:
    custom = any((args.accent, args.base))
    styles = palettes.STYLE_NAMES if args.style == "both" else (args.style,)
    if args.all:
        if custom or args.name:
            raise SystemExit("error: --all cannot be combined with --accent/--base/--name")
        return palettes.all_preset_themes(styles)
    keys = args.palette or ["default"]
    if len(keys) > 1 and (custom or args.name):
        raise SystemExit("error: --name/--accent/--base need a single --palette")
    try:
        return [palettes.make_theme(k, s, name=args.name, accent=args.accent, base=args.base)
                for k in keys for s in styles]
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
        for style in palettes.STYLE_NAMES:
            print(f"{style:5s} accents:", ", ".join(f"{k}={v}" for k, v in palettes.PALETTES[style].items()))
        print("cursors :", ", ".join(f"{s.name}{'*' if s.animated else ''}" for s in CURSORS.values()), "(* animated)")
        print(f"aliases : {len(ALIASES)}")
        return 0
    themes = select_themes(args)
    renderer = detect_renderer(args.renderer)
    if args.preview:
        first_per_style = {}
        for theme in themes:
            first_per_style.setdefault(theme.style, theme)
        for theme in first_per_style.values():
            build_preview_files(theme, renderer, ROOT / "generated")
        return 0
    xcursorgen = resolve_xcursorgen(args.xcursorgen)
    print(f"renderer: {renderer.name}   compiler: {'xcursorgen' if xcursorgen else 'builtin'}   "
          f"animations: {args.animations}")
    for theme in themes:
        build_theme(theme, args.sizes, renderer, xcursorgen, args.out_dir, args.inherits,
                    max(1, args.jobs), args.animations)
    return 0


if __name__ == "__main__":
    sys.exit(main())
