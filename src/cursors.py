"""Cursor drawings + the central registry (names, hotspots, animation, aliases).

Every ``draw_*`` function has the signature ``(theme, t) -> Group`` where ``t`` in ``[0, 1)`` is
the animation phase (ignored by static cursors) and the result is expressed in the 100x100
canvas of ``geometry.py``.  Hotspots live ONLY in ``CURSORS`` below.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import partial
from typing import Callable

from geometry import (ACCENT_LINE, BADGE_GLYPH, CENTER, RING_STROKE, STROKE_MAIN, accent_fill,
                      accent_line, accent_stroke, arrowhead, badge_disc, badge_offset, body_fill,
                      body_stroke, lerp, pip, polyline, ring, rotate_point, rounded_polygon,
                      separator, silhouette, spinner_arcs)
from palettes import Theme
from svg import Arc, Circle, Group, Line, Rect, rotate, scale, stroke, translate

DrawFn = Callable[[Theme, float], Group]


# =========================================================================== #
# Pointer family
# =========================================================================== #
ARROW_POINTS = [
    (14, 8),      # tip
    (14, 72),     # left-bottom
    (27, 60),     # notch, left
    (36, 85),     # tail, bottom-left
    (47, 80),     # tail, bottom-right
    (38, 55.5),   # notch, right
    (58, 55.5),   # right wing
]
ARROW_RADII = [2.2, 3.0, 3.0, 3.4, 3.4, 3.0, 3.4]
ARROW_TIP = ARROW_POINTS[0]


def _arrow(theme: Theme) -> Group:
    body = rounded_polygon(ARROW_POINTS, ARROW_RADII, body_fill(theme))
    p = ARROW_POINTS

    def axis(t: float):  # centre line of the tail
        return lerp(lerp(p[2], p[3], t), lerp(p[5], p[4], t), 0.5)

    return Group([silhouette(theme, [body]), accent_line(theme, axis(0.40), axis(0.78), ACCENT_LINE)])


def draw_arrow(theme: Theme, t: float = 0.0) -> Group:
    return _arrow(theme)


def _small_arrow(theme: Theme) -> Group:
    """Arrow shrunk about its tip so the hotspot stays put; leaves room for a badge."""
    return Group([_arrow(theme)], scale(0.9, cx=ARROW_TIP[0], cy=ARROW_TIP[1]))


def _with_badge(glyph: Callable[[Theme, float], list], theme: Theme, t: float) -> Group:
    return Group([_small_arrow(theme), silhouette(theme, [badge_disc(theme)]), *glyph(theme, t)])


# ---- badge glyphs (all accent coloured, centred on BADGE_CENTER) ----
def glyph_copy(theme: Theme, t: float) -> list:
    return [accent_line(theme, badge_offset(-6.5), badge_offset(6.5)),
            accent_line(theme, badge_offset(0, -6.5), badge_offset(0, 6.5))]


def glyph_link(theme: Theme, t: float) -> list:
    return [accent_line(theme, badge_offset(-5.5, 5.5), badge_offset(5.5, -5.5)),
            polyline([badge_offset(-4, -5.5), badge_offset(5.5, -5.5), badge_offset(5.5, 4)],
                     accent_stroke(theme, BADGE_GLYPH))]


def glyph_move(theme: Theme, t: float) -> list:
    return [accent_line(theme, badge_offset(-7), badge_offset(6)),
            polyline([badge_offset(1, -5.5), badge_offset(6.5, 0), badge_offset(1, 5.5)],
                     accent_stroke(theme, BADGE_GLYPH))]


def glyph_no_drop(theme: Theme, t: float) -> list:
    return [Circle(*badge_offset(0), 8.0, accent_stroke(theme, 2.6)),
            accent_line(theme, badge_offset(-5.7, 5.7), badge_offset(5.7, -5.7), 2.6)]


def glyph_help(theme: Theme, t: float) -> list:
    cx, cy = badge_offset(0, -3.6)
    r, end = 4.9, math.radians(40)
    hook_end = (cx + r * math.cos(end), cy + r * math.sin(end))
    return [Arc(cx, cy, r, 195, 400, accent_stroke(theme, BADGE_GLYPH)),
            polyline([hook_end, badge_offset(0, 3.4)], accent_stroke(theme, BADGE_GLYPH)),
            Circle(*badge_offset(0, 8.2), 1.7, accent_fill(theme))]


def glyph_menu(theme: Theme, t: float) -> list:
    return [accent_line(theme, badge_offset(-6.5, dy), badge_offset(6.5, dy), 2.6) for dy in (-6, 0, 6)]


def glyph_progress(theme: Theme, t: float) -> list:
    cx, cy = badge_offset(0)
    dim = Circle(cx, cy, 8.0, stroke(theme.outline, 3.0, 0.3))
    return [dim, *spinner_arcs(theme, cx, cy, 8.0, t, 3.2, head=100.0, tail=50.0)]


def draw_arrow_badge(glyph: Callable, theme: Theme, t: float = 0.0) -> Group:
    return _with_badge(glyph, theme, t)


# =========================================================================== #
# Link: pointing hand
# =========================================================================== #
def draw_pointer(theme: Theme, t: float = 0.0) -> Group:
    b = body_fill(theme)
    parts = [
        Line((34, 66), (21, 53), body_stroke(theme, 12)),   # thumb
        Rect(32, 8, 17, 52, 8.5, b),                        # index
        Rect(47, 32, 16, 34, 8.0, b),                       # middle
        Rect(61, 38, 15, 28, 7.5, b),                       # ring
        Rect(32, 46, 45, 40, 13.0, b),                      # palm
    ]
    return Group([silhouette(theme, parts),
                  separator(theme, (48, 36), (48, 51)),
                  separator(theme, (62, 42), (62, 54)),
                  accent_line(theme, (43, 77), (66, 77), ACCENT_LINE)])


# =========================================================================== #
# Grab / grabbing
# =========================================================================== #
def draw_grab(theme: Theme, t: float = 0.0) -> Group:
    b = body_fill(theme)
    parts = [
        Line((27, 70), (14, 54), body_stroke(theme, 12)),
        Rect(25.0, 26, 13, 40, 6.5, b),
        Rect(37.5, 16, 13, 50, 6.5, b),
        Rect(50.0, 22, 13, 44, 6.5, b),
        Rect(62.5, 32, 13, 34, 6.5, b),
        Rect(25.0, 48, 50.5, 38, 13.0, b),
    ]
    seps = [separator(theme, (x, 34), (x, 52)) for x in (37.5, 50.0, 62.5)]
    return Group([silhouette(theme, parts), *seps,
                  accent_line(theme, (38, 77), (63, 77), ACCENT_LINE)], translate(8, 0))


def draw_grabbing(theme: Theme, t: float = 0.0) -> Group:
    b = body_fill(theme)
    parts = [
        Rect(24, 36, 13, 26, 6.5, b), Rect(37, 32, 13, 30, 6.5, b),
        Rect(50, 33, 13, 29, 6.5, b), Rect(63, 38, 13, 24, 6.5, b),
        Rect(24, 44, 52, 40, 14.0, b),
    ]
    seps = [separator(theme, (x, 39), (x, 53)) for x in (37.0, 50.0, 63.0)]
    return Group([silhouette(theme, parts), *seps, accent_line(theme, (37, 75), (63, 75), ACCENT_LINE)])


# =========================================================================== #
# Text
# =========================================================================== #
def draw_text(theme: Theme, t: float = 0.0) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    parts = [Line((50, 16), (50, 84), w), Line((39, 16), (61, 16), w), Line((39, 84), (61, 84), w)]
    return Group([silhouette(theme, parts), accent_line(theme, (50, 43), (50, 57), STROKE_MAIN)])


def draw_vertical_text(theme: Theme, t: float = 0.0) -> Group:
    return Group([draw_text(theme)], rotate(90, *CENTER))


# =========================================================================== #
# Precision
# =========================================================================== #
def draw_crosshair(theme: Theme, t: float = 0.0) -> Group:
    w = body_stroke(theme, 5.5)
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [Line((50, 12), (50, 88), w), Line((12, 50), (88, 50), w), disc]), dot])


def draw_cell(theme: Theme, t: float = 0.0) -> Group:
    pts = [(43, 16), (57, 16), (57, 43), (84, 43), (84, 57), (57, 57),
           (57, 84), (43, 84), (43, 57), (16, 57), (16, 43), (43, 43)]
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [rounded_polygon(pts, 3.0, body_fill(theme)), disc]), dot])


# =========================================================================== #
# Move / resize
# =========================================================================== #
def draw_move(theme: Theme, t: float = 0.0) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    heads = [arrowhead(theme, rotate_point((50, 10), a), a) for a in (0, 90, 180, 270)]
    disc, dot = pip(theme, *CENTER)
    return Group([silhouette(theme, [Line((50, 27), (50, 73), w), Line((27, 50), (73, 50), w), *heads, disc]), dot])


def draw_resize_double(theme: Theme, t: float = 0.0, angle: float = 0.0) -> Group:
    w = body_stroke(theme, STROKE_MAIN)
    parts = [Line((50, 25), (50, 75), w), arrowhead(theme, (50, 10), 0), arrowhead(theme, (50, 90), 180)]
    disc, dot = pip(theme, *CENTER)
    return Group([Group([silhouette(theme, [*parts, disc]), dot], rotate(angle, *CENTER))])


def draw_resize_single(theme: Theme, t: float = 0.0, angle: float = 0.0) -> Group:
    """Arrow towards an edge (n/e/s/w and the four corners)."""
    w = body_stroke(theme, STROKE_MAIN)
    parts = [Line((50, 30), (50, 80), w), Line((35, 86), (65, 86), w), arrowhead(theme, (50, 14), 0)]
    disc, dot = pip(theme, 50, 56)
    return Group([Group([silhouette(theme, [*parts, disc]), dot], rotate(angle, *CENTER))])


# =========================================================================== #
# State
# =========================================================================== #
def draw_not_allowed(theme: Theme, t: float = 0.0) -> Group:
    r = 30.0
    d = r * math.cos(math.radians(45))
    return Group([silhouette(theme, [ring(theme, *CENTER, r)]),
                  accent_line(theme, (50 - d, 50 - d), (50 + d, 50 + d), 4.6)])


# =========================================================================== #
# Loading
# =========================================================================== #
def draw_wait(theme: Theme, t: float = 0.0) -> Group:
    r = 28.0
    return Group([silhouette(theme, [ring(theme, *CENTER, r, RING_STROKE)]),
                  *spinner_arcs(theme, *CENTER, r, t, 4.0, head=95.0, tail=60.0)])


# =========================================================================== #
# Zoom
# =========================================================================== #
def draw_zoom(theme: Theme, t: float = 0.0, plus: bool = True) -> Group:
    lens = Circle(42, 42, 25, body_fill(theme))
    handle = Line((60, 60), (84, 84), body_stroke(theme, 10))
    glyph = [accent_line(theme, (31, 42), (53, 42), 4.0)]
    if plus:
        glyph.append(accent_line(theme, (42, 31), (42, 53), 4.0))
    return Group([silhouette(theme, [handle, lens]), *glyph])


# =========================================================================== #
# Registry
# =========================================================================== #
@dataclass(frozen=True)
class CursorSpec:
    name: str
    draw: DrawFn
    hotspot: tuple[float, float]      # canvas units (0..100)
    group: str                        # used by the preview sheet
    frames: int = 1
    delay_ms: int = 0
    aliases: tuple[str, ...] = ()

    @property
    def animated(self) -> bool:
        return self.frames > 1


_ARROW_HOT = (15.0, 10.0)     # visible tip of the rounded arrow (also used by badge variants)
_C = CENTER

_SPECS = [
    # ---- normal ----
    CursorSpec("left_ptr", draw_arrow, _ARROW_HOT, "Default",
               aliases=("default", "arrow", "top_left_arrow", "left-ptr")),
    # ---- link ----
    CursorSpec("pointer", draw_pointer, (40.5, 9.0), "Pointer",
               aliases=("hand", "hand1", "hand2", "pointing_hand", "link")),
    # ---- text ----
    CursorSpec("text", draw_text, _C, "Text", aliases=("xterm", "ibeam")),
    CursorSpec("vertical-text", draw_vertical_text, _C, "Text"),
    # ---- precision ----
    CursorSpec("crosshair", draw_crosshair, _C, "Precision", aliases=("cross", "tcross", "cross_reverse")),
    CursorSpec("cell", draw_cell, _C, "Precision", aliases=("plus",)),
    # ---- move ----
    CursorSpec("move", draw_move, _C, "Move", aliases=("all-scroll", "fleur", "size_all")),
    # ---- resize: double headed ----
    CursorSpec("ns-resize", partial(draw_resize_double, angle=0), _C, "Resize",
               aliases=("sb_v_double_arrow", "v_double_arrow", "double_arrow", "size_ver", "row-resize", "split_v")),
    CursorSpec("ew-resize", partial(draw_resize_double, angle=90), _C, "Resize",
               aliases=("sb_h_double_arrow", "h_double_arrow", "size_hor", "col-resize", "split_h")),
    CursorSpec("nesw-resize", partial(draw_resize_double, angle=45), _C, "Resize",
               aliases=("bd_double_arrow", "size_bdiag")),
    CursorSpec("nwse-resize", partial(draw_resize_double, angle=-45), _C, "Resize",
               aliases=("fd_double_arrow", "size_fdiag")),
    # ---- resize: towards an edge / corner ----
    CursorSpec("n-resize", partial(draw_resize_single, angle=0), _C, "Resize", aliases=("top_side",)),
    CursorSpec("ne-resize", partial(draw_resize_single, angle=45), _C, "Resize", aliases=("top_right_corner",)),
    CursorSpec("e-resize", partial(draw_resize_single, angle=90), _C, "Resize", aliases=("right_side",)),
    CursorSpec("se-resize", partial(draw_resize_single, angle=135), _C, "Resize", aliases=("bottom_right_corner",)),
    CursorSpec("s-resize", partial(draw_resize_single, angle=180), _C, "Resize", aliases=("bottom_side",)),
    CursorSpec("sw-resize", partial(draw_resize_single, angle=225), _C, "Resize", aliases=("bottom_left_corner",)),
    CursorSpec("w-resize", partial(draw_resize_single, angle=270), _C, "Resize", aliases=("left_side",)),
    CursorSpec("nw-resize", partial(draw_resize_single, angle=315), _C, "Resize", aliases=("top_left_corner",)),
    # ---- drag ----
    CursorSpec("grab", draw_grab, _C, "Grab", aliases=("openhand",)),
    CursorSpec("grabbing", draw_grabbing, (50.0, 52.0), "Grab", aliases=("closedhand",)),
    CursorSpec("dnd-move", partial(draw_arrow_badge, glyph_move), _ARROW_HOT, "Drag"),
    CursorSpec("dnd-copy", partial(draw_arrow_badge, glyph_copy), _ARROW_HOT, "Drag", aliases=("copy",)),
    CursorSpec("dnd-link", partial(draw_arrow_badge, glyph_link), _ARROW_HOT, "Drag", aliases=("alias",)),
    # ---- state ----
    CursorSpec("not-allowed", draw_not_allowed, _C, "State",
               aliases=("forbidden", "crossed_circle", "circle", "dnd-none")),
    CursorSpec("no-drop", partial(draw_arrow_badge, glyph_no_drop), _ARROW_HOT, "State", aliases=("dnd-no-drop",)),
    CursorSpec("help", partial(draw_arrow_badge, glyph_help), _ARROW_HOT, "State",
               aliases=("question_arrow", "whats_this", "left_ptr_help")),
    CursorSpec("context-menu", partial(draw_arrow_badge, glyph_menu), _ARROW_HOT, "State"),
    # ---- loading (animated) ----
    CursorSpec("wait", draw_wait, _C, "Loading", frames=12, delay_ms=80, aliases=("watch",)),
    CursorSpec("progress", partial(draw_arrow_badge, glyph_progress), _ARROW_HOT, "Loading",
               frames=12, delay_ms=80, aliases=("left_ptr_watch", "half-busy")),
    # ---- zoom ----
    CursorSpec("zoom-in", partial(draw_zoom, plus=True), (42.0, 42.0), "Zoom", aliases=("zoom_in",)),
    CursorSpec("zoom-out", partial(draw_zoom, plus=False), (42.0, 42.0), "Zoom", aliases=("zoom_out",)),
]

CURSORS: dict[str, CursorSpec] = {spec.name: spec for spec in _SPECS}

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
