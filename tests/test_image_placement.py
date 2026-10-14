"""Every authored layout and legacy wrapper maps onto one placement look."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

try:
    import build_via_papyrus  # noqa: F401  (puts Papyrus on sys.path)
    import anthus_dom as dom
    IMPORT_ERROR = None
except (ImportError, SystemExit) as error:
    dom = None
    IMPORT_ERROR = error


def wrap(layout, caption=""):
    return SimpleNamespace(request=SimpleNamespace(layout=layout, caption=caption), layout=layout,
                           width=800, height=400, display_width=None, placeholder=None, inner="<img>")


@unittest.skipIf(dom is None, f"build module unavailable: {IMPORT_ERROR}")
class ImagePlacement(unittest.TestCase):
    def test_layout_names(self):
        for layout, place in (("full", "full"), ("center-small-image", "small"), ("centered", "medium"),
                              ("center-full-image", "medium"), ("right", "inset-right"),
                              ("right-aligned", "inset-right")):
            self.assertIn(f'class="img img--{place}"', dom.anthus_image_wrap(wrap(layout)), layout)

    def test_wrappers_map_onto_the_same_looks(self):
        cases = {"full@figure-cfi": "full", "center-small-image@p-cfi": "small", "full@div-csi": "small",
                 "right-aligned@float-260": "inset-right", "full@box-26rem": "medium"}
        for layout, place in cases.items():
            self.assertIn(f"img--{place}", dom.anthus_image_wrap(wrap(layout)), layout)

    def test_every_wrapper_key_is_mapped(self):
        self.assertEqual(set(dom.IMAGE_WRAPPERS), set(dom.WRAPPER_PLACEMENT))


if __name__ == "__main__":
    unittest.main()
