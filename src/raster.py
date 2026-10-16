"""Pillow-based fallback rasteriser for the scene graph in ``svg.py``.

Only used when none of rsvg-convert / resvg / inkscape is installed (e.g. a minimal CI box).
It walks the *same* scene that is serialised to SVG, supersamples, then box-filters down.
Pillow is imported lazily so the rest of the project stays standard-library only.
"""

from __future__ import annotations

import math

from svg import Group, Matrix, Text, scale, walk


def available() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _supersample(size: int) -> int:
    return 8 if size <= 40 else 6 if size <= 64 else 4 if size <= 128 else 2


def _stroke(draw, pts, width: float, closed: bool) -> None:
    """Round-capped / round-joined stroke built from quads and discs."""
    if closed:
        pts = pts + [pts[0]]
    r = width / 2.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        nx, ny = -dy / length * r, dx / length * r
        draw.polygon([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], fill=255)
    for i, (x, y) in enumerate(pts):
        if 0 < i < len(pts) - 1 and not _is_corner(pts[i - 1], pts[i], pts[i + 1]):
            continue  # smooth interior vertex: the quads already overlap enough
        draw.ellipse([x - r, y - r, x + r, y + r], fill=255)


def _is_corner(a, b, c, min_turn_deg: float = 4.0) -> bool:
    v1 = (b[0] - a[0], b[1] - a[1])
    v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return False
    cos_t = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_t)))) > min_turn_deg


def render(root: Group, width: int, canvas: float = 100.0, height: int | None = None,
           canvas_h: float | None = None):
    """Rasterise ``root`` (scene units) to a straight-alpha RGBA image.

    ``width`` pixels span ``canvas`` units; ``height``/``canvas_h`` default to a square image.
    """
    from PIL import Image, ImageDraw, ImageFont

    height = width if height is None else height
    ss = _supersample(width)
    pw, ph = width * ss, height * ss
    base = scale(pw / canvas)
    img = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))

    def composite(mask, color: str, opacity: float) -> None:
        if opacity < 1.0:
            mask = mask.point(lambda v: int(v * opacity + 0.5))
        layer = Image.new("RGBA", (pw, ph), _rgb(color) + (0,))
        layer.putalpha(mask)
        img.alpha_composite(layer)

    for shape, m in walk(root, base):
        style = shape.style
        if isinstance(shape, Text):
            mask = Image.new("L", (pw, ph), 0)
            d = ImageDraw.Draw(mask)
            font = ImageFont.load_default(size=max(1, round(shape.size * m.uniform_scale)))
            x, y = m.apply((shape.x, shape.y))
            d.text((x, y), shape.text, font=font, fill=255,
                   anchor={"start": "ls", "middle": "ms", "end": "rs"}[shape.anchor])
            if style.fill:
                composite(mask, style.fill, style.opacity)
            continue
        polys = [([m.apply(p) for p in pts], closed) for pts, closed in shape.flatten()]
        if style.fill:
            mask = Image.new("L", (pw, ph), 0)
            d = ImageDraw.Draw(mask)
            for pts, _closed in polys:
                if len(pts) >= 3:
                    d.polygon(pts, fill=255)
            composite(mask, style.fill, style.opacity)
        if style.stroke and style.width > 0:
            mask = Image.new("L", (pw, ph), 0)
            d = ImageDraw.Draw(mask)
            for pts, closed in polys:
                _stroke(d, pts, style.width * m.uniform_scale, closed)
            composite(mask, style.stroke, style.opacity)

    return img.resize((width, height), Image.Resampling.BOX)
