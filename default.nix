# Package the themes for NixOS / home-manager (not tested on a real Nix install yet).
#
#   home.pointerCursor = {
#     package = pkgs.callPackage /path/to/haku-cursor { };
#     name = "Haku-Dark";  # or "Haku-Light"
#     size = 24;
#     gtk.enable = true;
#   };
{ lib, stdenvNoCC, python3, librsvg, gnumake, xcursorgen ? null, xorg ? null }:

stdenvNoCC.mkDerivation {
  pname = "haku-cursor";
  version = "0.1.0";
  src = lib.cleanSource ./.;

  nativeBuildInputs = [ python3 librsvg gnumake (if xcursorgen != null then xcursorgen else xorg.xcursorgen) ];

  buildPhase = ''
    runHook preBuild
    make all
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    mkdir -p $out/share/icons
    cp -a dist/Haku-* $out/share/icons/
    runHook postInstall
  '';

  meta = {
    description = "Minimal black XCursor theme with configurable accent colour, generated from code";
    license = lib.licenses.mit;
    platforms = lib.platforms.linux;
  };
}
