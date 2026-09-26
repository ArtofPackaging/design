import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "snoot"))

import fake_c4d  # noqa: E402
from fake_c4d import FakeDoc, FakeNode  # noqa: E402

SNOOT = 1000001


def load():
    c4d = fake_c4d.install()
    from snootlib import actions, ids
    return c4d, actions, ids


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.actions, self.ids = load()

    def rig(self):
        light = FakeNode(5102, name="Key")
        snoot = light.add_child(FakeNode(SNOOT, name="Snoot"))
        bare = FakeNode(5102, name="Fill")
        return light, snoot, bare

    def test_selecting_the_light_edits_its_snoot(self):
        light, snoot, _ = self.rig()
        snoots, bare = self.actions.selection(FakeDoc(active=[light]))
        self.assertEqual(snoots, [snoot])
        self.assertEqual(bare, [])

    def test_light_and_snoot_both_selected_counts_once(self):
        light, snoot, _ = self.rig()
        snoots, _ = self.actions.selection(FakeDoc(active=[light, snoot]))
        self.assertEqual(snoots, [snoot])

    def test_light_without_snoot_is_offered_for_adding(self):
        light, snoot, bare = self.rig()
        snoots, bare_lights = self.actions.selection(FakeDoc(active=[bare, light]))
        self.assertEqual(snoots, [snoot])
        self.assertEqual(bare_lights, [bare])

    def test_other_objects_ignored(self):
        snoots, bare = self.actions.selection(FakeDoc(active=[FakeNode(5100)]))
        self.assertEqual((snoots, bare), ([], []))


class SetParamsTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.actions, self.ids = load()

    def test_applies_to_all_with_one_undo_step(self):
        a, b = FakeNode(SNOOT), FakeNode(SNOOT)
        doc = FakeDoc()
        self.actions.set_params(doc, [a, b], {self.ids.SNOOT_LENGTH: 42.0})
        self.assertEqual((a[self.ids.SNOOT_LENGTH], b[self.ids.SNOOT_LENGTH]), (42.0, 42.0))
        self.assertEqual(doc.undo_log[0], "start")
        self.assertEqual(doc.undo_log[-1], "end")
        self.assertEqual(len(doc.undo_log), 4)

    def test_drag_continuation_skips_undo(self):
        a = FakeNode(SNOOT)
        doc = FakeDoc()
        self.actions.set_params(doc, [a], {self.ids.SNOOT_LENGTH: 10.0}, record_undo=False)
        self.assertEqual(a[self.ids.SNOOT_LENGTH], 10.0)
        self.assertEqual(doc.undo_log, [])


class CreateSnootTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.actions, self.ids = load()

    def test_opening_starts_with_light_shape(self):
        c4d, ids = self.c4d, self.ids
        disc = FakeNode(5102, {c4d.LIGHT_TYPE: c4d.LIGHT_TYPE_AREA,
                               c4d.LIGHT_AREADETAILS_SHAPE: c4d.LIGHT_AREADETAILS_SHAPE_DISC,
                               c4d.LIGHT_AREADETAILS_SIZEX: 50.0,
                               c4d.LIGHT_AREADETAILS_SIZEY: 50.0})
        rect = FakeNode(5102, {c4d.LIGHT_TYPE: c4d.LIGHT_TYPE_AREA,
                               c4d.LIGHT_AREADETAILS_SHAPE: c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE,
                               c4d.LIGHT_AREADETAILS_SIZEX: 35.0,
                               c4d.LIGHT_AREADETAILS_SIZEY: 26.0})
        self.assertEqual(self.actions.create_snoot(disc)[ids.SNOOT_ROUNDNESS], 1.0)
        self.assertEqual(self.actions.create_snoot(rect)[ids.SNOOT_ROUNDNESS], 0.0)

    def test_point_light_gets_manual_size(self):
        c4d, ids = self.c4d, self.ids
        spot = FakeNode(5102, {c4d.LIGHT_TYPE: c4d.LIGHT_TYPE_SPOT}, name="Spot")
        snoot = self.actions.create_snoot(spot)
        self.assertEqual(snoot[ids.SNOOT_SIZE_MODE], ids.SNOOT_SIZE_MODE_MANUAL)
        self.assertEqual(snoot[ids.SNOOT_SIZE_X], self.actions.POINT_LIGHT_SIZE)


if __name__ == "__main__":
    unittest.main()
