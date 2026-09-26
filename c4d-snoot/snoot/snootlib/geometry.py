"""Snoot mesh construction and handle math.

Pure Python with no Cinema 4D dependency so it can be unit tested outside C4D.
All coordinates are in the light's local space: the emitter lies in the XY
plane and emits along +Z (Cinema 4D, Redshift, Arnold and Octane convention).

Cross-section: a rounded rectangle with half extents (a, b) and corner radius
r = roundness * min(a, b). The base keeps the light's own shape
(``base_roundness``: 0 for a rectangle, 1 for a disc); ``roundness`` shapes
only the opening. Roundness 0 gives square corners, 1 gives a circle for a
square opening and a slot (stadium) for a rectangular one. Where a sharp base
corner meets a rounded opening corner the wall becomes a triangle fan.

The wall is a closed shell made of four rings of points:

    0  inner base   (z = offset)
    1  inner tip    (z = offset + length)
    2  outer base   (inner base pushed out by the wall thickness)
    3  outer tip

Polygons follow Cinema 4D's winding (normal = (b - a) x (c - a)) so every face
points out of the wall solid: the inner wall faces the beam axis, the outer
wall and both rims face away from the wall.
"""

import math
from collections import namedtuple

INSIDE_SELECTION = "SnootInside"
OUTSIDE_SELECTION = "SnootOutside"

MIN_EXTENT = 0.01   # cm, smallest half extent / length the mesh will use
MIN_THICKNESS = 0.01
# Opening limits, matching SNOOT_OPENING_X/Y in Osnoot.res (1% .. 1000%).
MIN_OPENING = 0.01
MAX_OPENING = 10.0
_EPS = 1e-6

SQRT2 = math.sqrt(2.0)
# Distance from a rectangle corner to the 45 degree point of a fillet of
# radius r is r * (sqrt(2) - 1).
_FILLET_HANDLE = SQRT2 - 1.0

HANDLE_LENGTH = 0
HANDLE_OPENING_X = 1
HANDLE_OPENING_Y = 2
HANDLE_ROUNDNESS = 3
HANDLE_COUNT = 4

# namedtuples are hashable and comparable, so a SnootParams doubles as the
# cache signature in GetVirtualObjects.
SnootParams = namedtuple(
    "SnootParams",
    "width height length opening_x opening_y roundness base_roundness "
    "thickness padding offset subdivision flip",
)

Ring = namedtuple("Ring", "a b r z")

Mesh = namedtuple("Mesh", "points polygons uvs inside outside")


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def direction(params):
    return -1.0 if params.flip else 1.0


def rings(params):
    """Return (inner_base, inner_tip, outer_base, outer_tip) rings."""
    d = direction(params)
    rho_base = _clamp(params.base_roundness, 0.0, 1.0)
    rho_tip = _clamp(params.roundness, 0.0, 1.0)
    t = max(params.thickness, MIN_THICKNESS)
    length = max(params.length, MIN_EXTENT)

    a0 = max(params.width * 0.5 + params.padding, MIN_EXTENT)
    b0 = max(params.height * 0.5 + params.padding, MIN_EXTENT)
    a1 = max(a0 * params.opening_x, MIN_EXTENT)
    b1 = max(b0 * params.opening_y, MIN_EXTENT)
    z0 = d * params.offset
    z1 = d * (params.offset + length)

    inner_base = Ring(a0, b0, rho_base * min(a0, b0), z0)
    inner_tip = Ring(a1, b1, rho_tip * min(a1, b1), z1)
    return (
        inner_base,
        inner_tip,
        _offset_ring(inner_base, t, rho_base),
        _offset_ring(inner_tip, t, rho_tip),
    )


def _offset_ring(ring, t, rho):
    # The parallel offset of a rounded rectangle is a rounded rectangle with
    # radius r + t. Square corners stay square (mitred) so a roundness of 0
    # gives a crisp box.
    r = ring.r + t if rho > _EPS else 0.0
    return Ring(ring.a + t, ring.b + t, r, ring.z)


