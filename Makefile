# Haku Cursor — geometry (Python) -> SVG -> PNG -> xcursorgen -> XCursor themes
#
#   make                  build every accent theme into dist/
#   make blue             build only Haku-Blue   (blue cyan green purple pink red orange yellow)
#   make preview          generated/preview.svg + preview.png (all cursors, dark + light panel)
#   make verify           structural checks on everything in dist/
#   make install          install all built themes to ~/.local/share/icons
#   make install THEME=blue
#   make uninstall [THEME=blue]
#   make clean

PYTHON  ?= python3
THEME   ?= all
SIZES   ?= default
PRESETS := $(shell $(PYTHON) -c "import json;print(*json.load(open('config/palettes.json'))['accents'])")

.PHONY: all $(PRESETS) preview verify install uninstall clean help

all:
	$(PYTHON) src/generate.py --all --sizes $(SIZES)

$(PRESETS):
	$(PYTHON) src/generate.py --palette $@ --sizes $(SIZES)

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
	@sed -n '2,12p' Makefile
