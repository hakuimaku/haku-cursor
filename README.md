# Haku Cursor

Bộ XCursor theme tối giản, hình học, màu đen + accent nhỏ, **toàn bộ được sinh ra từ code**:

```
Python geometry → SVG → PNG (mỗi size render lại từ vector) → xcursorgen → XCursor theme
```

SVG / PNG / binary cursor đều là *generated artifacts* (không sửa tay). Muốn đổi thiết kế: sửa code trong `src/` rồi build lại.
Không dùng AI image generation, không trace hay copy asset của theme nào khác.

![preview](generated/preview.png)

## Dependency

| Cần | Vai trò | Ghi chú |
|---|---|---|
| `python3` ≥ 3.10 | generator | chỉ dùng standard library |
| `rsvg-convert` (librsvg) | SVG → PNG | thay thế: `resvg`, `inkscape` (CLI, không GUI) |
| `xcursorgen` | PNG → XCursor | |
| `make` | build | tuỳ chọn |
| `Pillow` | fallback | **chỉ** dùng khi không có renderer SVG / xcursorgen |

Mọi binary được tìm qua `PATH` (`shutil.which`), không hardcode `/usr/bin`.
Nếu thiếu `rsvg-convert`/`xcursorgen`, generator tự chuyển sang rasterizer Pillow và XCursor writer thuần Python
(in ra `note:` trên stderr). Đường chính vẫn là rsvg-convert + xcursorgen; dùng `--renderer` / `--xcursorgen` để ép.

### NixOS

```bash
nix-shell            # dùng shell.nix đi kèm
make
```

hoặc tối thiểu:

```nix
pkgs.mkShell {
  packages = with pkgs; [
    python3
    gnumake
    librsvg        # rsvg-convert
    xcursorgen     # nixpkgs >= 25.05; bản cũ hơn: xorg.xcursorgen
  ];
}
```

Dùng như package (home-manager) — `default.nix` đi kèm *chưa được test trên máy có Nix*:

```nix
home.pointerCursor = {
  package = pkgs.callPackage /path/to/haku-cursor { };
  name = "Haku-Blue";
  size = 24;
  gtk.enable = true;
};
```

## Build

```bash
make                  # tất cả theme accent → dist/Haku-*
make blue             # chỉ Haku-Blue (blue cyan green purple pink red orange yellow)
make preview          # generated/preview.svg + preview.png (tile nền tối + nền sáng, chấm đỏ = hotspot)
make verify           # kiểm tra cấu trúc XCursor, hotspot, animation, symlink
make clean
make SIZES=extended   # 16 20 24 28 32 40 48 56 64 72 96  (mặc định: 24 32 48 64 96)
```

Hoặc gọi trực tiếp:

```bash
python src/generate.py --palette blue
python src/generate.py --all
python src/generate.py --accent "#7aa2f7" --name Haku-Tokyo      # accent tuỳ chỉnh
python src/generate.py --name Haku-Mono --accent "#d0d0d0" --base "#000000"
python src/generate.py --sizes 24,32,48 --palette green
python src/generate.py --list
```

## Install

Cài vào `~/.local/share/icons` (không cần root):

```bash
make install THEME=blue        # hoặc ./scripts/install.sh blue
make install                   # tất cả theme đã build
make uninstall THEME=blue
```

## Dùng thử

GTK / GNOME:

```bash
gsettings set org.gnome.desktop.interface cursor-theme 'Haku-Blue'
gsettings set org.gnome.desktop.interface cursor-size 24
```

Thử nhanh một app, không đổi cấu hình hệ thống:

```bash
XCURSOR_THEME=Haku-Blue XCURSOR_SIZE=24 gtk3-demo     # hoặc bất kỳ app nào
```

Compositor Wayland (đặt cả biến môi trường để XWayland/Qt/Electron đồng bộ):

| WM | Cấu hình |
|---|---|
| Hyprland | `env = XCURSOR_THEME,Haku-Blue` · `env = XCURSOR_SIZE,24` · `exec-once = hyprctl setcursor Haku-Blue 24` |
| Niri | `cursor { xcursor-theme "Haku-Blue"; xcursor-size 24 }` (trong `config.kdl`) |
| Sway | `seat seat0 xcursor_theme Haku-Blue 24` |
| GTK thuần | `~/.config/gtk-3.0/settings.ini` & `gtk-4.0`: `gtk-cursor-theme-name=Haku-Blue`, `gtk-cursor-theme-size=24` |
| X11 | `~/.Xresources`: `Xcursor.theme: Haku-Blue` / `Xcursor.size: 24` |

Flatpak cần thấy thư mục icon: `flatpak override --user --filesystem=~/.local/share/icons:ro`.
Hyprland: `hyprcursor` là định dạng khác; theme này là XCursor và Hyprland tự fallback về XCursor.

## Design system (`src/geometry.py`)

