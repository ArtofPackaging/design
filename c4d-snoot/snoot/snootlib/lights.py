"""Find the light a snoot is mounted on and read its emitter size.

Supported lights:

* Cinema 4D light (Olight), area type. Octane area lights are Cinema 4D
  lights carrying an Octane Light tag, so they use the same parameters.
* Redshift Light (1036751), area type. Redshift's parameter symbols are
  looked up by name at runtime (see ``_redshift_params``) because they are
  only published in the Redshift SDK headers.
* Arnold Light (1030424) from C4DtoA, quad and disk types. C4DtoA derives its
  IDs from the Arnold node/parameter names (``c4dtoa_id``).

Every size is a full width/height in centimetres, in the light's local XY
plane.
"""

import re
from collections import namedtuple

import c4d

ID_OLIGHT = 5102
ID_REDSHIFT_LIGHT = 1036751
ID_ARNOLD_LIGHT = 1030424
ID_OCTANE_LIGHT_TAG = 1029526

KIND_C4D = "c4d"
KIND_OCTANE = "octane"
KIND_REDSHIFT = "redshift"
KIND_ARNOLD = "arnold"

SHAPE_RECT = "rectangle"
SHAPE_DISC = "disc"
SHAPE_OTHER = "other"

_LABELS = {
    KIND_C4D: "Cinema 4D",
    KIND_OCTANE: "Octane",
    KIND_REDSHIFT: "Redshift",
    KIND_ARNOLD: "Arnold",
}

LightInfo = namedtuple(
    "LightInfo", "light kind is_area shape width height roundness message")


def _info(light=None, kind=None, is_area=False, shape=SHAPE_OTHER, width=None,
          height=None, roundness=None, message=""):
    return LightInfo(light, kind, is_area, shape, width, height, roundness, message)


def has_size(info):
    return bool(info.width) and bool(info.height) and info.width > 0.0 and info.height > 0.0


def label(kind):
    return _LABELS.get(kind, "Unknown")


def c4dtoa_id(name):
    """C4DtoA node/parameter ID, e.g. c4dtoa_id("quad_light.width").

    C4DtoA IDs are abs(int32(djb2(name))). This reproduces the published
    constants, e.g. C4DAIN_QUAD_LIGHT = 1218397465 and
    C4DAIP_QUAD_LIGHT_WIDTH = 2034436501.
    """
    h = 5381
    for byte in name.encode("utf-8"):
        h = (h * 33 + byte) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return abs(h)


C4DAI_LIGHT_TYPE = 101
C4DAIN_QUAD_LIGHT = c4dtoa_id("quad_light")
C4DAIN_DISK_LIGHT = c4dtoa_id("disk_light")
C4DAIP_QUAD_LIGHT_WIDTH = c4dtoa_id("quad_light.width")
C4DAIP_QUAD_LIGHT_HEIGHT = c4dtoa_id("quad_light.height")
C4DAIP_QUAD_LIGHT_ROUNDNESS = c4dtoa_id("quad_light.roundness")
C4DAIP_DISK_LIGHT_RADIUS = c4dtoa_id("disk_light.radius")


def light_kind(obj):
    if obj is None:
        return None
    t = obj.GetType()
    if t == ID_OLIGHT:
        return KIND_OCTANE if obj.GetTag(ID_OCTANE_LIGHT_TAG) is not None else KIND_C4D
    if t == ID_REDSHIFT_LIGHT:
        return KIND_REDSHIFT
    if t == ID_ARNOLD_LIGHT:
        return KIND_ARNOLD
    return None


def is_light(obj):
    return light_kind(obj) is not None


def parent_light(op):
    """The light a snoot is mounted on: its direct parent, or None."""
    parent = op.GetUp()
    return parent if is_light(parent) else None


def read_light(light, allow_description_scan=False):
    """Return a LightInfo for ``light`` (which may be None).

    ``allow_description_scan`` enables the slower description lookup used
    when a renderer's parameter symbols are missing; only pass True on the
    main thread.
    """
    kind = light_kind(light)
    if kind is None:
        return _info(message="Not mounted on a light")
    try:
        if kind in (KIND_C4D, KIND_OCTANE):
            return _read_c4d_light(light, kind)
        if kind == KIND_ARNOLD:
            return _read_arnold_light(light)
        return _read_redshift_light(light, allow_description_scan)
    except Exception as error:  # a renderer update renamed something
        return _info(light, kind, message="Could not read light size (%s)" % error)


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_c4d_light(light, kind):
    if light[c4d.LIGHT_TYPE] != c4d.LIGHT_TYPE_AREA:
        return _info(light, kind, message="Not an area light")
    shape = light[c4d.LIGHT_AREADETAILS_SHAPE]
    width = _float(light[c4d.LIGHT_AREADETAILS_SIZEX])
    height = _float(light[c4d.LIGHT_AREADETAILS_SIZEY])
    if shape == c4d.LIGHT_AREADETAILS_SHAPE_RECTANGLE:
        return _info(light, kind, True, SHAPE_RECT, width, height)
    if shape == c4d.LIGHT_AREADETAILS_SHAPE_DISC:
        return _info(light, kind, True, SHAPE_DISC, width, height)
    return _info(light, kind, True, SHAPE_OTHER, width, height,
                 message="Area shape is not a rectangle or disc; fitting to Size X/Y")


