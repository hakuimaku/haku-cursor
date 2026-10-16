"""Preview sheet (grid of every cursor on a dark and a light panel), also generated purely by code."""

from __future__ import annotations

from cursors import CURSORS
from geometry import CANVAS
from palettes import Theme
from svg import Circle, Group, Line, Rect, Text, fill, scale, stroke, translate

CELL = 96.0       # cursor drawn at 0.96x its canvas
PAD = 14.0
LABEL_H = 18.0
COLUMNS = 8
DARK_BG, LIGHT_BG = "#1e1e2e", "#eceff4"
DARK_LABEL, LIGHT_LABEL = "#9399b2", "#5c6370"


def _panel(theme: Theme, x0: float, bg: str, label: str, columns: int, rows: int, tile_w: float, tile_h: float) -> list:
    out: list = [Rect(x0, 0, columns * tile_w, rows * tile_h, 0, fill(bg))]
    k = CELL / CANVAS
    for i, spec in enumerate(CURSORS.values()):
        col, row = i % columns, i // columns
        ox, oy = x0 + col * tile_w + PAD, row * tile_h + PAD
        phase = 0.25 if spec.animated else 0.0
        scene = Group([spec.draw(theme, phase)], translate(ox, oy) @ scale(k))
        hx, hy = ox + spec.hotspot[0] * k, oy + spec.hotspot[1] * k
        marker = Group([Circle(hx, hy, 2.4, stroke("#ff3b3b", 0.9)), Circle(hx, hy, 0.5, fill("#ff3b3b"))])
        text = Text(ox + CELL / 2, oy + CELL + 11, spec.name, 9.0, "middle", fill(label))
        out += [scene, marker, text]
    return out


def build_preview(theme: Theme) -> tuple[Group, float, float]:
    """Return ``(scene, width, height)``; both panels share the same grid."""
    columns = COLUMNS
    rows = -(-len(CURSORS) // columns)
    tile_w, tile_h = CELL + 2 * PAD, CELL + 2 * PAD + LABEL_H - 10
    panel_w = columns * tile_w
    root = Group()
    root.add(*_panel(theme, 0, DARK_BG, DARK_LABEL, columns, rows, tile_w, tile_h))
    root.add(*_panel(theme, panel_w, LIGHT_BG, LIGHT_LABEL, columns, rows, tile_w, tile_h))
    return root, 2 * panel_w, rows * tile_h
