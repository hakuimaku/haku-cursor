"""Colour configuration: base / outline defaults and accent presets (config/palettes.json)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "palettes.json"

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

    name: str          # directory / theme id, e.g. "Haku-Blue"
    base: str          # silhouette colour
    accent: str        # small accents only
    outline: str       # thin light outline that keeps the cursor visible on dark backgrounds
    comment: str = ""

    @property
    def display_name(self) -> str:
        return self.name.replace("-", " ")


def load_config(path: Path = CONFIG_FILE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load() -> tuple[dict, dict[str, str]]:
    cfg = load_config()
    defaults = {"base": normalize_hex(cfg["base"]), "outline": normalize_hex(cfg["outline"]),
                "prefix": cfg.get("prefix", "Haku")}
    accents = {key: normalize_hex(val) for key, val in cfg["accents"].items()}
    return defaults, accents


DEFAULTS, PALETTES = _load()   # PALETTES = {"blue": "#89b4fa", ...}


def make_theme(
    palette: str | None = "blue",
    *,
    name: str | None = None,
    accent: str | None = None,
    base: str | None = None,
    outline: str | None = None,
    comment: str | None = None,
) -> Theme:
    """Build a theme from a preset, optionally overriding any colour (custom accent)."""
    key = (palette or "blue").lower()
    if key not in PALETTES:
        raise KeyError(f"unknown palette {palette!r}; available: {', '.join(PALETTES)}")
    accent_hex = normalize_hex(accent) if accent else PALETTES[key]
    if name:
        theme_name = name
    elif accent:
        theme_name = f"{DEFAULTS['prefix']}-{accent_hex.lstrip('#')}"
    else:
        theme_name = f"{DEFAULTS['prefix']}-{key.capitalize()}"
    if comment is None:
        label = accent_hex if accent else key
        comment = f"Minimal black cursor theme with {label} accent"
    return Theme(
        name=theme_name,
        base=normalize_hex(base) if base else DEFAULTS["base"],
        accent=accent_hex,
        outline=normalize_hex(outline) if outline else DEFAULTS["outline"],
        comment=comment,
    )


def all_preset_themes() -> list[Theme]:
    return [make_theme(key) for key in PALETTES]
