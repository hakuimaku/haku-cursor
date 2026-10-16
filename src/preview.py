"""Preview sheets, generated purely by code.

* ``build_preview``   grid of every cursor on a dark and a light panel (red ring = hotspot)
* ``build_filmstrip`` one row per animated cursor showing every frame, on dark and light panels
"""

from __future__ import annotations

from cursors import CURSORS
from geometry import CANVAS
from palettes import Theme
from svg import Circle, Group, Rect, Text, fill, scale, stroke, translate

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
        phase = 0.3 if spec.group == "Loading" else None     # rest frame, except spinners
        scene = Group([spec.draw(theme, phase)], translate(ox, oy) @ scale(k))
        hx, hy = ox + spec.hotspot[0] * k, oy + spec.hotspot[1] * k
        marker = Group([Circle(hx, hy, 2.4, stroke("#ff3b3b", 0.9)), Circle(hx, hy, 0.5, fill("#ff3b3b"))])
        name = spec.name + (" *" if spec.animated else "")
        out += [scene, marker, Text(ox + CELL / 2, oy + CELL + 11, name, 9.0, "middle", fill(label))]
    return out


def build_preview(theme: Theme) -> tuple[Group, float, float]:
    """Return ``(scene, width, height)``; both panels share the same grid. ``*`` = animated."""
    columns = COLUMNS
    rows = -(-len(CURSORS) // columns)
    tile_w, tile_h = CELL + 2 * PAD, CELL + 2 * PAD + LABEL_H - 10
    panel_w = columns * tile_w
    root = Group()
    root.add(*_panel(theme, 0, DARK_BG, DARK_LABEL, columns, rows, tile_w, tile_h))
    root.add(*_panel(theme, panel_w, LIGHT_BG, LIGHT_LABEL, columns, rows, tile_w, tile_h))
    return root, 2 * panel_w, rows * tile_h


FRAME = 56.0      # filmstrip frame size
LABEL_W = 110.0
MAX_FRAMES = 16


def build_filmstrip(theme: Theme) -> tuple[Group, float, float]:
    """Every frame of every animated cursor, in a row each (dark panel on the left, light on the right)."""
    animated = [s for s in CURSORS.values() if s.animated]
    row_h = FRAME + 8
    strip_w = MAX_FRAMES * FRAME
    panel_w = LABEL_W + strip_w + 12
    k = FRAME / CANVAS
    root = Group()
    for x0, bg, label_color in ((0, DARK_BG, DARK_LABEL), (panel_w, LIGHT_BG, LIGHT_LABEL)):
        root.add(Rect(x0, 0, panel_w, len(animated) * row_h + 8, 0, fill(bg)))
        for r, spec in enumerate(animated):
            y = 8 + r * row_h
            root.add(Text(x0 + 8, y + FRAME / 2 + 3, f"{spec.name} ({spec.frames}f)", 9.0, "start", fill(label_color)))
            for i in range(spec.frames):
                scene = spec.draw(theme, i / spec.frames)
                root.add(Group([scene], translate(x0 + LABEL_W + i * FRAME, y) @ scale(k)))
    return root, 2 * panel_w, len(animated) * row_h + 8
