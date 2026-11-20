"""A pressed call to action keeps the link under the pointer, so one click always navigates.

Moving a link with `:active { transform }` shifts it off a pointer resting near its edge between
mousedown and mouseup; the click is then dispatched to the parent and the link does not navigate
until it is clicked again. The press effect belongs on the button face (`> span`), not the link.
"""
import re
import unittest
from pathlib import Path

CSS_DIRECTORY = Path(__file__).resolve().parents[1] / "web" / "css"
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def rules():
    for sheet in sorted(CSS_DIRECTORY.glob("*.css")):
        text = re.sub(r"/\*.*?\*/", "", sheet.read_text(encoding="utf-8"), flags=re.S)
        for selectors, body in RULE.findall(text):
            for selector in selectors.split(","):
                yield sheet.name, selector.strip(), body


def moves(body):
    match = re.search(r"(?:^|;)\s*transform\s*:\s*([^;]+)", body)
    return bool(match) and match.group(1).strip() != "none"


class ButtonPressTests(unittest.TestCase):
    def test_no_active_rule_moves_the_link_itself(self):
        offenders = [
            f"{sheet}: {selector}"
            for sheet, selector, body in rules()
            if re.search(r":active$", selector) and moves(body)
        ]
        self.assertEqual(offenders, [])

    def test_the_press_still_moves_the_button_face(self):
        pressed = {selector for _, selector, body in rules() if moves(body)}
        self.assertIn(".btn:active > span", pressed)
        self.assertIn(".btn--ghost:active > span", pressed)


if __name__ == "__main__":
    unittest.main()