Canvas cố định **100 × 100**, mọi cursor vẽ bằng toạ độ chuẩn hoá rồi render lại từ SVG ở từng size (không scale PNG).
Hotspot khai báo một chỗ duy nhất (`CURSORS` trong `src/cursors.py`), được quy đổi sang pixel: `floor(h · size/100)`.

| Token | Giá trị | Ý nghĩa |
|---|---|---|
| `base` | `#111111` | silhouette (`config/palettes.json`) |
| `outline` | `#f2f2f2` | viền sáng mỏng `OUTLINE = 2.2` ôm cả silhouette, để cursor đen vẫn thấy trên nền tối |
| `accent` | preset / tuỳ chỉnh | chỉ **một** chi tiết nhỏ mỗi cursor |
| `STROKE_MAIN` / `STROKE_MINOR` | 6 / 3 | nét chính / nét phụ, luôn round cap + round join |
| `CORNER_RADIUS` | 3.4 | bo góc polygon |

Quy ước accent: đường chèn ở đuôi arrow, cổ tay bàn tay, "caret" của I-beam, chấm ở tâm cho crosshair/move/resize/cell,
glyph trong badge (copy/link/help/menu…), cung xoay của spinner, gạch chéo của not-allowed, dấu +/− trong kính lúp.

## Cursor đã có (32 asset + 68 alias, symlink — không nhân đôi binary)

| Nhóm | Asset | Alias chính |
|---|---|---|
| Normal | `left_ptr` | `default` `arrow` `top_left_arrow` |
| Link | `pointer` | `hand` `hand1` `hand2` `pointing_hand` `link` |
| Text | `text` `vertical-text` | `xterm` `ibeam` |
| Precision | `crosshair` `cell` | `cross` `tcross` `plus` |
| Move | `move` | `all-scroll` `fleur` `size_all` |
| Resize | `n/s/e/w-resize` `ne/nw/se/sw-resize` `ns/ew/nesw/nwse-resize` | `top_side` `bottom_left_corner` `sb_h_double_arrow` `col-resize` `fd_double_arrow` … |
| Drag | `grab` `grabbing` `dnd-move` `dnd-copy` `dnd-link` | `openhand` `closedhand` `copy` `alias` |
| State | `not-allowed` `no-drop` `help` `context-menu` | `forbidden` `crossed_circle` `question_arrow` |
| Loading (12 frame, 80 ms) | `wait` `progress` | `watch` · `left_ptr_watch` `half-busy` |
| Zoom | `zoom-in` `zoom-out` | `zoom_in` `zoom_out` |

Alias hash 32 ký tự (X11 cũ) nằm ở `HASH_ALIASES` trong `src/cursors.py`; chỉ gồm các mapping đã xác nhận từ tài liệu công khai
(Arch Wiki *Cursor themes*, thread Gentoo về symlink xcursor). Toolkit hiện đại (GTK3/4, Qt5/6, Firefox, Chromium) dùng tên CSS nên không cần chúng.

## Cấu trúc

```
src/svg.py        scene graph + serialiser SVG (transform, group, path, arc, text)
src/geometry.py   design tokens, rounded_polygon, halo/silhouette, arrowhead, badge, spinner
src/cursors.py    hình vẽ từng cursor + registry (hotspot, frames, alias)
src/palettes.py   đọc config/palettes.json, Theme, accent tuỳ chỉnh
src/generate.py   CLI + pipeline (SVG → PNG → xcursorgen → symlink → index.theme)
src/raster.py     rasterizer Pillow dự phòng       src/xcursor.py  reader/writer XCursor dự phòng
src/preview.py    sheet preview                    src/verify.py   kiểm tra theme đã build
config/palettes.json   base / outline / accent presets
generated/<Theme>/{svg,png}   artifact trung gian     build/<Theme>/*.conf   config xcursorgen
dist/<Theme>/                 theme hoàn chỉnh
```

Thêm cursor mới: viết `draw_xxx(theme, t) -> Group` trong `cursors.py`, thêm một `CursorSpec(...)` (tên, hotspot, alias). Xong.
Thêm màu: thêm một dòng vào `config/palettes.json` (Makefile tự nhận target mới).

## Hạn chế / việc còn lại

- Chưa test trên desktop thật; môi trường phát triển không có `rsvg-convert`/`xcursorgen`. Đường Pillow + writer thuần Python đã được chạy và kiểm tra bằng `make verify`
  (header khớp file Adwaita thật); đường rsvg-convert + xcursorgen chỉ mới kiểm tra việc truyền tham số bằng stub. Hãy chạy `make verify` và xem `make preview` sau lần build đầu trên máy bạn.
- Ở 24 px, nét mảnh + viền sáng khá sát nhau; hinting theo pixel grid chưa có.
- Chưa có: `right_ptr`, `pencil`, `color-picker`, `col-resize`/`row-resize` riêng (hiện alias của `ew/ns-resize`), `.cur` cho Windows/Wine.
- Chưa có định dạng hyprcursor native.

## License

MIT.
