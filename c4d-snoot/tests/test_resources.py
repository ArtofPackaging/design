"""Checks on the (minimal) description resource files."""

import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "snoot", "res")


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as handle:
        return handle.read()


class ResourceTest(unittest.TestCase):
    def test_minimal_description(self):
        res = read("description", "Osnoot.res")
        self.assertRegex(res, r"CONTAINER Osnoot\s*\{\s*NAME Osnoot;\s*INCLUDE Obase;\s*\}")
        # No comments or parameters: the Snoot tab is built in code.
        self.assertNotIn("//", res)
        self.assertNotIn("SNOOT_", res)

    def test_name_string(self):
        strings = read("strings_en-US", "description", "Osnoot.str")
        self.assertRegex(strings, r'STRINGTABLE Osnoot\s*\{\s*Osnoot "Snoot";\s*\}')

    def test_header_is_valid_enum(self):
        header = read("description", "Osnoot.h")
        self.assertIn("enum", header)
        self.assertRegex(header, r"\w+\s*=\s*0")

    def test_balanced_braces(self):
        for parts in (("description", "Osnoot.res"), ("description", "Osnoot.h"),
                      ("strings_en-US", "description", "Osnoot.str"),
                      ("strings_en-US", "c4d_strings.str"), ("c4d_symbols.h",)):
            text = read(*parts)
            self.assertEqual(text.count("{"), text.count("}"), parts)


if __name__ == "__main__":
    unittest.main()
