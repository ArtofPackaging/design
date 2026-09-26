import math
import os
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "snoot"))

from snootlib import geometry  # noqa: E402
from snootlib.geometry import SnootParams  # noqa: E402


def make(**overrides):
    values = dict(
        width=200.0, height=100.0, length=150.0, opening_x=1.0, opening_y=1.0,
        roundness=0.0, base_roundness=0.0, thickness=0.5, padding=0.5, offset=0.0, subdivision=8,
        flip=False,
    )
    values.update(overrides)
    return SnootParams(**values)


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1], p[2] - q[2])


def cross(u, v):
    # Same component formula as Cinema 4D's Vector % Vector.
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def face_normal(points, poly):
    # Cinema 4D CalcFaceNormal: triangles (b - a) x (c - a), quads (b - d) x (c - a).
    a, b, c, d = (points[i] for i in poly)
    if poly[2] == poly[3]:
        return cross(sub(b, a), sub(c, a))
    return cross(sub(b, d), sub(c, a))


def corners(poly):
    return poly[:3] if poly[2] == poly[3] else poly


def centroid(points, poly):
    ps = [points[i] for i in corners(poly)]
    return tuple(sum(p[k] for p in ps) / len(ps) for k in range(3))


def signed_volume(mesh):
    total = 0.0
    for a, b, c, d in mesh.polygons:
        for tri in ((a, b, c), (a, c, d)):
            p, q, r = (mesh.points[i] for i in tri)
            total += dot(p, cross(q, r))
    return total / 6.0


class MeshTopologyTest(unittest.TestCase):
    CASES = [
        make(),
        make(roundness=0.5),
        make(roundness=1.0),
        make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0),  # disc light: cylinder
        make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0, opening_x=0.5),  # circle -> slot
        make(width=100.0, height=100.0, roundness=1.0),              # square light, round opening
        make(roundness=0.6, opening_x=0.5),                          # rect light, rounded taper
        make(base_roundness=1.0, roundness=0.0),                     # disc light, square opening
        make(width=100.0, height=300.0, roundness=1.0),              # vertical slot
        make(opening_x=0.3, opening_y=1.8, roundness=0.7),
        make(flip=True, roundness=0.4),
        make(offset=-10.0, roundness=0.2, subdivision=1),
    ]

    def test_closed_two_manifold_with_consistent_winding(self):
        for params in self.CASES:
            mesh = geometry.build_mesh(params)
            directed = Counter()
            for poly in mesh.polygons:
                vs = corners(poly)
                for k in range(len(vs)):
                    directed[(vs[k], vs[(k + 1) % len(vs)])] += 1
            for (u, v), count in directed.items():
                self.assertEqual(count, 1, (params, u, v))
                # Every directed edge is matched by its reverse exactly once:
                # closed surface, consistently oriented.
                self.assertEqual(directed[(v, u)], 1, (params, u, v))

    def test_no_degenerate_edges(self):
        for params in self.CASES:
            mesh = geometry.build_mesh(params)
            for poly in mesh.polygons:
                vs = corners(poly)
                for k in range(len(vs)):
                    p, q = mesh.points[vs[k]], mesh.points[vs[(k + 1) % len(vs)]]
                    gap = math.sqrt(sum((p[i] - q[i]) ** 2 for i in range(3)))
                    self.assertGreater(gap, 1e-9, (params, poly))

    def test_circle_to_slot_welds_into_triangles(self):
        mesh = geometry.build_mesh(make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0, opening_x=0.5))
        triangles = [poly for poly in mesh.polygons if poly[2] == poly[3]]
        self.assertTrue(triangles)
        self.assertEqual(len(set(mesh.points)), len(mesh.points))

    def test_positive_volume_matches_wall(self):
        params = make()
        mesh = geometry.build_mesh(params)
        a, b = 100.5, 50.5
        t, length = params.thickness, params.length
        expected = length * ((2 * (a + t)) * (2 * (b + t)) - (2 * a) * (2 * b))
        self.assertAlmostEqual(signed_volume(mesh), expected, places=6)

        flipped = geometry.build_mesh(make(flip=True))
        self.assertAlmostEqual(signed_volume(flipped), expected, places=6)

    def test_rounded_volume_is_positive(self):
        for params in self.CASES:
            self.assertGreater(signed_volume(geometry.build_mesh(params)), 0.0, params)

    def test_counts(self):
        mesh = geometry.build_mesh(make())
        self.assertEqual(len(mesh.points), 16)
        self.assertEqual(len(mesh.polygons), 16)
        self.assertEqual(len(mesh.inside), 4)
        self.assertEqual(len(mesh.outside), 12)
        self.assertEqual(len(mesh.uvs), len(mesh.polygons))

        # Square light, full roundness: circle without duplicate side points.
        circle = geometry.build_mesh(make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0, subdivision=8))
        self.assertEqual(len(circle.points), 4 * 32)

    def test_selections_partition_polygons(self):
        mesh = geometry.build_mesh(make(roundness=0.5))
        self.assertEqual(sorted(mesh.inside + mesh.outside), list(range(len(mesh.polygons))))


