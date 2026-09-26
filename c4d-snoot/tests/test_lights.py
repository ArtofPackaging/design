import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "snoot"))

import fake_c4d  # noqa: E402
from fake_c4d import DescID, DescLevel, FakeDoc, FakeNode  # noqa: E402

REDSHIFT_SYMBOLS = {
    "REDSHIFT_LIGHT_TYPE": 5000,
    "REDSHIFT_LIGHT_TYPE_POINT": 0,
    "REDSHIFT_LIGHT_TYPE_PHYSICAL_AREA": 3,
    "REDSHIFT_LIGHT_PHYSICAL_AREA_GEOMETRY": 5001,
    "REDSHIFT_LIGHT_PHYSICAL_AREA_GEOMETRY_RECTANGLE": 0,
    "REDSHIFT_LIGHT_PHYSICAL_AREA_GEOMETRY_DISC": 1,
    "REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEX": 5002,
    "REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEY": 5003,
    "REDSHIFT_LIGHT_VOLUME_SIZEX": 5004,
}


class BC(dict):
    def __missing__(self, key):
        return None


def load(extra_symbols=None):
    c4d = fake_c4d.install(extra_symbols)
    from snootlib import lights, render_setup
    return c4d, lights, render_setup


class C4DLightTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.lights, _ = load()

    def area_light(self, shape, x=200.0, y=100.0, tags=()):
        c4d = self.c4d
        return FakeNode(5102, {
            c4d.LIGHT_TYPE: c4d.LIGHT_TYPE_AREA,
            c4d.LIGHT_AREADETAILS_SHAPE: shape,
            c4d.LIGHT_AREADETAILS_SIZEX: x,
            c4d.LIGHT_AREADETAILS_SIZEY: y,
        }, tags=tags)

    def test_rectangle(self):
        info = self.lights.read_light(self.area_light(self.c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE))
        self.assertEqual((info.kind, info.is_area, info.shape), ("c4d", True, "rectangle"))
        self.assertEqual((info.width, info.height), (200.0, 100.0))
        self.assertTrue(self.lights.has_size(info))

    def test_disc(self):
        info = self.lights.read_light(self.area_light(self.c4d.LIGHT_AREADETAILS_SHAPE_DISC, 50.0, 50.0))
        self.assertEqual(info.shape, "disc")

    def test_base_roundness_follows_light_shape(self):
        L, c4d = self.lights, self.c4d
        rect = L.read_light(self.area_light(c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE))
        disc = L.read_light(self.area_light(c4d.LIGHT_AREADETAILS_SHAPE_DISC, 50.0, 50.0))
        self.assertEqual(L.base_roundness(rect), 0.0)
        self.assertEqual(L.base_roundness(disc), 1.0)
        self.assertEqual(L.base_roundness(L.read_light(None)), 0.0)

    def test_other_shape_still_sized(self):
        info = self.lights.read_light(self.area_light(self.c4d.LIGHT_AREADETAILS_SHAPE_SPHERE))
        self.assertEqual(info.shape, "other")
        self.assertTrue(self.lights.has_size(info))
        self.assertTrue(info.message)

    def test_spot_light_is_not_area(self):
        light = FakeNode(5102, {self.c4d.LIGHT_TYPE: self.c4d.LIGHT_TYPE_SPOT})
        info = self.lights.read_light(light)
        self.assertFalse(info.is_area)
        self.assertFalse(self.lights.has_size(info))

    def test_octane_tag_marks_octane(self):
        light = self.area_light(self.c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE,
                                tags=[FakeNode(1029526)])
        info = self.lights.read_light(light)
        self.assertEqual(info.kind, "octane")
        self.assertEqual((info.width, info.height), (200.0, 100.0))

    def test_no_light(self):
        info = self.lights.read_light(None)
        self.assertIsNone(info.kind)
        self.assertFalse(self.lights.has_size(info))

    def test_parent_light_is_direct_parent_only(self):
        light = self.area_light(self.c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE)
        snoot = FakeNode(1000001)
        snoot.parent = light
        self.assertIs(self.lights.parent_light(snoot), light)
        null = FakeNode(5140)
        null.parent = light
        snoot.parent = null
        self.assertIsNone(self.lights.parent_light(snoot))


