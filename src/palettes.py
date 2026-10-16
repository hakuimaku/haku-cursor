"""Colour configuration (config/palettes.json).

A theme has exactly two colours:

* ``base``   the fill of every shape (near-black in the dark style, near-white in the light style)
* ``accent`` the border and every glyph

The default accents are grey-white for dark and black for light. Optional colour presets
use pastels for dark and saturated variants for light.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "palettes.json"
STYLE_NAMES = ("dark", "light")

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_hex(value: str) -> str:
    """Accept ``#rrggbb`` / ``rrggbb`` / ``#rgb`` and return lowercase ``#rrggbb``."""
    v = value.strip().lstrip("#").lower()
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    color = "#" + v
    if not _HEX.match(color):
        raise ValueError(f"invalid colour {value!r}; expected hex like #89b4fa")
    return color


@dataclass(frozen=True)
class Theme:
    """Everything the cursor drawing code needs to know about colour."""

    name: str          # directory / theme id, e.g. "Haku-Blue-Light"
    style: str         # "dark" | "light"
    base: str          # fill colour
    accent: str        # border + glyph colour
    comment: str = ""

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ")


def _load() -> tuple[str, dict[str, dict], dict[str, dict[str, str]]]:
    with open(CONFIG_FILE, encoding="utf-8") as fh:
        cfg = json.load(fh)
    styles = {k: {"suffix": v.get("suffix", ""), "base": normalize_hex(v["base"])}
              for k, v in cfg["styles"].items()}
    accents = {style: {key: normalize_hex(val) for key, val in table.items()}
               for style, table in cfg["accents"].items()}
    if set(styles) != set(STYLE_NAMES) or set(accents) != set(STYLE_NAMES):
        raise ValueError("palettes.json must define exactly the styles: " + ", ".join(STYLE_NAMES))
    if set(accents["dark"]) != set(accents["light"]):
        raise ValueError("palettes.json: dark and light accents must define the same keys")
    return cfg.get("prefix", "Haku"), styles, accents


PREFIX, STYLES, PALETTES = _load()      # PALETTES = {"dark": {"blue": "#89b4fa", ...}, "light": {...}}
PALETTE_KEYS = list(PALETTES["dark"])


def make_theme(
    palette: str | None = "default",
    style: str = "dark",
    *,
    name: str | None = None,
    accent: str | None = None,
    base: str | None = None,
    comment: str | None = None,
) -> Theme:
    """Build a theme from a preset, optionally overriding colours (custom accent / base).

    ``name`` is the theme name *without* style suffix; the light style appends ``-Light``.
    """
    key = (palette or "default").lower()
    if style not in STYLES:
        raise KeyError(f"unknown style {style!r}; available: {', '.join(STYLES)}")
    if key not in PALETTES[style]:
        raise KeyError(f"unknown palette {palette!r}; available: {', '.join(PALETTE_KEYS)}")
    accent_hex = normalize_hex(accent) if accent else PALETTES[style][key]
    if name:
        stem = name
    elif accent:
        stem = f"{PREFIX}-{accent_hex.lstrip('#')}"
    elif key == "default":
        stem = f"{PREFIX}-Dark" if style == "dark" else PREFIX
    else:
        stem = f"{PREFIX}-{key.capitalize()}"
    label = accent_hex if accent else key
    return Theme(
        name=stem + STYLES[style]["suffix"],
        style=style,
        base=normalize_hex(base) if base else STYLES[style]["base"],
        accent=accent_hex,
        comment=comment or f"Minimal {style} cursor theme with a {label} accent border",
    )


def all_preset_themes(styles: tuple[str, ...] = STYLE_NAMES) -> list[Theme]:
    return [make_theme(key, style) for style in styles for key in PALETTE_KEYS]