class OrientationTest(unittest.TestCase):
    def check_orientation(self, params):
        mesh = geometry.build_mesh(params)
        d = -1.0 if params.flip else 1.0
        inside = set(mesh.inside)
        z_mid = d * (params.offset + params.length * 0.5)
        for index, poly in enumerate(mesh.polygons):
            normal = face_normal(mesh.points, poly)
            self.assertGreater(dot(normal, normal), 0.0, "zero-area face")
            c = centroid(mesh.points, poly)
            radial = (c[0], c[1], 0.0)
            if index in inside:
                self.assertLess(dot(normal, radial), 0.0, "inner wall must face the axis")
            elif abs(normal[2]) > abs(normal[0]) + abs(normal[1]):
                # Rim: tip faces along the beam, base faces the light.
                along = 1.0 if (c[2] - z_mid) * d > 0 else -1.0
                self.assertGreater(normal[2] * d * along, 0.0)
            else:
                self.assertGreater(dot(normal, radial), 0.0, "outer wall must face out")

    def test_straight(self):
        self.check_orientation(make())

    def test_rounded_tapered(self):
        self.check_orientation(make(roundness=0.6, opening_x=0.5, opening_y=0.7))

    def test_circle_to_slot(self):
        self.check_orientation(make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0, opening_x=0.5))
        self.check_orientation(make(width=100.0, height=100.0, roundness=1.0, base_roundness=1.0, opening_y=0.4, flip=True))

    def test_flipped(self):
        self.check_orientation(make(flip=True, roundness=0.3))

    def test_tip_is_along_positive_z(self):
        mesh = geometry.build_mesh(make(length=80.0, offset=5.0))
        zs = sorted(set(round(p[2], 6) for p in mesh.points))
        self.assertEqual(zs, [5.0, 85.0])
        flipped = geometry.build_mesh(make(length=80.0, offset=5.0, flip=True))
        zs = sorted(set(round(p[2], 6) for p in flipped.points))
        self.assertEqual(zs, [-85.0, -5.0])


def rounded_rect_distance(x, y, ring):
    """Signed distance from (x, y) to a rounded rectangle outline."""
    qx = abs(x) - (ring.a - ring.r)
    qy = abs(y) - (ring.b - ring.r)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - ring.r


def split_rings(mesh, params, tip=False):
    """(inner, outer) points of the base or tip ring."""
    inner_ring = geometry.rings(params)[1 if tip else 0]
    pts = [p for p in mesh.points if abs(p[2] - inner_ring.z) < 1e-9]
    inner = [p for p in pts if abs(rounded_rect_distance(p[0], p[1], inner_ring)) < 1e-6]
    outer = [p for p in pts if abs(rounded_rect_distance(p[0], p[1], inner_ring)) >= 1e-6]
    return inner, outer