class ArnoldLightTest(unittest.TestCase):
    def setUp(self):
        _, self.lights, _ = load()

    def test_published_ids(self):
        # Constants published with C4DtoA.
        self.assertEqual(self.lights.C4DAIN_QUAD_LIGHT, 1218397465)
        self.assertEqual(self.lights.C4DAIN_DISK_LIGHT, 998592185)
        self.assertEqual(self.lights.C4DAIP_QUAD_LIGHT_WIDTH, 2034436501)
        self.assertEqual(self.lights.C4DAIP_QUAD_LIGHT_HEIGHT, 2120286158)
        self.assertEqual(self.lights.C4DAIP_QUAD_LIGHT_ROUNDNESS, 1641633270)
        self.assertEqual(self.lights.c4dtoa_id("quad_light.intensity"), 67722820)
        self.assertEqual(self.lights.c4dtoa_id("point_light.radius"), 319355460)

    def test_quad(self):
        L = self.lights
        light = FakeNode(1030424, {
            L.C4DAI_LIGHT_TYPE: L.C4DAIN_QUAD_LIGHT,
            L.C4DAIP_QUAD_LIGHT_WIDTH: 120.0,
            L.C4DAIP_QUAD_LIGHT_HEIGHT: 60.0,
            L.C4DAIP_QUAD_LIGHT_ROUNDNESS: 0.25,
        })
        info = L.read_light(light)
        self.assertEqual((info.kind, info.shape, info.width, info.height, info.roundness),
                         ("arnold", "rectangle", 120.0, 60.0, 0.25))

    def test_quad_roundness_is_base_roundness(self):
        L = self.lights
        light = FakeNode(1030424, {L.C4DAI_LIGHT_TYPE: L.C4DAIN_QUAD_LIGHT,
                                   L.C4DAIP_QUAD_LIGHT_WIDTH: 10.0,
                                   L.C4DAIP_QUAD_LIGHT_HEIGHT: 10.0,
                                   L.C4DAIP_QUAD_LIGHT_ROUNDNESS: 0.4})
        self.assertEqual(L.base_roundness(L.read_light(light)), 0.4)

    def test_disk(self):
        L = self.lights
        light = FakeNode(1030424, {L.C4DAI_LIGHT_TYPE: L.C4DAIN_DISK_LIGHT,
                                   L.C4DAIP_DISK_LIGHT_RADIUS: 30.0})
        info = L.read_light(light)
        self.assertEqual((info.shape, info.width, info.height), ("disc", 60.0, 60.0))

    def test_other_type(self):
        L = self.lights
        info = L.read_light(FakeNode(1030424, {L.C4DAI_LIGHT_TYPE: L.c4dtoa_id("point_light")}))
        self.assertFalse(info.is_area)


