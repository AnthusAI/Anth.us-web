"""Every authored layout and legacy wrapper maps onto one placement look."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

import anthus_dom as dom
import support


def wrap(layout, caption=""):
    return SimpleNamespace(request=SimpleNamespace(layout=layout, caption=caption), layout=layout,
                           width=800, height=400, display_width=None, placeholder=None, inner="<img>")


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

    def test_the_projected_article_places_each_image_by_its_layout(self):
        main = support.project_fixture().main("/articles/pictured-article/")
        wrappers = re.findall(r'<div class="img (img--[a-z-]+)">', main)
        self.assertEqual(wrappers, ["img--full", "img--small", "img--inset-right"])
        self.assertIn('<p class="image-caption">Wide</p>', main)
        for place in ("full", "small", "inset-right"):  # the theme has a rule for each look it emits
            self.assertIn(f".img--{place}", Path(dom.__file__).parent.joinpath("css", "site-theme.css").read_text())

    def test_the_projected_images_are_responsive_and_use_the_stored_renditions(self):
        main = support.project_fixture().main("/articles/pictured-article/")
        self.assertIn("/assets/responsive/images/wide-1400.png", main)
        self.assertIn('width="1400" height="700"', main)
        self.assertNotIn("markus-", main)  # the class vocabulary of the converted fragment is the site's own


if __name__ == "__main__":
    unittest.main()
