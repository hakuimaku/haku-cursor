"""Cursor drawings + the central registry (names, hotspots, animation, aliases).

Every ``draw_*`` function has the signature ``(theme, t) -> Group`` where ``t`` is the animation
phase in ``[0, 1)`` (``None`` = resting frame) and the result is expressed in the 100x100 canvas of
``geometry.py``.  Colours come only from ``theme.base`` and ``theme.accent``.
Hotspots live ONLY in ``CURSORS`` below.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from functools import partial
from typing import Callable, Optional

from geometry import (BADGE_CENTER, CANVAS, BADGE_GLYPH, CENTER, RING_STROKE, STROKE_MAIN,
                      accent_fill, accent_line, accent_stroke, arrowhead, badge_disc, badge_offset,
                      body_fill, body_stroke, phase, pip, polyline, pulse, ripple, ring,
                      rotate_point, rounded_polygon, silhouette, spinner_arcs,
                      staggered)
from palettes import Theme
from svg import Arc, Circle, Group, Line, Matrix, Rect, bounds, rotate, scale, stroke, translate

Phase = Optional[float]
DrawFn = Callable[[Theme, Phase], Group]


# =========================================================================== #
# Pointer: a compact arrowhead, no tail
# =========================================================================== #
ARROW_POINTS = [
    (14, 8),      # tip
    (14, 78),     # bottom-left
    (33, 62),     # notch
    (66, 62),     # right wing
]
ARROW_RADII = [4.5, 5.0, 4.0, 4.5]
ARROW_TIP = ARROW_POINTS[0]


def _arrow(theme: Theme) -> Group:
    return Group([silhouette(theme, [rounded_polygon(ARROW_POINTS, ARROW_RADII, body_fill(theme))])])


def draw_arrow(theme: Theme, t: Phase = None) -> Group:
    return _arrow(theme)


def _small_arrow(theme: Theme) -> Group:
    """Arrow shrunk about its tip so the hotspot stays put; leaves room for a badge."""
    return Group([_arrow(theme)], scale(0.8, cx=ARROW_TIP[0], cy=ARROW_TIP[1]))


def _glyph(items: list, matrix) -> Group:
    return Group(items, matrix)


def _about_badge(s: float):
    return scale(s, cx=BADGE_CENTER[0], cy=BADGE_CENTER[1])


def _with_badge(glyph: Callable[[Theme, Phase], list], theme: Theme, t: Phase) -> Group:
    return Group([_small_arrow(theme), silhouette(theme, [badge_disc(theme)]), *glyph(theme, t)])


# ---- badge glyphs (accent only, centred on BADGE_CENTER, animated through ``t``) ----
def glyph_copy(theme: Theme, t: Phase) -> list:
    plus = [accent_line(theme, badge_offset(-6.5), badge_offset(6.5)),
            accent_line(theme, badge_offset(0, -6.5), badge_offset(0, 6.5))]
    return [_glyph(plus, _about_badge(1.0 + 0.22 * pulse(t)))]


def glyph_link(theme: Theme, t: Phase) -> list:
    arrow = [accent_line(theme, badge_offset(-5.5, 5.5), badge_offset(5.5, -5.5)),
             polyline([badge_offset(-4, -5.5), badge_offset(5.5, -5.5), badge_offset(5.5, 4)],
                      accent_stroke(theme, BADGE_GLYPH))]
    d = 2.2 * pulse(t)
    return [_glyph(arrow, translate(d, -d))]


def glyph_move(theme: Theme, t: Phase) -> list:
    arrow = [accent_line(theme, badge_offset(-7), badge_offset(6)),
             polyline([badge_offset(1, -5.5), badge_offset(6.5, 0), badge_offset(1, 5.5)],
                      accent_stroke(theme, BADGE_GLYPH))]
    return [_glyph(arrow, translate(2.6 * pulse(t), 0))]


def glyph_no_drop(theme: Theme, t: Phase) -> list:
    return [Circle(*badge_offset(0), 8.0, accent_stroke(theme, 2.6)),
            accent_line(theme, badge_offset(-5.7, 5.7), badge_offset(5.7, -5.7), 2.6)]


def glyph_help(theme: Theme, t: Phase) -> list:
    cx, cy = badge_offset(0, -3.6)
    r, end = 4.9, math.radians(40)
    hook_end = (cx + r * math.cos(end), cy + r * math.sin(end))
    mark = [Arc(cx, cy, r, 195, 400, accent_stroke(theme, BADGE_GLYPH)),
            polyline([hook_end, badge_offset(0, 3.4)], accent_stroke(theme, BADGE_GLYPH)),
            Circle(*badge_offset(0, 8.2), 1.7, accent_fill(theme))]
    return [_glyph(mark, _about_badge(1.0 + 0.2 * pulse(t)))]


def glyph_menu(theme: Theme, t: Phase) -> list:
    out = []
    for i, dy in enumerate((-6, 0, 6)):
        out.append(accent_line(theme, badge_offset(-6.5, dy), badge_offset(6.5, dy), 2.6,
                               opacity=0.3 + 0.7 * staggered(t, i, 3)))
    return out


def glyph_progress(theme: Theme, t: Phase) -> list:
    cx, cy = badge_offset(0)
    return [Circle(cx, cy, 8.5, accent_stroke(theme, 3.4, 0.3)),
            *spinner_arcs(theme, cx, cy, 8.5, t, 3.6, head=100.0, tail=50.0)]


def draw_arrow_badge(glyph: Callable, theme: Theme, t: Phase = None) -> Group:
    return _with_badge(glyph, theme, t)


# =========================================================================== #
# Link: pointing hand (click ripple at the fingertip)
# =========================================================================== #
def draw_pointer(theme: Theme, t: Phase = None) -> Group:
    b = body_fill(theme)
    parts = [
        Line((34, 68), (20, 54), body_stroke(theme, 12)),   # thumb
        Rect(33, 8, 15, 54, 7.5, b),                        # index
        Rect(47, 32, 14, 36, 7.0, b),                       # middle
        Rect(60, 38, 13, 30, 6.5, b),                       # ring
        Rect(72, 44, 12, 24, 6.0, b),                       # pinky
        Rect(30, 46, 54, 42, 15.0, b),                      # palm
    ]
    return Group([silhouette(theme, parts), *ripple(theme, 40.5, 28, t, 4.0, 15.0, 2.6)])


# =========================================================================== #
# Grab / grabbing
# =========================================================================== #
def draw_grab(theme: Theme, t: Phase = None) -> Group:
    b = body_fill(theme)
    parts = [
        Line((27, 72), (13, 57), body_stroke(theme, 12)),
        Rect(24, 26, 12.5, 40, 6.25, b),
        Rect(36, 16, 12.5, 50, 6.25, b),
        Rect(48, 22, 12.5, 44, 6.25, b),
        Rect(60, 32, 12.5, 34, 6.25, b),
        Rect(24, 48, 48.5, 40, 14.0, b),
    ]
    return Group([silhouette(theme, parts)], translate(10, 0))


def draw_grabbing(theme: Theme, t: Phase = None) -> Group:
    b = body_fill(theme)
    parts = [
        Rect(24, 34, 12.5, 28, 6.25, b), Rect(36, 30, 12.5, 32, 6.25, b),
        Rect(48, 31, 12.5, 31, 6.25, b), Rect(60, 36, 12.5, 26, 6.25, b),
        Rect(24, 44, 48.5, 42, 15.0, b),
    ]
    return Group([silhouette(theme, parts)], translate(1.7, 0))


# =========================================================================== #
# Text
# =========================================================================== #
def draw_text(theme: Theme, t: Phase = None) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    parts = [Line((50, 18), (50, 82), w), Line((37, 18), (63, 18), w), Line((37, 82), (63, 82), w)]
    return Group([silhouette(theme, parts)])


def draw_vertical_text(theme: Theme, t: Phase = None) -> Group:
    return Group([draw_text(theme, t)], rotate(90, *CENTER))


# =========================================================================== #
# Precision (crosshair sends out a ripple from its centre)
# =========================================================================== #
def draw_crosshair(theme: Theme, t: Phase = None) -> Group:
    w = body_stroke(theme, 8.0)
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [Line((50, 14), (50, 86), w), Line((14, 50), (86, 50), w), disc]),
                  dot, *ripple(theme, 50, 50, t, 8.0, 30.0, 2.8)])


def draw_cell(theme: Theme, t: Phase = None) -> Group:
    pts = [(40, 15), (60, 15), (60, 40), (85, 40), (85, 60), (60, 60),
           (60, 85), (40, 85), (40, 60), (15, 60), (15, 40), (40, 40)]
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [rounded_polygon(pts, 5.0, body_fill(theme)), disc]), dot])


# =========================================================================== #
# Move / resize (arrowheads breathe outwards)
# =========================================================================== #
BREATH = 3.0


def draw_move(theme: Theme, t: Phase = None) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    d = BREATH * pulse(t)
    heads = [arrowhead(theme, rotate_point((50, 10 - d), a), a) for a in (0, 90, 180, 270)]
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [Line((50, 27), (50, 73), w), Line((27, 50), (73, 50), w), *heads, disc]), dot])


def draw_resize_double(theme: Theme, t: Phase = None, angle: float = 0.0) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    d = BREATH * pulse(t)
    parts = [Line((50, 25), (50, 75), w), arrowhead(theme, (50, 10 - d), 0), arrowhead(theme, (50, 90 + d), 180)]
    disc, dot = pip(theme, *CENTER)
    return Group([Group([silhouette(theme, [*parts, disc]), dot], rotate(angle, *CENTER))])


def draw_resize_single(theme: Theme, t: Phase = None, angle: float = 0.0) -> Group:
    """Arrow towards an edge (n/e/s/w and the four corners)."""
    w = body_stroke(theme, STROKE_MAIN)
    d = BREATH * pulse(t)
    parts = [Line((50, 30), (50, 80), w), Line((33, 86), (67, 86), body_stroke(theme, 8.0)),
             arrowhead(theme, (50, 14 - d), 0)]
    disc, dot = pip(theme, 50, 56)
    return Group([Group([silhouette(theme, [*parts, disc]), dot], rotate(angle, *CENTER))])


# =========================================================================== #
# State
# =========================================================================== #
def draw_not_allowed(theme: Theme, t: Phase = None) -> Group:
    r = 29.0
    d = r * math.cos(math.radians(45))
    return Group([silhouette(theme, [ring(theme, *CENTER, r)]),
                  accent_line(theme, (50 - d, 50 - d), (50 + d, 50 + d), 6.0)])


# =========================================================================== #
# Loading
# =========================================================================== #
def draw_wait(theme: Theme, t: Phase = None) -> Group:
    r = 29.0
    return Group([silhouette(theme, [ring(theme, *CENTER, r, RING_STROKE)]),
                  *spinner_arcs(theme, *CENTER, r, t, 5.0, head=95.0, tail=60.0)])


# =========================================================================== #
# Zoom (a glint sweeps around the lens)
# =========================================================================== #
def draw_zoom(theme: Theme, t: Phase = None, plus: bool = True) -> Group:
    lens = Circle(42, 42, 26, body_fill(theme))
    handle = Line((62, 62), (82, 82), body_stroke(theme, 11))
    glyph = [accent_line(theme, (30, 42), (54, 42), 5.0)]
    if plus:
        glyph.append(accent_line(theme, (42, 30), (42, 54), 5.0))
    shine = []
    if t is not None:
        a = -90.0 + 360.0 * phase(t)
        shine = [Arc(42, 42, 19.0, a, a + 55, accent_stroke(theme, 2.6, 0.9))]
    return Group([silhouette(theme, [handle, lens]), *glyph, *shine])


# =========================================================================== #
# Registry
# =========================================================================== #
@dataclass(frozen=True)
class CursorSpec:
    name: str
    draw: DrawFn
    hotspot: tuple[float, float]      # canvas units (0..100)
    group: str                        # used by the preview sheet
    frames: int = 1                   # > 1 -> animated
    delay_ms: int = 0
    aliases: tuple[str, ...] = ()

    @property
    def animated(self) -> bool:
        return self.frames > 1


# Visible tip of the rounded arrow *including* its border (also used by the badge variants).
_ARROW_HOT = (14.0, 8.1)
_C = CENTER
_BREATH = dict(frames=8, delay_ms=80)

_SPECS = [
    # ---- normal ----
    CursorSpec("left_ptr", draw_arrow, _ARROW_HOT, "Default",
               aliases=("default", "arrow", "top_left_arrow", "left-ptr")),
    # ---- link ----
    CursorSpec("pointer", draw_pointer, (40.5, 4.0), "Pointer", frames=12, delay_ms=70,
               aliases=("hand", "hand1", "hand2", "pointing_hand", "link")),
    # ---- text ----
    CursorSpec("text", draw_text, _C, "Text", aliases=("xterm", "ibeam")),
    CursorSpec("vertical-text", draw_vertical_text, _C, "Text"),
    # ---- precision ----
    CursorSpec("crosshair", draw_crosshair, _C, "Precision", frames=10, delay_ms=70,
               aliases=("cross", "tcross", "cross_reverse")),
    CursorSpec("cell", draw_cell, _C, "Precision", aliases=("plus",)),
    # ---- move ----
    CursorSpec("move", draw_move, _C, "Move", aliases=("all-scroll", "fleur", "size_all"), **_BREATH),
    # ---- resize: double headed ----
    CursorSpec("ns-resize", partial(draw_resize_double, angle=0), _C, "Resize", **_BREATH,
               aliases=("sb_v_double_arrow", "v_double_arrow", "double_arrow", "size_ver", "row-resize", "split_v")),
    CursorSpec("ew-resize", partial(draw_resize_double, angle=90), _C, "Resize", **_BREATH,
               aliases=("sb_h_double_arrow", "h_double_arrow", "size_hor", "col-resize", "split_h")),
    CursorSpec("nesw-resize", partial(draw_resize_double, angle=45), _C, "Resize", **_BREATH,
               aliases=("bd_double_arrow", "size_bdiag")),
    CursorSpec("nwse-resize", partial(draw_resize_double, angle=-45), _C, "Resize", **_BREATH,
               aliases=("fd_double_arrow", "size_fdiag")),
    # ---- resize: towards an edge / corner ----
    CursorSpec("n-resize", partial(draw_resize_single, angle=0), _C, "Resize", **_BREATH, aliases=("top_side",)),
    CursorSpec("ne-resize", partial(draw_resize_single, angle=45), _C, "Resize", **_BREATH, aliases=("top_right_corner",)),
    CursorSpec("e-resize", partial(draw_resize_single, angle=90), _C, "Resize", **_BREATH, aliases=("right_side",)),
    CursorSpec("se-resize", partial(draw_resize_single, angle=135), _C, "Resize", **_BREATH, aliases=("bottom_right_corner",)),
    CursorSpec("s-resize", partial(draw_resize_single, angle=180), _C, "Resize", **_BREATH, aliases=("bottom_side",)),
    CursorSpec("sw-resize", partial(draw_resize_single, angle=225), _C, "Resize", **_BREATH, aliases=("bottom_left_corner",)),
    CursorSpec("w-resize", partial(draw_resize_single, angle=270), _C, "Resize", **_BREATH, aliases=("left_side",)),
    CursorSpec("nw-resize", partial(draw_resize_single, angle=315), _C, "Resize", **_BREATH, aliases=("top_left_corner",)),
    # ---- drag ----
    CursorSpec("grab", draw_grab, _C, "Grab", aliases=("openhand",)),
    CursorSpec("grabbing", draw_grabbing, (50.0, 52.0), "Grab", aliases=("closedhand",)),
    CursorSpec("dnd-move", partial(draw_arrow_badge, glyph_move), _ARROW_HOT, "Drag", **_BREATH),
    CursorSpec("dnd-copy", partial(draw_arrow_badge, glyph_copy), _ARROW_HOT, "Drag", **_BREATH, aliases=("copy",)),
    CursorSpec("dnd-link", partial(draw_arrow_badge, glyph_link), _ARROW_HOT, "Drag", **_BREATH, aliases=("alias",)),
    # ---- state ----
    CursorSpec("not-allowed", draw_not_allowed, _C, "State",
               aliases=("forbidden", "crossed_circle", "circle", "dnd-none")),
    CursorSpec("no-drop", partial(draw_arrow_badge, glyph_no_drop), _ARROW_HOT, "State", aliases=("dnd-no-drop",)),
    CursorSpec("help", partial(draw_arrow_badge, glyph_help), _ARROW_HOT, "State", frames=10, delay_ms=80,
               aliases=("question_arrow", "whats_this", "left_ptr_help")),
    CursorSpec("context-menu", partial(draw_arrow_badge, glyph_menu), _ARROW_HOT, "State", frames=12, delay_ms=80),
    # ---- loading ----
    CursorSpec("wait", draw_wait, _C, "Loading", frames=16, delay_ms=60, aliases=("watch",)),
    CursorSpec("progress", partial(draw_arrow_badge, glyph_progress), _ARROW_HOT, "Loading",
               frames=16, delay_ms=60, aliases=("left_ptr_watch", "half-busy")),
    # ---- zoom ----
    CursorSpec("zoom-in", partial(draw_zoom, plus=True), (42.0, 42.0), "Zoom", frames=12, delay_ms=80,
               aliases=("zoom_in",)),
    CursorSpec("zoom-out", partial(draw_zoom, plus=False), (42.0, 42.0), "Zoom", frames=12, delay_ms=80,
               aliases=("zoom_out",)),
]

# --------------------------------------------------------------------------- #
# Fit-to-canvas: every cursor is scaled so its longest side (border included) spans the whole
# nominal size, i.e. exactly 24 px tall/wide at size 24.  Hotspots are mapped accordingly.
# --------------------------------------------------------------------------- #
FIT_MARGIN = 0.5                      # canvas units kept free so anti-aliasing is never clipped
# Pointer-like cursors hug the top-left corner (the hotspot is their tip); the rest are centred.
_TOP_LEFT = {"left_ptr", "pointer", "dnd-move", "dnd-copy", "dnd-link", "no-drop", "help",
             "context-menu", "progress"}
_REF_THEME = Theme("ref", "dark", "#000000", "#ffffff")   # geometry does not depend on colour


def _fit_matrix(spec: CursorSpec) -> Matrix:
    phases = [None] + ([i / spec.frames for i in range(spec.frames)] if spec.animated else [])
    boxes = [bounds(spec.draw(_REF_THEME, p)) for p in phases]
    min_x, min_y = min(b[0] for b in boxes), min(b[1] for b in boxes)
    max_x, max_y = max(b[2] for b in boxes), max(b[3] for b in boxes)
    s = (CANVAS - 2 * FIT_MARGIN) / max(max_x - min_x, max_y - min_y)
    if spec.name in _TOP_LEFT:
        tx, ty = FIT_MARGIN - min_x * s, FIT_MARGIN - min_y * s
    else:
        tx, ty = CANVAS / 2 - (min_x + max_x) / 2 * s, CANVAS / 2 - (min_y + max_y) / 2 * s
    return translate(tx, ty) @ scale(s)


class _Fitted:
    """Draw function wrapper applying the fit transform."""

    def __init__(self, draw: DrawFn, matrix: Matrix) -> None:
        self.draw, self.matrix = draw, matrix

    def __call__(self, theme: Theme, t: Phase = None) -> Group:
        return Group([self.draw(theme, t)], self.matrix)


def _fit(spec: CursorSpec) -> CursorSpec:
    m = _fit_matrix(spec)
    return replace(spec, draw=_Fitted(spec.draw, m), hotspot=m.apply(spec.hotspot))


CURSORS: dict[str, CursorSpec] = {spec.name: _fit(spec) for spec in _SPECS}

# Legacy 32-hex "hash" names still requested by some old X11 / toolkit builds.  Only mappings
# confirmed by public documentation are listed (Arch Wiki "Cursor themes", Gentoo forums thread
# on xcursor symlinks, Vanilla-DMZ).  Extend freely: values must be real cursor names above.
HASH_ALIASES: dict[str, str] = {
    "08e8e1c95fe2fc01f976f1e063a24ccd": "progress",
    "3ecb610c1bf2410f44200f48c40d3599": "progress",
    "6ce0180090108e0005814700a0021400": "progress",
    "fc618c00da110f0034fd0e004e082400": "wait",
    "9d800788f1b08800ae810202380a0822": "pointer",
    "e29285e634086352946a0e7090d73106": "pointer",
    "d2201000a2c622004385440041308800": "pointer",
    "d9ce0ab605698f320427677b458ad60b": "help",
    "00000000017e000002fc000000000000": "text",
    "24020000002800000528000084810000": "left_ptr",
}


def build_alias_map() -> dict[str, str]:
    """alias -> real cursor name (explicit aliases first, then hash names). Validates consistency."""
    aliases: dict[str, str] = {}
    for spec in CURSORS.values():
        for alias in spec.aliases:
            if alias in CURSORS:
                raise ValueError(f"alias {alias!r} shadows a real cursor")
            if alias in aliases:
                raise ValueError(f"alias {alias!r} defined twice")
            aliases[alias] = spec.name
    for alias, target in HASH_ALIASES.items():
        if target not in CURSORS or alias in aliases or alias in CURSORS:
            raise ValueError(f"bad hash alias {alias} -> {target}")
        aliases[alias] = target
    return aliases


ALIASES: dict[str, str] = build_alias_map()
