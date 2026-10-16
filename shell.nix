# nix-shell            (or `nix develop` users: wrap this in a flake devShell)
# Provides everything `make` needs; all tools are found through PATH.
{ pkgs ? import <nixpkgs> { } }:

let
  # nixpkgs >= 25.05 exposes `xcursorgen` at top level; older releases keep it under `xorg`.
  xcursorgen = pkgs.xcursorgen or pkgs.xorg.xcursorgen;
in
pkgs.mkShell {
  packages = [
    pkgs.python3
    pkgs.python3Packages.pillow   # optional: only used by the no-SVG-renderer fallback
    pkgs.gnumake
    pkgs.librsvg                  # rsvg-convert
    xcursorgen
  ];
}