def _is_rounded(params):
    # Either end rounded means every ring gets arc points; a sharp end then
    # has coincident corner points, which _weld merges.
    return max(_clamp(params.roundness, 0.0, 1.0),
               _clamp(params.base_roundness, 0.0, 1.0)) > _EPS


def _ring_points(ring, segments, rounded, drop_h, drop_v):
    """Counter-clockwise (seen from +Z) outline of a rounded rectangle.

    Corner k spans k*90 .. (k+1)*90 degrees. The straight side before corner
    1 and 3 is horizontal, before corner 0 and 2 vertical; when that side has
    zero length in every ring it is dropped so no duplicate points appear.
    """
    points = []
    for k in range(4):
        sx = 1.0 if k in (0, 3) else -1.0
        sy = 1.0 if k in (0, 1) else -1.0
        if not rounded:
            points.append((sx * ring.a, sy * ring.b))
            continue
        cx = sx * (ring.a - ring.r)
        cy = sy * (ring.b - ring.r)
        start = k * math.pi * 0.5
        for j in range(segments + 1):
            if j == 0 and ((k in (1, 3) and drop_h) or (k in (0, 2) and drop_v)):
                continue
            angle = start + j * (math.pi * 0.5) / segments
            points.append((cx + ring.r * math.cos(angle), cy + ring.r * math.sin(angle)))
    return points


def _cumulative_u(points):
    """Arc-length parameter along a closed outline, with a closing value of 1."""
    lengths = [0.0]
    for i in range(1, len(points)):
        (x0, y0), (x1, y1) = points[i - 1], points[i]
        lengths.append(lengths[-1] + math.hypot(x1 - x0, y1 - y0))
    (x0, y0), (x1, y1) = points[-1], points[0]
    total = lengths[-1] + math.hypot(x1 - x0, y1 - y0)
    if total <= 0.0:
        return [i / float(len(points)) for i in range(len(points))] + [1.0]
    return [value / total for value in lengths] + [1.0]


def build_mesh(params):
    """Build the snoot shell. Returns a Mesh of plain tuples."""
    ring_list = rings(params)
    rounded = _is_rounded(params)
    segments = max(int(params.subdivision), 1)

    inner = ring_list[:2]
    drop_h = rounded and all(ring.a - ring.r < _EPS for ring in inner)
    drop_v = rounded and all(ring.b - ring.r < _EPS for ring in inner)

    outlines = [_ring_points(ring, segments, rounded, drop_h, drop_v) for ring in ring_list]
    n = len(outlines[0])

    points = []
    for ring, outline in zip(ring_list, outlines):
        points.extend((x, y, ring.z) for x, y in outline)

    us = [_cumulative_u(outline) for outline in outlines]

    def idx(ring, i):
        return ring * n + (i % n)

    polygons = []
    uvs = []
    inside = []
    outside = []

    for i in range(n):
        j = i + 1
        ib_u, it_u, ob_u, ot_u = us[0], us[1], us[2], us[3]

        # Inner wall, faces the beam axis.
        inside.append(len(polygons))
        polygons.append((idx(0, i), idx(1, i), idx(1, j), idx(0, j)))
        uvs.append(((ib_u[i], 0.0), (it_u[i], 1.0), (it_u[j], 1.0), (ib_u[j], 0.0)))

        # Outer wall, faces away from the axis.
        outside.append(len(polygons))
        polygons.append((idx(2, i), idx(2, j), idx(3, j), idx(3, i)))
        uvs.append(((ob_u[i], 0.0), (ob_u[j], 0.0), (ot_u[j], 1.0), (ot_u[i], 1.0)))

        # Tip rim, faces along the beam.
        outside.append(len(polygons))
        polygons.append((idx(1, i), idx(3, i), idx(3, j), idx(1, j)))
        uvs.append(((it_u[i], 0.0), (ot_u[i], 1.0), (ot_u[j], 1.0), (it_u[j], 0.0)))

        # Base rim, faces back towards the light.
        outside.append(len(polygons))
        polygons.append((idx(0, i), idx(0, j), idx(2, j), idx(2, i)))
        uvs.append(((ib_u[i], 0.0), (ib_u[j], 0.0), (ob_u[j], 1.0), (ob_u[i], 1.0)))

    if params.flip:
        # Mirroring along Z inverts orientation; reverse the winding to keep
        # normals pointing out of the wall.
        polygons = [(a, d, c, b) for a, b, c, d in polygons]
        uvs = [(ua, ud, uc, ub) for ua, ub, uc, ud in uvs]

    return _weld(Mesh(points, polygons, uvs, inside, outside))


