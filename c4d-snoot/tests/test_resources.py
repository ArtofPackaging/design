"""Checks that the description resource, strings and ids.py agree."""

import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "snoot")
sys.path.insert(0, ROOT)

from snootlib import ids  # noqa: E402


def read(*parts):
    with open(os.path.join(ROOT, *parts)) as handle:
        return handle.read()


class ResourceTest(unittest.TestCase):
    def setUp(self):
        self.header = dict(
            (name, int(value))
            for name, value in re.findall(r"^\s*(SNOOT_\w+)\s*=\s*(\d+)", read("res", "description", "Osnoot.h"), re.M))
        self.res = read("res", "description", "Osnoot.res")
        self.strings = read("res", "strings_en-US", "description", "Osnoot.str")

    def test_header_matches_ids(self):
        self.assertTrue(self.header)
        for name, value in self.header.items():
            self.assertEqual(getattr(ids, name), value, name)
        for name in dir(ids):
            if name.startswith("SNOOT_"):
                self.assertIn(name, self.header, name)

    def test_every_res_symbol_is_defined_and_named(self):
        symbols = set(re.findall(r"\b(SNOOT_\w+)\b", self.res))
        self.assertTrue(symbols)
        for name in symbols:
            self.assertIn(name, self.header, name)
            self.assertRegex(self.strings, r"\b%s\s+\"" % name, name)

    def test_param_ids_unique(self):
        params = [v for k, v in self.header.items()
                  if not re.search(r"_(MODE|RENDERER)_", k)]
        self.assertEqual(len(params), len(set(params)))

    def test_balanced_braces(self):
        for text in (self.res, self.strings):
            self.assertEqual(text.count("{"), text.count("}"))

    def test_plugin_ids_distinct(self):
        self.assertNotEqual(ids.ID_SNOOT_OBJECT, ids.ID_ADD_SNOOT_COMMAND)


if __name__ == "__main__":
    unittest.main()
