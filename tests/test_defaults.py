"""Default theme selection and install/uninstall isolation (no desktop required)."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import generate
import palettes


class DefaultsTest(unittest.TestCase):
    def test_default_colours_and_names(self):
        themes = generate.select_themes(generate.build_parser().parse_args([]))
        self.assertEqual([(t.name, t.base, t.accent) for t in themes], [
            ("Haku-Dark", "#111111", "#d0d0d0"),
            ("Haku-Light", "#f5f5f5", "#000000"),
        ])
        self.assertEqual(palettes.make_theme(), themes[0])
        for style, theme in zip(palettes.STYLE_NAMES, themes):
            args = generate.build_parser().parse_args(["--style", style])
            self.assertEqual(generate.select_themes(args), [theme])

    def test_optional_accents_and_custom_names(self):
        parser = generate.build_parser()
        blue = generate.select_themes(parser.parse_args(["--palette", "blue"]))
        self.assertEqual([(t.name, t.accent) for t in blue], [
            ("Haku-Blue", "#89b4fa"), ("Haku-Blue-Light", "#1e66f5"),
        ])
        custom = generate.select_themes(parser.parse_args(["--accent", "#abc", "--name", "Haku-Test"]))
        self.assertEqual([t.name for t in custom], ["Haku-Test", "Haku-Test-Light"])
        self.assertTrue(all(t.accent == "#aabbcc" for t in custom))
        self.assertEqual(len(generate.select_themes(parser.parse_args(["--all"]))),
                         2 * len(palettes.PALETTE_KEYS))

    def test_build_script_requires_explicit_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "python-stub"
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            stub.chmod(0o755)
            for args, flags in [([], []), (["all"], ["--all"]),
                                (["blue"], ["--palette", "blue"])]:
                with self.subTest(args=args):
                    result = subprocess.run([str(ROOT / "scripts/build.sh"), *args],
                                            env={**os.environ, "PYTHON": str(stub)},
                                            check=True, capture_output=True, text=True)
                    self.assertEqual(result.stdout.splitlines()[1:], flags)

    def test_install_and_uninstall_selectors(self):
        defaults = {"Haku-Dark", "Haku-Light"}
        extras = {"Haku-Blue", "Haku-Blue-Light"}
        for args, expected in [([], defaults), (["dark"], {"Haku-Dark"}),
                               (["light"], {"Haku-Light"}), (["blue"], extras),
                               (["blue-light"], {"Haku-Blue-Light"}),
                               (["Haku-Blue"], {"Haku-Blue"}),
                               (["all"], defaults | extras)]:
            with self.subTest(args=args), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                scripts = root / "scripts"
                scripts.mkdir()
                for name in ("install.sh", "uninstall.sh"):
                    shutil.copy2(ROOT / "scripts" / name, scripts / name)
                for name in defaults | extras:
                    theme = root / "dist" / name
                    (theme / "cursors").mkdir(parents=True)
                    (theme / "index.theme").write_text("[Icon Theme]\n")
                    (theme / "cursors/left_ptr").write_bytes(b"fixture")
                    (theme / "cursors/default").symlink_to("left_ptr")
                env = {**os.environ, "HOME": str(root / "home"),
                       "XDG_DATA_HOME": str(root / "xdg")}
                subprocess.run([str(scripts / "install.sh"), "all"], env=env,
                               check=True, capture_output=True)
                subprocess.run([str(scripts / "uninstall.sh"), *args], env=env,
                               check=True, capture_output=True)
                dest = root / "home/.icons"
                self.assertEqual({p.name for p in dest.iterdir()}, (defaults | extras) - expected)
                shutil.rmtree(dest)
                subprocess.run([str(scripts / "install.sh"), *args], env=env,
                               check=True, capture_output=True)
                self.assertEqual({p.name for p in dest.iterdir()}, expected)
                self.assertTrue(all((dest / name / "cursors/default").is_symlink() for name in expected))
                self.assertFalse((root / "xdg").exists())


if __name__ == "__main__":
    unittest.main()
