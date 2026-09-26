import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "snoot"))

import fake_c4d  # noqa: E402
from fake_c4d import FakeDescription  # noqa: E402


def load():
    c4d = fake_c4d.install()
    from snootlib import ids, ui
    return c4d, ids, ui


def param_ids(ids):
    """Every Snoot parameter and group ID (cycle values excluded)."""
    return {name: getattr(ids, name) for name in dir(ids)
            if name.startswith("SNOOT_") and getattr(ids, name) >= 10000}


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.ids, self.ui = load()

    def test_every_parameter_appears_once(self):
        in_layout = [entry[1] for entry in self.ui.LAYOUT]
        self.assertEqual(len(in_layout), len(set(in_layout)))
        expected = set(param_ids(self.ids).values()) - {self.ids.SNOOT_GROUP_MAIN}
        self.assertEqual(set(in_layout), expected)

    def test_parents_are_earlier_groups(self):
        groups = {self.ui.ROOT}
        for kind, param_id, parent, label, _options in self.ui.LAYOUT:
            self.assertIn(parent, groups, label)
            self.assertTrue(label)
            if kind == "group":
                groups.add(param_id)

    def test_cycles_cover_their_values(self):
        items = {entry[1]: [value for value, _ in entry[4]["items"]]
                 for entry in self.ui.LAYOUT if entry[0] == "cycle"}
        ids = self.ids
        self.assertEqual(items[ids.SNOOT_SIZE_MODE],
                         [ids.SNOOT_SIZE_MODE_LIGHT, ids.SNOOT_SIZE_MODE_MANUAL])
        self.assertEqual(sorted(items[ids.SNOOT_RENDERER]), [0, 1, 2, 3, 4])

    def test_param_ids_unique(self):
        values = list(param_ids(self.ids).values())
        self.assertEqual(len(values), len(set(values)))

    def test_plugin_ids(self):
        ids = self.ids
        self.assertNotEqual(ids.ID_SNOOT_OBJECT, ids.ID_ADD_SNOOT_COMMAND)
        # 1000001 is taken by the Megapixels plugin in the same install.
        self.assertNotIn(1000001, (ids.ID_SNOOT_OBJECT, ids.ID_ADD_SNOOT_COMMAND))
        for plugin_id in (ids.ID_SNOOT_OBJECT, ids.ID_ADD_SNOOT_COMMAND):
            self.assertTrue(1000001 <= plugin_id <= 1000010)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.ids, self.ui = load()

    def test_builds_into_renamed_object_tab(self):
        c4d, ids = self.c4d, self.ids
        description = FakeDescription()
        self.ui.build(description, "Storm 80: Octane area light 35 x 26 cm")
        tab = description.by_id[(c4d.ID_OBJECTPROPERTIES,)]
        self.assertEqual(tab[c4d.DESC_NAME], "Snoot")
        self.assertEqual(len(description.entries), len(self.ui.LAYOUT))

        by_id = {entry[0][0].id: entry for entry in description.entries}
        # Status line carries the light text.
        self.assertEqual(by_id[ids.SNOOT_INFO][1][c4d.DESC_NAME],
                         "Storm 80: Octane area light 35 x 26 cm")
        # Length sits in the Opening section, which sits in the tab.
        self.assertEqual(by_id[ids.SNOOT_LENGTH][2][0].id, ids.SNOOT_GROUP_OPENING)
        self.assertEqual(by_id[ids.SNOOT_GROUP_OPENING][2][0].id, c4d.ID_OBJECTPROPERTIES)
        # Percent sliders use fractions.
        opening = by_id[ids.SNOOT_OPENING_X][1]
        self.assertEqual(opening[c4d.DESC_UNIT], c4d.DESC_UNIT_PERCENT)
        self.assertEqual((opening[c4d.DESC_MIN], opening[c4d.DESC_MAX]), (0.01, 10.0))
        # Cycle entries.
        cycle = by_id[ids.SNOOT_SIZE_MODE][1][c4d.DESC_CYCLE]
        self.assertEqual(cycle[ids.SNOOT_SIZE_MODE_MANUAL], "Manual")
        # Light Size starts collapsed, Opening open.
        self.assertEqual(by_id[ids.SNOOT_GROUP_SIZE][1][c4d.DESC_DEFAULT], 0)
        self.assertEqual(by_id[ids.SNOOT_GROUP_OPENING][1][c4d.DESC_DEFAULT], 1)

    def test_creates_tab_when_missing(self):
        c4d = self.c4d
        description = FakeDescription(with_object_tab=False)
        self.ui.build(description, "Light: -")
        first_id, first_bc, parent = description.entries[0]
        self.assertEqual(first_id[0].id, c4d.ID_OBJECTPROPERTIES)
        self.assertEqual(first_bc[c4d.DESC_NAME], "Snoot")
        self.assertIs(parent, c4d.DESCID_ROOT)
        self.assertEqual(len(description.entries), len(self.ui.LAYOUT) + 1)


if __name__ == "__main__":
    unittest.main()