class RedshiftLightTest(unittest.TestCase):
    def rs_light(self, c4d, light_type=3, geometry=0, x=150.0, y=75.0):
        return FakeNode(1036751, {
            c4d.REDSHIFT_LIGHT_TYPE: light_type,
            c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_GEOMETRY: geometry,
            c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEX: x,
            c4d.REDSHIFT_LIGHT_PHYSICAL_AREA_SIZEY: y,
        })

    def test_symbols_found_by_pattern(self):
        c4d, lights, _ = load(REDSHIFT_SYMBOLS)
        info = lights.read_light(self.rs_light(c4d))
        self.assertEqual((info.kind, info.is_area, info.shape), ("redshift", True, "rectangle"))
        self.assertEqual((info.width, info.height), (150.0, 75.0))

    def test_disc_and_non_area(self):
        c4d, lights, _ = load(REDSHIFT_SYMBOLS)
        self.assertEqual(lights.read_light(self.rs_light(c4d, geometry=1)).shape, "disc")
        self.assertFalse(lights.read_light(self.rs_light(c4d, light_type=0)).is_area)

    def test_underscore_variant(self):
        symbols = {"REDSHIFT_LIGHT_AREA_SIZE_X": 7001, "REDSHIFT_LIGHT_AREA_SIZE_Y": 7002}
        c4d, lights, _ = load(symbols)
        info = lights.read_light(FakeNode(1036751, {7001: 40.0, 7002: 20.0}))
        self.assertEqual((info.width, info.height), (40.0, 20.0))

    def test_description_scan_when_symbols_missing(self):
        c4d, lights, _ = load()
        size_x = DescID(DescLevel(8001, c4d.DTYPE_REAL))
        size_y = DescID(DescLevel(8002, c4d.DTYPE_REAL))
        other = DescID(DescLevel(8003, c4d.DTYPE_REAL))
        light = FakeNode(1036751, description=[
            (BC({c4d.DESC_NAME: "Intensity", c4d.DESC_IDENT: "REDSHIFT_LIGHT_INTENSITY"}), other, None),
            (BC({c4d.DESC_NAME: "Size X", c4d.DESC_IDENT: "REDSHIFT_LIGHT_AREA_SIZEX"}), size_x, None),
            (BC({c4d.DESC_NAME: "Size Y", c4d.DESC_IDENT: "REDSHIFT_LIGHT_AREA_SIZEY"}), size_y, None),
        ])
        light[size_x] = 90.0
        light[size_y] = 30.0

        # Off the main thread the scan is not allowed: report, don't guess.
        info = lights.read_light(light, allow_description_scan=False)
        self.assertFalse(lights.has_size(info))
        self.assertTrue(info.message)

        info = lights.read_light(light, allow_description_scan=True)
        self.assertEqual((info.width, info.height), (90.0, 30.0))
        # Cached for worker threads afterwards.
        info = lights.read_light(light, allow_description_scan=False)
        self.assertEqual((info.width, info.height), (90.0, 30.0))

    def test_missing_everything(self):
        _, lights, _ = load()
        info = lights.read_light(FakeNode(1036751), allow_description_scan=True)
        self.assertEqual(info.kind, "redshift")
        self.assertFalse(lights.has_size(info))
        self.assertIn("not found", lights.describe(info))


class ResolveRendererTest(unittest.TestCase):
    def setUp(self):
        self.c4d, self.lights, self.render_setup = load()
        from snootlib import ids
        self.ids = ids

    def test_light_decides_in_auto(self):
        rs = self.render_setup
        doc = FakeDoc(0)
        self.assertEqual(rs.resolve_renderer(doc, FakeNode(1036751)), "redshift")
        self.assertEqual(rs.resolve_renderer(doc, FakeNode(1030424)), "arnold")
        self.assertEqual(rs.resolve_renderer(doc, FakeNode(5102, tags=[FakeNode(1029526)])), "octane")

    def test_render_engine_decides_for_c4d_lights(self):
        rs = self.render_setup
        light = FakeNode(5102)
        self.assertEqual(rs.resolve_renderer(FakeDoc(1036219), light), "redshift")
        self.assertEqual(rs.resolve_renderer(FakeDoc(1029988), light), "arnold")
        self.assertEqual(rs.resolve_renderer(FakeDoc(1029525), light), "octane")
        self.assertEqual(rs.resolve_renderer(FakeDoc(0), light), "standard")
        self.assertEqual(rs.resolve_renderer(FakeDoc(1023342), None), "standard")

    def test_explicit_choice_wins(self):
        rs = self.render_setup
        self.assertEqual(
            rs.resolve_renderer(FakeDoc(1036219), FakeNode(1036751), self.ids.SNOOT_RENDERER_OCTANE),
            "octane")


if __name__ == "__main__":
    unittest.main()
