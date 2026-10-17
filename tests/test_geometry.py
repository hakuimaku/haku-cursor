"""Regression checks for balanced arrows and visible exterior hand animation."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cursors import CURSORS, draw_arrow, draw_pointer
from geometry import CANVAS
from palettes import make_theme
from preview import build_preview
from svg import Group, bounds, rotate, translate, walk


class GeometryTest(unittest.TestCase):
    """Check the rendered geometry rather than individual control points."""

    def test_arrow_wings_and_rounding_are_symmetric(self):
        """Both painted wings mirror exactly across the tilted arrow axis."""
        upright = rotate(22.5) @ translate(-14, -8)  # undo the drawing's tilt
        for style in ("dark", "light"):
            for shape, matrix in walk(draw_arrow(make_theme(style=style)), upright):
                points = [matrix.apply(p) for line, _ in shape.flatten() for p in line]
                for x, y in points:
                    self.assertLess(min((x + px) ** 2 + (y - py) ** 2 for px, py in points), 1e-12)

    def test_hand_animation_stays_outside_and_keeps_hand_still(self):
        """Click waves stay beside the fingertip within the hand's existing canvas."""
        theme = make_theme()  # colours do not affect bounds
        resting = draw_pointer(theme)
        hand_box = bounds(resting)  # include the accent outline
        for i in range(CURSORS["pointer"].frames):
            scene = draw_pointer(theme, i / CURSORS["pointer"].frames)
            self.assertEqual(scene.children[0].to_svg(), resting.children[0].to_svg())
            wave_box = bounds(Group(scene.children[1:]))  # include the animation stroke
            self.assertGreater(wave_box[0], 53)  # right edge of the outlined index finger
            self.assertGreaterEqual(wave_box[0], hand_box[0])
            self.assertGreaterEqual(wave_box[1], hand_box[1])
            self.assertLessEqual(wave_box[2], hand_box[2])
            self.assertLessEqual(wave_box[3], hand_box[3])

    def test_hand_matches_arrow_size(self):
        """Animation space must not shrink the hand relative to the main arrow."""
        theme = make_theme()
        hand_box = bounds(CURSORS["pointer"].draw(theme))  # resting hand after animation fitting
        arrow_box = bounds(CURSORS["left_ptr"].draw(theme))  # main cursor at the same nominal size
        self.assertGreaterEqual(hand_box[3] - hand_box[1], 0.95 * max(arrow_box[2] - arrow_box[0],
                                                                   arrow_box[3] - arrow_box[1]))

    def test_all_frames_fit_canvas(self):
        """The outline and exterior waves stay inside every cursor canvas."""
        theme = make_theme()
        for spec in CURSORS.values():
            for phase in [None] + ([i / spec.frames for i in range(spec.frames)] if spec.animated else []):
                with self.subTest(cursor=spec.name, phase=phase):
                    x0, y0, x1, y1 = bounds(spec.draw(theme, phase))
                    self.assertGreaterEqual(min(x0, y0), 0)
                    self.assertLessEqual(max(x1, y1), CANVAS)
            self.assertTrue(all(0 <= coordinate < CANVAS for coordinate in spec.hotspot))

    def test_preview_uses_cursor_frame_delays(self):
        """A 70 ms pointer frame advances at its configured time in the GIF scene."""
        theme = make_theme()
        pointer_index = 1 + 2 * list(CURSORS).index("pointer")  # panel background, then scene/marker
        first = build_preview(theme, 0)[0].children[pointer_index].to_svg()
        self.assertEqual(first, build_preview(theme, 69)[0].children[pointer_index].to_svg())
        self.assertNotEqual(first, build_preview(theme, 70)[0].children[pointer_index].to_svg())


if __name__ == "__main__":
    unittest.main()
