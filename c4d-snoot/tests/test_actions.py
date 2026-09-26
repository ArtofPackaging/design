import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "snoot"))

import fake_c4d  # noqa: E402
from fake_c4d import FakeNode  # noqa: E402



def load():
    c4d = fake_c4d.install()
    from snootlib import actions, ids
    return c4d, actions, ids


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
