"""Haku design system: tokens + reusable geometry helpers.

Every cursor is drawn on a fixed ``CANVAS x CANVAS`` grid (normalised units) and
rasterised at each requested pixel size, so hotspots and proportions stay exact.

Visual rules shared by *all* cursors
------------------------------------
* TWO colours only: ``theme.base`` (fill) and ``theme.accent`` (border + every glyph).
* border ........... accent, ``OUTLINE`` units thick, hugging the union of all
                     filled shapes of a cursor (so overlapping parts merge cleanly)
* linework ......... ``STROKE_MAIN`` for primary strokes, ``STROKE_MINOR`` for
                     details, always round caps / joins
* corners .......... ``CORNER_RADIUS`` on polygons
* no tails ......... the pointer is a compact arrowhead, nothing sticks out of it
* animation ........ every ``draw`` takes a phase ``t`` in [0, 1) or ``None`` for the
                     resting frame; helpers below keep motion subtle and loop seamlessly
"""

from __future__ import annotations

import math
from typing import Sequence

from palettes import Theme
from svg import (Arc, Circle, Group, Line, Path, Point, Shape, Style, fill, rotate,
                 stroke, translate, with_style)

# --------------------------------------------------------------------------- #
# Design tokens (canvas units; the canvas is CANVAS x CANVAS)
# --------------------------------------------------------------------------- #
CANVAS = 100.0
CENTER: Point = (50.0, 50.0)

STROKE_MAIN = 9.0        # shafts, I-beam, crosshair arms
STROKE_MINOR = 3.0       # separators, badge glyphs
RING_STROKE = 10.0       # spinner / forbidden ring
OUTLINE = 5.0            # accent border thickness, measured outside the fill
CORNER_RADIUS = 4.0      # default polygon rounding
SEPARATOR = 2.0          # thin accent lines separating fingers
ACCENT_LINE = 3.6        # accent inlay thickness
PIP_DISC_R = 8.0         # base disc that carries the accent pip
PIP_DOT_R = 4.0          # accent pip radius

ARROWHEAD_LEN = 18.0
ARROWHEAD_HALF = 14.0

BADGE_CENTER: Point = (73.0, 73.0)
BADGE_R = 15.5
BADGE_GLYPH = 3.0        # accent stroke inside badges


# --------------------------------------------------------------------------- #
# Primitive constructors bound to a theme
# --------------------------------------------------------------------------- #
def body_fill(theme: Theme) -> Style:
    return fill(theme.base)


def body_stroke(theme: Theme, width: float) -> Style:
    return stroke(theme.base, width)


def accent_stroke(theme: Theme, width: float = ACCENT_LINE, opacity: float = 1.0) -> Style:
    return stroke(theme.accent, width, opacity)


def accent_fill(theme: Theme) -> Style:
    return fill(theme.accent)


def separator(theme: Theme, p0: Point, p1: Point) -> Line:
    return Line(p0, p1, accent_stroke(theme, SEPARATOR))


# --------------------------------------------------------------------------- #
# Border ("halo") handling
# --------------------------------------------------------------------------- #
def halo(shape: Shape, color: str, grow: float = OUTLINE) -> Shape:
    """Copy of ``shape`` painted in ``color`` and grown outward by ``grow`` units."""
    s = shape.style
    if s.stroke:                       # stroke-only line-work: widen the stroke
        return with_style(shape, Style(stroke=color, width=s.width + 2 * grow))
    return with_style(shape, Style(fill=color, stroke=color, width=2 * grow))


def silhouette(theme: Theme, shapes: Sequence[Shape], grow: float = OUTLINE) -> Group:
    """Paint all accent borders first, then every body, so overlapping parts merge cleanly."""
    return Group([halo(s, theme.accent, grow) for s in shapes] + list(shapes))


# --------------------------------------------------------------------------- #
# Polygon helpers
# --------------------------------------------------------------------------- #
def lerp(a: Point, b: Point, t: float) -> Point:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _unit(a: Point, b: Point) -> tuple[Point, float]:
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    return (dx / length, dy / length), length


