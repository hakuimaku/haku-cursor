# Haku Cursor — geometry (Python) -> SVG -> PNG -> xcursorgen -> XCursor themes
#
#   make                  build default Haku-Dark + Haku-Light
#   make blue             Haku-Blue and Haku-Blue-Light   (blue cyan green purple pink red orange yellow)
#   make light | dark     default light style only | dark style only
#   make blue STYLE=light only Haku-Blue-Light              (STYLE=dark|light|both, default both)
#   make ANIM=loading     only wait/progress animate        (ANIM=all|loading|none, default all)
#   make SIZES=extended   16 20 24 28 32 40 48 56 64 72 96  (default: 24 32 48 64 96)
#   make preview          generated/preview*.png + animations*.png
#   make verify           structural + two-colour checks on everything in dist/
#   make install          install Haku-Dark + Haku-Light to ~/.icons/
#   make install THEME=blue         (installs Haku-Blue and Haku-Blue-Light; THEME=blue-light for one)
#   make uninstall [THEME=blue]
#   make clean

PYTHON  ?= python3
THEME   ?= default
SIZES   ?= default
STYLE   ?= both
ANIM    ?= all
PRESETS := $(shell $(PYTHON) -c "import json;print(*json.load(open('config/palettes.json'))['accents']['dark'])")
GEN      = $(PYTHON) src/generate.py --sizes $(SIZES) --animations $(ANIM)

.PHONY: all light dark $(PRESETS) preview verify install uninstall clean help

all:
	$(GEN) --style $(STYLE)

light:
	$(GEN) --style light

dark:
	$(GEN) --style dark

$(PRESETS):
	$(GEN) --palette $@ --style $(STYLE)

preview:
	$(PYTHON) src/generate.py --preview

verify:
	$(PYTHON) src/verify.py

install:
	./scripts/install.sh $(THEME)

uninstall:
	./scripts/uninstall.sh $(THEME)

clean:
	./scripts/clean.sh

help:
	@sed -n '2,17p' Makefile
