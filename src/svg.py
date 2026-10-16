"""Tiny vector scene graph.

Cursor art is described once, in code, as a tree of shapes (``Group`` /
``Polygon`` / ``Path`` / ``Circle`` / ``Rect`` / ``Line`` / ``Arc`` / ``Text``).
That tree is the single source of truth:

* ``to_svg()`` serialises it to plain SVG (the primary pipeline renders this
  with rsvg-convert / resvg / inkscape);
* ``raster.py`` can walk the very same tree to produce pixels when no SVG
  renderer is installed.

Conventions
-----------
* Angles are in degrees; 0 deg points along +x and angles grow clockwise on
  screen (SVG's y axis points down).
* ``opacity`` is only meant for shapes that have a fill *or* a stroke, not both.
* Only standard library is used here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Iterable, Iterator, Sequence

Point = tuple[float, float]
Polyline = tuple[list[Point], bool]  # (points, closed)


def fmt(value: float) -> str:
    """Compact number formatting for SVG attributes."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# --------------------------------------------------------------------------- #
# Affine transforms
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Matrix:
    """SVG-style affine matrix ``[a c e; b d f; 0 0 1]``."""

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    def __matmul__(self, other: "Matrix") -> "Matrix":
        """``(m1 @ m2)(p) == m1(m2(p))``."""
        return Matrix(
            self.a * other.a + self.c * other.b,
            self.b * other.a + self.d * other.b,
            self.a * other.c + self.c * other.d,
            self.b * other.c + self.d * other.d,
            self.a * other.e + self.c * other.f + self.e,
            self.b * other.e + self.d * other.f + self.f,
        )

    def apply(self, p: Point) -> Point:
        x, y = p
        return (self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f)

    @property
    def uniform_scale(self) -> float:
        """Average scale factor (exact for rotations + uniform scaling)."""
        return math.sqrt(abs(self.a * self.d - self.b * self.c))

    @property
    def is_identity(self) -> bool:
        return self == IDENTITY

    def svg(self) -> str:
        return "matrix(" + " ".join(fmt(v) for v in (self.a, self.b, self.c, self.d, self.e, self.f)) + ")"


IDENTITY = Matrix()


def translate(dx: float, dy: float = 0.0) -> Matrix:
    return Matrix(e=dx, f=dy)


def scale(sx: float, sy: float | None = None, cx: float = 0.0, cy: float = 0.0) -> Matrix:
    """Scale about ``(cx, cy)``."""
    sy = sx if sy is None else sy
    return translate(cx, cy) @ Matrix(a=sx, d=sy) @ translate(-cx, -cy)


def rotate(deg: float, cx: float = 0.0, cy: float = 0.0) -> Matrix:
    """Rotate clockwise on screen by ``deg`` about ``(cx, cy)``."""
    r = math.radians(deg)
    cos, sin = math.cos(r), math.sin(r)
    return translate(cx, cy) @ Matrix(cos, sin, -sin, cos) @ translate(-cx, -cy)


# --------------------------------------------------------------------------- #
# Style
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Style:
    fill: str | None = None
    stroke: str | None = None
    width: float = 0.0
    opacity: float = 1.0

    def attrs(self) -> str:
        parts = [f'fill="{self.fill}"' if self.fill else 'fill="none"']
        if self.stroke:
            parts += [
                f'stroke="{self.stroke}"',
                f'stroke-width="{fmt(self.width)}"',
                'stroke-linecap="round"',
                'stroke-linejoin="round"',
            ]
        if self.opacity < 1.0:
            parts.append(f'opacity="{fmt(self.opacity)}"')
        return " ".join(parts)


def fill(color: str, opacity: float = 1.0) -> Style:
    return Style(fill=color, opacity=opacity)


def stroke(color: str, width: float, opacity: float = 1.0) -> Style:
    return Style(stroke=color, width=width, opacity=opacity)


# --------------------------------------------------------------------------- #
# Shapes
# --------------------------------------------------------------------------- #
def _points_attr(points: Iterable[Point]) -> str:
    return " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)


def _sample_quadratic(p0: Point, c: Point, p1: Point, steps: int = 8) -> list[Point]:
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        out.append((mt * mt * p0[0] + 2 * mt * t * c[0] + t * t * p1[0],
                    mt * mt * p0[1] + 2 * mt * t * c[1] + t * t * p1[1]))
    return out


def _arc_points(cx: float, cy: float, r: float, a0: float, a1: float, max_step: float = 4.0) -> list[Point]:
    steps = max(2, int(math.ceil(abs(a1 - a0) / max_step)))
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


@dataclass
class Polygon:
    points: Sequence[Point]
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        return [(list(self.points), True)]

    def to_svg(self) -> str:
        return f'<polygon points="{_points_attr(self.points)}" {self.style.attrs()}/>'


@dataclass
class Path:
    """Path made of ``("M", x, y)``, ``("L", x, y)``, ``("Q", cx, cy, x, y)`` and ``("Z",)``."""

    commands: Sequence[tuple]
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        result: list[Polyline] = []
        current: list[Point] = []
        for cmd in self.commands:
            op = cmd[0]
            if op == "M":
                if current:
                    result.append((current, False))
                current = [(cmd[1], cmd[2])]
            elif op == "L":
                current.append((cmd[1], cmd[2]))
            elif op == "Q":
                current.extend(_sample_quadratic(current[-1], (cmd[1], cmd[2]), (cmd[3], cmd[4])))
            elif op == "Z":
                if current:
                    result.append((current, True))
                    current = []
        if current:
            result.append((current, False))
        return result

    def to_svg(self) -> str:
        parts = []
        for cmd in self.commands:
            parts.append(cmd[0] + " ".join(fmt(v) for v in cmd[1:]) if len(cmd) > 1 else cmd[0])
        return f'<path d="{" ".join(parts)}" {self.style.attrs()}/>'