def rounded_polygon(points: Sequence[Point], radius: float | Sequence[float] = CORNER_RADIUS,
                    style: Style | None = None) -> Path:
    """Closed polygon with softly rounded corners (quadratic curves, one radius per vertex)."""
    n = len(points)
    radii = [radius] * n if isinstance(radius, (int, float)) else list(radius)
    cuts: list[tuple[Point, Point]] = []
    for i, p in enumerate(points):
        d1, len1 = _unit(p, points[i - 1])
        d2, len2 = _unit(p, points[(i + 1) % n])
        cos_t = max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))
        theta = math.acos(cos_t)
        tangent = radii[i] / math.tan(theta / 2) if theta > 1e-3 else 0.0
        tangent = min(tangent, len1 / 2, len2 / 2)
        cuts.append(((p[0] + d1[0] * tangent, p[1] + d1[1] * tangent),
                     (p[0] + d2[0] * tangent, p[1] + d2[1] * tangent)))
    cmds: list[tuple] = [("M", *cuts[0][1])]
    for i in list(range(1, n)) + [0]:
        before, after = cuts[i]
        cmds += [("L", *before), ("Q", *points[i], *after)]
    cmds.append(("Z",))
    return Path(cmds, style or Style())


def polyline(points: Sequence[Point], style: Style) -> Path:
    cmds: list[tuple] = [("M", *points[0])] + [("L", *p) for p in points[1:]]
    return Path(cmds, style)


def arrowhead(theme: Theme, tip: Point, angle: float = 0.0, length: float = ARROWHEAD_LEN,
              half: float = ARROWHEAD_HALF, radius: float = 2.6) -> Path:
    """Rounded triangle with its tip at ``tip``, pointing ``angle`` degrees clockwise from "up"."""
    m = translate(*tip) @ rotate(angle)
    pts = [m.apply(p) for p in ((0.0, 0.0), (-half, length), (half, length))]
    return rounded_polygon(pts, radius, body_fill(theme))


def rotate_point(p: Point, angle: float, about: Point = CENTER) -> Point:
    return rotate(angle, *about).apply(p)


def pip(theme: Theme, cx: float, cy: float) -> tuple[Circle, Circle]:
    """Accent pip: a base disc (part of the silhouette) and the accent dot on top."""
    return (Circle(cx, cy, PIP_DISC_R, body_fill(theme)),
            Circle(cx, cy, PIP_DOT_R, accent_fill(theme)))


# --------------------------------------------------------------------------- #
# Badges (used by dnd-*, help, progress, no-drop, context-menu)
# --------------------------------------------------------------------------- #
def badge_disc(theme: Theme) -> Circle:
    return Circle(*BADGE_CENTER, BADGE_R, body_fill(theme))


def badge_offset(dx: float, dy: float = 0.0) -> Point:
    return (BADGE_CENTER[0] + dx, BADGE_CENTER[1] + dy)


def accent_line(theme: Theme, p0: Point, p1: Point, width: float = BADGE_GLYPH, opacity: float = 1.0) -> Line:
    return Line(p0, p1, accent_stroke(theme, width, opacity))


def ring(theme: Theme, cx: float, cy: float, r: float, width: float = RING_STROKE) -> Circle:
    return Circle(cx, cy, r, body_stroke(theme, width))


# --------------------------------------------------------------------------- #
# Animation helpers. ``t`` is the loop phase in [0, 1); ``None`` means "resting frame".
# --------------------------------------------------------------------------- #
def phase(t: float | None) -> float:
    return 0.0 if t is None else t


def pulse(t: float | None) -> float:
    """Smooth 0 -> 1 -> 0 loop (0 at rest and at t = 0)."""
    return 0.0 if t is None else 0.5 - 0.5 * math.cos(2 * math.pi * t)


def staggered(t: float | None, index: int, count: int, spread: float = 0.5) -> float:
    """``pulse`` delayed by ``index/count * spread`` of a loop (1.0 at rest)."""
    if t is None:
        return 1.0
    return pulse((t - spread * index / count) % 1.0)


def spinner_arcs(theme: Theme, cx: float, cy: float, r: float, t: float | None,
                 width: float, head: float = 95.0, tail: float = 60.0) -> list[Arc]:
    """Fading arc spinner. ``t`` is one full revolution."""
    angle = -90.0 + 360.0 * phase(t)
    return [
        Arc(cx, cy, r, angle - tail, angle, accent_stroke(theme, width, 0.4)),
        Arc(cx, cy, r, angle, angle + head, accent_stroke(theme, width)),
    ]


def ripple(theme: Theme, cx: float, cy: float, t: float | None, r0: float, r1: float,
           width: float = 3.0) -> list[Circle]:
    """Expanding, fading ring. Nothing is drawn on the resting frame."""
    if t is None:
        return []
    return [Circle(cx, cy, r0 + (r1 - r0) * t, accent_stroke(theme, width, max(0.0, 1.0 - t)))]