def _weld(mesh):
    """Merge coincident points and collapse the polygons that touch them.

    A side can have zero length at one end of the tube but not the other
    (a round base opening into a slot). Those points are welded; quads that
    lose a corner become triangles (c == d, Cinema 4D's convention) and faces
    that collapse to a line are removed.
    """
    parent = list(range(len(mesh.points)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for poly in mesh.polygons:
        for k in range(4):
            i, j = poly[k], poly[(k + 1) % 4]
            p, q = mesh.points[i], mesh.points[j]
            if abs(p[0] - q[0]) + abs(p[1] - q[1]) + abs(p[2] - q[2]) < _EPS:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)

    if all(find(i) == i for i in range(len(parent))):
        return mesh

    remap = {}
    points = []
    for i, point in enumerate(mesh.points):
        root = find(i)
        if root not in remap:
            remap[root] = len(points)
            points.append(point)

    inside_set = set(mesh.inside)
    polygons, uvs, inside, outside = [], [], [], []
    for index, (poly, uv) in enumerate(zip(mesh.polygons, mesh.uvs)):
        verts, coords = [], []
        for vertex, coord in zip(poly, uv):
            v = remap[find(vertex)]
            if not verts or (v != verts[-1]):
                verts.append(v)
                coords.append(coord)
        if len(verts) > 1 and verts[0] == verts[-1]:
            verts.pop()
            coords.pop()
        if len(verts) < 3:
            continue
        if len(verts) == 3:
            verts.append(verts[2])
            coords.append(coords[2])
        (inside if index in inside_set else outside).append(len(polygons))
        polygons.append(tuple(verts))
        uvs.append(tuple(coords))

    return Mesh(points, polygons, uvs, inside, outside)


def handles(params):
    """Viewport handles as a list of (position, direction, anchor) tuples.

    ``anchor`` is where the guide line to the handle starts.
    """
    inner_base, inner_tip, _, _ = rings(params)
    d = direction(params)
    z0, z1 = inner_base.z, inner_tip.z
    a, b, r = inner_tip.a, inner_tip.b, inner_tip.r
    s = r * _FILLET_HANDLE / SQRT2
    tip = (0.0, 0.0, z1)
    return [
        ((0.0, 0.0, z1), (0.0, 0.0, d), (0.0, 0.0, z0)),
        ((a, 0.0, z1), (1.0, 0.0, 0.0), tip),
        ((0.0, b, z1), (0.0, 1.0, 0.0), tip),
        ((a - s, b - s, z1), (-1.0 / SQRT2, -1.0 / SQRT2, 0.0), (a, b, z1)),
    ]


def apply_handle(params, index, position):
    """Map a dragged handle position (light local space) back to parameters.

    Returns a dict with the changed SnootParams field names.
    """
    inner_base, inner_tip, _, _ = rings(params)
    x, y, z = position
    if index == HANDLE_LENGTH:
        return {"length": max(direction(params) * z - params.offset, 0.0)}
    if index == HANDLE_OPENING_X:
        return {"opening_x": _clamp(x / inner_base.a, MIN_OPENING, MAX_OPENING)}
    if index == HANDLE_OPENING_Y:
        return {"opening_y": _clamp(y / inner_base.b, MIN_OPENING, MAX_OPENING)}
    if index == HANDLE_ROUNDNESS:
        a, b = inner_tip.a, inner_tip.b
        # Distance travelled from the corner along the inward diagonal.
        dist = ((a - x) + (b - y)) / SQRT2
        radius = max(dist, 0.0) / _FILLET_HANDLE
        return {"roundness": _clamp(radius / min(a, b), 0.0, 1.0)}
    raise IndexError(index)