def _read_arnold_light(light):
    light_type = light[C4DAI_LIGHT_TYPE]
    if light_type == C4DAIN_QUAD_LIGHT:
        return _info(light, KIND_ARNOLD, True, SHAPE_RECT,
                     _float(light[C4DAIP_QUAD_LIGHT_WIDTH]),
                     _float(light[C4DAIP_QUAD_LIGHT_HEIGHT]),
                     _float(light[C4DAIP_QUAD_LIGHT_ROUNDNESS]))
    if light_type == C4DAIN_DISK_LIGHT:
        radius = _float(light[C4DAIP_DISK_LIGHT_RADIUS])
        diameter = radius * 2.0 if radius is not None else None
        return _info(light, KIND_ARNOLD, True, SHAPE_DISC, diameter, diameter)
    return _info(light, KIND_ARNOLD, message="Not a quad or disk light")


# -- Redshift ---------------------------------------------------------------

# Redshift registers its description symbols (REDSHIFT_LIGHT_*) in the c4d
# module. The exact names are not part of the public Python docs, so match
# them by pattern and cache the result.
_RS_SIZE_X = re.compile(r"AREA.*(SIZE_?X|WIDTH)$")
_RS_SIZE_Y = re.compile(r"AREA.*(SIZE_?Y|HEIGHT)$")
_RS_SIZE_X_LOOSE = re.compile(r"(SIZE_?X|WIDTH)$")
_RS_SIZE_Y_LOOSE = re.compile(r"(SIZE_?Y|HEIGHT)$")
_RS_NOT_AREA = ("VOLUME", "GOBO", "PROJ", "SHADOW", "IES", "DOME", "SUN", "PORTAL")
_RS_SHAPE = re.compile(r"AREA_(GEOMETRY|SHAPE)$")

_redshift_cache = {}


def _shortest(names):
    return min(names, key=len) if names else None


def _match_pair(names, pattern_x, pattern_y):
    size_x = _shortest([n for n in names if pattern_x.search(n)])
    size_y = _shortest([n for n in names if pattern_y.search(n)])
    return (size_x, size_y) if size_x and size_y else (None, None)


def _redshift_symbol_params():
    names = [n for n in dir(c4d) if n.startswith("REDSHIFT_LIGHT")]
    params = {
        "type": getattr(c4d, "REDSHIFT_LIGHT_TYPE", None),
        "area_types": [getattr(c4d, n) for n in names
                       if n.startswith("REDSHIFT_LIGHT_TYPE_") and "AREA" in n],
        "size_x": None,
        "size_y": None,
        "shape": None,
        "disc_values": [],
    }
    size_x, size_y = _match_pair(names, _RS_SIZE_X, _RS_SIZE_Y)
    if size_x is None:
        loose = [n for n in names if not any(word in n for word in _RS_NOT_AREA)]
        size_x, size_y = _match_pair(loose, _RS_SIZE_X_LOOSE, _RS_SIZE_Y_LOOSE)
    if size_x is not None:
        params["size_x"] = getattr(c4d, size_x)
        params["size_y"] = getattr(c4d, size_y)

    shape = _shortest([n for n in names if _RS_SHAPE.search(n)])
    if shape:
        params["shape"] = getattr(c4d, shape)
        params["disc_values"] = [getattr(c4d, n) for n in names
                                 if n.startswith(shape + "_") and "DISC" in n]
    return params


def _redshift_params(light, allow_description_scan):
    params = _redshift_cache.get("symbols")
    if params is None:
        params = _redshift_cache["symbols"] = _redshift_symbol_params()
    if params["size_x"] is not None:
        return params
    scanned = _redshift_cache.get("scan")
    if scanned is None and allow_description_scan:
        scanned = _redshift_cache["scan"] = _scan_size_ids(light)
    if scanned and scanned[0] is not None:
        return dict(params, size_x=scanned[0], size_y=scanned[1])
    return params


def _scan_size_ids(light):
    """Find area size parameters through the light's description."""
    ident_key = getattr(c4d, "DESC_IDENT", None)
    by_ident = {}
    by_name = {}
    description = light.GetDescription(c4d.DESCFLAGS_DESC_NONE)
    for bc, param_id, _group in description:
        if param_id[0].dtype != c4d.DTYPE_REAL:
            continue
        ident = bc[ident_key] if ident_key is not None else None
        if isinstance(ident, str):
            if _RS_SIZE_X.search(ident):
                by_ident.setdefault("x", param_id)
            elif _RS_SIZE_Y.search(ident):
                by_ident.setdefault("y", param_id)
        name = (bc[c4d.DESC_NAME] or "").strip().lower()
        if name in ("size x", "width"):
            by_name.setdefault("x", param_id)
        elif name in ("size y", "height"):
            by_name.setdefault("y", param_id)
    for found in (by_ident, by_name):
        if "x" in found and "y" in found:
            return found["x"], found["y"]
    return None, None


def _read_redshift_light(light, allow_description_scan):
    params = _redshift_params(light, allow_description_scan)
    if params["type"] is not None and params["area_types"]:
        if light[params["type"]] not in params["area_types"]:
            return _info(light, KIND_REDSHIFT, message="Not an area light")
    if params["size_x"] is None:
        return _info(light, KIND_REDSHIFT, True,
                     message="Redshift area size parameters not found")
    shape = SHAPE_RECT
    if params["shape"] is not None and light[params["shape"]] in params["disc_values"]:
        shape = SHAPE_DISC
    return _info(light, KIND_REDSHIFT, True, shape,
                 _float(light[params["size_x"]]), _float(light[params["size_y"]]))


def describe(info):
    """One line for the Attribute Manager."""
    if info.kind is None:
        return info.message
    text = "%s %s" % (label(info.kind), "area light" if info.is_area else "light")
    if has_size(info):
        text += "  %.4g x %.4g cm" % (info.width, info.height)
    if info.message:
        text += "  (%s)" % info.message
    return text
