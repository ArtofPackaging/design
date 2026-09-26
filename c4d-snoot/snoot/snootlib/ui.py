"""The Snoot tab, built in code.

The parameters are added to the object's description in GetDDescription
rather than read from a .res file, so the tab does not depend on Cinema 4D
loading the plugin's resource files. They go into the object tab
(ID_OBJECTPROPERTIES), which is relabelled "Snoot".
"""

import c4d

from . import ids

ROOT = 0  # the object tab

# (kind, parameter id, parent group id, label, options)
LAYOUT = (
    ("static", ids.SNOOT_INFO, ROOT, "Light: -", {}),

    ("group", ids.SNOOT_GROUP_OPENING, ROOT, "Opening", {"open": True}),
    ("real", ids.SNOOT_LENGTH, ids.SNOOT_GROUP_OPENING, "Length",
     {"unit": "meter", "min": 0.0, "max": 100000.0, "step": 1.0, "slider": (0.0, 500.0)}),
    ("real", ids.SNOOT_OPENING_X, ids.SNOOT_GROUP_OPENING, "Opening Width",
     {"unit": "percent", "min": 0.01, "max": 10.0, "step": 0.01, "slider": (0.1, 2.0)}),
    ("real", ids.SNOOT_OPENING_Y, ids.SNOOT_GROUP_OPENING, "Opening Height",
     {"unit": "percent", "min": 0.01, "max": 10.0, "step": 0.01, "slider": (0.1, 2.0)}),
    ("bool", ids.SNOOT_UNIFORM, ids.SNOOT_GROUP_OPENING, "Uniform Opening", {}),
    ("real", ids.SNOOT_ROUNDNESS, ids.SNOOT_GROUP_OPENING, "Opening Roundness",
     {"unit": "percent", "min": 0.0, "max": 1.0, "step": 0.01, "slider": (0.0, 1.0)}),

    ("group", ids.SNOOT_GROUP_FIT, ROOT, "Fit", {"open": True}),
    ("real", ids.SNOOT_THICKNESS, ids.SNOOT_GROUP_FIT, "Wall Thickness",
     {"unit": "meter", "min": 0.01, "max": 1000.0, "step": 0.1, "slider": (0.01, 5.0)}),
    ("real", ids.SNOOT_PADDING, ids.SNOOT_GROUP_FIT, "Padding",
     {"unit": "meter", "min": 0.0, "max": 1000.0, "step": 0.1, "slider": (0.0, 10.0)}),
    ("real", ids.SNOOT_OFFSET, ids.SNOOT_GROUP_FIT, "Offset",
     {"unit": "meter", "min": -100000.0, "max": 100000.0, "step": 1.0, "slider": (-50.0, 50.0)}),
    ("bool", ids.SNOOT_FLIP, ids.SNOOT_GROUP_FIT, "Flip Direction", {}),
    ("long", ids.SNOOT_SUBDIVISION, ids.SNOOT_GROUP_FIT, "Corner Subdivision",
     {"min": 1, "max": 64}),

    ("group", ids.SNOOT_GROUP_SIZE, ROOT, "Light Size", {"open": False}),
    ("cycle", ids.SNOOT_SIZE_MODE, ids.SNOOT_GROUP_SIZE, "Size",
     {"items": ((ids.SNOOT_SIZE_MODE_LIGHT, "From Light"),
                (ids.SNOOT_SIZE_MODE_MANUAL, "Manual"))}),
    ("real", ids.SNOOT_SIZE_X, ids.SNOOT_GROUP_SIZE, "Manual Width",
     {"unit": "meter", "min": 0.0, "max": 100000.0, "step": 1.0}),
    ("real", ids.SNOOT_SIZE_Y, ids.SNOOT_GROUP_SIZE, "Manual Height",
     {"unit": "meter", "min": 0.0, "max": 100000.0, "step": 1.0}),

    ("group", ids.SNOOT_GROUP_RENDER, ROOT, "Render", {"open": True}),
    ("cycle", ids.SNOOT_RENDERER, ids.SNOOT_GROUP_RENDER, "Renderer",
     {"items": ((ids.SNOOT_RENDERER_AUTO, "Auto"),
                (ids.SNOOT_RENDERER_REDSHIFT, "Redshift"),
                (ids.SNOOT_RENDERER_ARNOLD, "Arnold"),
                (ids.SNOOT_RENDERER_OCTANE, "Octane"),
                (ids.SNOOT_RENDERER_STANDARD, "Standard / Physical"))}),
    ("button", ids.SNOOT_SETUP_RENDER, ids.SNOOT_GROUP_RENDER,
     "Set Up Materials and Visibility", {}),
)

TAB_NAME = "Snoot"


def _dtype(kind):
    return {
        "group": c4d.DTYPE_GROUP,
        "real": c4d.DTYPE_REAL,
        "bool": c4d.DTYPE_BOOL,
        "long": c4d.DTYPE_LONG,
        "cycle": c4d.DTYPE_LONG,
        "button": c4d.DTYPE_BUTTON,
        "static": c4d.DTYPE_STATICTEXT,
    }[kind]


def desc_id(kind, param_id):
    return c4d.DescID(c4d.DescLevel(param_id, _dtype(kind), 0))


def _container(kind, label, options):
    bc = c4d.GetCustomDataTypeDefault(_dtype(kind))
    bc[c4d.DESC_NAME] = label
    bc[c4d.DESC_SHORT_NAME] = label
    if kind == "group":
        bc[c4d.DESC_COLUMNS] = 1
        bc[c4d.DESC_DEFAULT] = 1 if options.get("open") else 0
    elif kind in ("real", "long"):
        if "unit" in options:
            bc[c4d.DESC_UNIT] = {"meter": c4d.DESC_UNIT_METER,
                                 "percent": c4d.DESC_UNIT_PERCENT}[options["unit"]]
        if "min" in options:
            bc[c4d.DESC_MIN] = options["min"]
        if "max" in options:
            bc[c4d.DESC_MAX] = options["max"]
        if "step" in options:
            bc[c4d.DESC_STEP] = options["step"]
        if "slider" in options:
            bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_REALSLIDER
            bc[c4d.DESC_MINSLIDER], bc[c4d.DESC_MAXSLIDER] = options["slider"]
    elif kind == "cycle":
        items = c4d.BaseContainer()
        for value, text in options["items"]:
            items.SetString(value, text)
        bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_CYCLE
        bc.SetContainer(c4d.DESC_CYCLE, items)
    elif kind == "button":
        bc[c4d.DESC_CUSTOMGUI] = c4d.CUSTOMGUI_BUTTON
    return bc


def build(description, info_text):
    """Add the Snoot parameters to a loaded object description."""
    root = c4d.DescID(c4d.DescLevel(c4d.ID_OBJECTPROPERTIES))
    tab = description.GetParameterI(root, None)
    if tab is None:
        # No object tab in the loaded description: create it at the top level.
        tab = _container("group", TAB_NAME, {"open": True})
        description.SetParameter(root, tab, getattr(c4d, "DESCID_ROOT", c4d.DescID()))
    else:
        tab[c4d.DESC_NAME] = TAB_NAME
        tab[c4d.DESC_SHORT_NAME] = TAB_NAME
        tab[c4d.DESC_DEFAULT] = 1
    parents = {ROOT: root}
    for kind, param_id, parent, label, options in LAYOUT:
        if param_id == ids.SNOOT_INFO:
            label = info_text
        entry = desc_id(kind, param_id)
        description.SetParameter(entry, _container(kind, label, options), parents[parent])
        if kind == "group":
            parents[param_id] = entry