class ShapeTest(unittest.TestCase):
    def test_inner_base_clears_light_by_padding(self):
        params = make(padding=2.0)
        base, outer = split_rings(geometry.build_mesh(params), params)
        self.assertEqual(len(base), 4)
        self.assertEqual(len(outer), 4)
        self.assertAlmostEqual(max(p[0] for p in base), 102.0)
        self.assertAlmostEqual(max(p[1] for p in base), 52.0)
        self.assertAlmostEqual(max(p[0] for p in outer), 102.5)

    def test_opening_scales_tip(self):
        params = make(opening_x=0.5, opening_y=2.0, padding=0.0)
        tip, _ = split_rings(geometry.build_mesh(params), params, tip=True)
        self.assertAlmostEqual(max(p[0] for p in tip), 50.0)
        self.assertAlmostEqual(max(p[1] for p in tip), 100.0)

    def test_full_roundness_square_is_circle(self):
        params = make(width=100.0, height=100.0, padding=0.0, roundness=1.0, base_roundness=1.0)
        inner, outer = split_rings(geometry.build_mesh(params), params)
        self.assertEqual(len(inner), 32)
        self.assertEqual(len(outer), 32)
        for x, y, _ in inner:
            self.assertAlmostEqual(math.hypot(x, y), 50.0)
        for x, y, _ in outer:
            self.assertAlmostEqual(math.hypot(x, y), 50.5)

    def test_base_keeps_light_shape_when_opening_is_round(self):
        # Rectangular light, fully rounded opening: the base stays a sharp
        # rectangle the size of the light (plus padding).
        params = make(width=35.0, height=26.0, padding=0.0, roundness=1.0, length=60.0)
        mesh = geometry.build_mesh(params)
        base, outer_base = split_rings(mesh, params)
        self.assertEqual(sorted(set((abs(x), abs(y)) for x, y, _ in base)), [(17.5, 13.0)])
        self.assertEqual(len(base), 4)
        self.assertEqual(len(outer_base), 4)
        tip, _ = split_rings(mesh, params, tip=True)
        self.assertGreater(len(tip), 4)
        for x, y, _ in tip:
            ring = geometry.rings(params)[1]
            self.assertAlmostEqual(rounded_rect_distance(x, y, ring), 0.0)
        # The corners fan out into triangles.
        self.assertTrue(any(poly[2] == poly[3] for poly in mesh.polygons))

    def test_disc_light_base_is_round_even_with_square_opening(self):
        params = make(width=50.0, height=50.0, padding=0.0, base_roundness=1.0, roundness=0.0)
        base, _ = split_rings(geometry.build_mesh(params), params)
        for x, y, _ in base:
            self.assertAlmostEqual(math.hypot(x, y), 25.0)

    def test_circle_base_opens_into_slot(self):
        params = make(width=100.0, height=100.0, padding=0.0, roundness=1.0, base_roundness=1.0, opening_x=0.5)
        mesh = geometry.build_mesh(params)
        base, _ = split_rings(mesh, params)
        tip, _ = split_rings(mesh, params, tip=True)
        for x, y, _ in base:
            self.assertAlmostEqual(math.hypot(x, y), 50.0)
        # Slot: 25 cm half width, 50 cm half height, fully rounded ends.
        self.assertAlmostEqual(max(p[0] for p in tip), 25.0)
        self.assertAlmostEqual(max(p[1] for p in tip), 50.0)
        self.assertTrue(any(abs(p[0]) == 25.0 and abs(p[1]) > 1.0 for p in tip))

    def test_uvs_in_range(self):
        mesh = geometry.build_mesh(make(roundness=0.5))
        for quad in mesh.uvs:
            for u, v in quad:
                self.assertGreaterEqual(u, 0.0)
                self.assertLessEqual(u, 1.0)
                self.assertIn(v, (0.0, 1.0))


class HandleTest(unittest.TestCase):
    def round_trip(self, params):
        for index, (position, _direction, _anchor) in enumerate(geometry.handles(params)):
            changes = geometry.apply_handle(params, index, position)
            for field, value in changes.items():
                self.assertAlmostEqual(value, getattr(params, field), places=9,
                                       msg="handle %d field %s" % (index, field))

    def test_round_trip(self):
        self.round_trip(make())
        self.round_trip(make(roundness=0.35, opening_x=0.6, opening_y=1.4, offset=3.0))
        self.round_trip(make(roundness=1.0, flip=True, offset=-4.0))

    def test_drag_changes_value(self):
        params = make(padding=0.0)
        self.assertAlmostEqual(geometry.apply_handle(params, geometry.HANDLE_LENGTH, (0, 0, 40.0))["length"], 40.0)
        self.assertAlmostEqual(geometry.apply_handle(params, geometry.HANDLE_OPENING_X, (50.0, 0, 0))["opening_x"], 0.5)
        self.assertAlmostEqual(geometry.apply_handle(params, geometry.HANDLE_OPENING_Y, (0, 25.0, 0))["opening_y"], 0.5)
        self.assertEqual(geometry.apply_handle(params, geometry.HANDLE_ROUNDNESS, (500.0, 500.0, 0))["roundness"], 0.0)
        self.assertEqual(geometry.apply_handle(params, geometry.HANDLE_ROUNDNESS, (-500.0, -500.0, 0))["roundness"], 1.0)

    def test_opening_handle_clamps_to_description_limits(self):
        params = make(padding=0.0)
        self.assertEqual(geometry.apply_handle(params, geometry.HANDLE_OPENING_X, (-40.0, 0, 0))["opening_x"], 0.01)
        self.assertEqual(geometry.apply_handle(params, geometry.HANDLE_OPENING_Y, (0, 1e6, 0))["opening_y"], 10.0)

    def test_length_handle_clamps_at_zero(self):
        params = make(offset=10.0)
        self.assertEqual(geometry.apply_handle(params, geometry.HANDLE_LENGTH, (0, 0, -30.0))["length"], 0.0)


if __name__ == "__main__":
    unittest.main()