@dataclass
class Circle:
    cx: float
    cy: float
    r: float
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        pts = _arc_points(self.cx, self.cy, self.r, 0, 360, max_step=5.0)[:-1]
        return [(pts, True)]

    def to_svg(self) -> str:
        return f'<circle cx="{fmt(self.cx)}" cy="{fmt(self.cy)}" r="{fmt(self.r)}" {self.style.attrs()}/>'


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    rx: float = 0.0
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        x0, y0, x1, y1 = self.x, self.y, self.x + self.w, self.y + self.h
        r = min(self.rx, self.w / 2, self.h / 2)
        if r <= 0:
            return [([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)]
        pts: list[Point] = []
        for cx, cy, start in ((x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            pts += _arc_points(cx, cy, r, start, start + 90, max_step=15)
        return [(pts, True)]

    def to_svg(self) -> str:
        rx = f' rx="{fmt(self.rx)}"' if self.rx else ""
        return (f'<rect x="{fmt(self.x)}" y="{fmt(self.y)}" width="{fmt(self.w)}" '
                f'height="{fmt(self.h)}"{rx} {self.style.attrs()}/>')


@dataclass
class Line:
    p0: Point
    p1: Point
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        return [([self.p0, self.p1], False)]

    def to_svg(self) -> str:
        return (f'<line x1="{fmt(self.p0[0])}" y1="{fmt(self.p0[1])}" '
                f'x2="{fmt(self.p1[0])}" y2="{fmt(self.p1[1])}" {self.style.attrs()}/>')


@dataclass
class Arc:
    """Circular arc from angle ``a0`` to ``a1`` (degrees, clockwise on screen, < 360 sweep)."""

    cx: float
    cy: float
    r: float
    a0: float
    a1: float
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:
        return [(_arc_points(self.cx, self.cy, self.r, self.a0, self.a1), False)]

    def to_svg(self) -> str:
        sweep = max(-359.9, min(359.9, self.a1 - self.a0))
        start, end = math.radians(self.a0), math.radians(self.a0 + sweep)
        x0, y0 = self.cx + self.r * math.cos(start), self.cy + self.r * math.sin(start)
        x1, y1 = self.cx + self.r * math.cos(end), self.cy + self.r * math.sin(end)
        large = 1 if abs(sweep) > 180 else 0
        direction = 1 if sweep > 0 else 0
        d = f"M{fmt(x0)} {fmt(y0)} A{fmt(self.r)} {fmt(self.r)} 0 {large} {direction} {fmt(x1)} {fmt(y1)}"
        return f'<path d="{d}" {self.style.attrs()}/>'


@dataclass
class Text:
    x: float
    y: float
    text: str
    size: float = 8.0
    anchor: str = "middle"  # start | middle | end
    style: Style = field(default_factory=Style)

    def flatten(self) -> list[Polyline]:  # text is handled specially by the rasteriser
        return []

    def to_svg(self) -> str:
        escaped = self.text.replace("&", "&amp;").replace("<", "&lt;")
        return (f'<text x="{fmt(self.x)}" y="{fmt(self.y)}" font-family="sans-serif" '
                f'font-size="{fmt(self.size)}" text-anchor="{self.anchor}" {self.style.attrs()}>{escaped}</text>')


Shape = Polygon | Path | Circle | Rect | Line | Arc | Text


@dataclass
class Group:
    children: list = field(default_factory=list)
    transform: Matrix = IDENTITY

    def add(self, *items) -> "Group":
        self.children.extend(items)
        return self

    def to_svg(self, indent: int = 0) -> str:
        pad = "  " * indent
        inner = "\n".join(_node_svg(child, indent + 1) for child in self.children)
        attr = "" if self.transform.is_identity else f' transform="{self.transform.svg()}"'
        return f"{pad}<g{attr}>\n{inner}\n{pad}</g>"


def _node_svg(node, indent: int) -> str:
    if isinstance(node, Group):
        return node.to_svg(indent)
    return "  " * indent + node.to_svg()


def walk(node, matrix: Matrix = IDENTITY) -> Iterator[tuple[Shape, Matrix]]:
    """Yield ``(shape, accumulated_matrix)`` in paint order."""
    if isinstance(node, Group):
        m = matrix @ node.transform
        for child in node.children:
            yield from walk(child, m)
    else:
        yield node, matrix


def with_style(shape: Shape, style: Style) -> Shape:
    return replace(shape, style=style)


def document(root: Group, size: float = 100.0, title: str | None = None) -> str:
    """Serialise a scene to a standalone SVG document (``size`` x ``size`` user units)."""
    s = fmt(size)
    head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{s}" height="{s}" viewBox="0 0 {s} {s}">'
    title_tag = f"\n  <title>{title}</title>" if title else ""
    return f"{head}{title_tag}\n{root.to_svg(1)}\n</svg>\n"


def document_wh(root: Group, width: float, height: float) -> str:
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(width)}" height="{fmt(height)}" '
            f'viewBox="0 0 {fmt(width)} {fmt(height)}">')
    return f"{head}\n{root.to_svg(1)}\n</svg>\n"
