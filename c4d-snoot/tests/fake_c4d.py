"""Minimal stand-in for the ``c4d`` module, enough to exercise lights.py and
the renderer resolution in render_setup.py outside Cinema 4D.

Constant values here are arbitrary except where lights.py relies on the real
ones (object type IDs), which it defines itself.
"""

import sys
import types


class DescLevel(object):
    def __init__(self, id, dtype=0, creator=0):
        self.id = id
        self.dtype = dtype
        self.creator = creator


class DescID(object):
    def __init__(self, *levels):
        self.levels = levels

    def __getitem__(self, index):
        return self.levels[index]

    def __eq__(self, other):
        return isinstance(other, DescID) and [l.id for l in self.levels] == [l.id for l in other.levels]

    def __hash__(self):
        return hash(tuple(l.id for l in self.levels))


class FakeNode(object):
    """Object/tag with a parameter dict, tags, a parent and a description."""

    def __init__(self, type_id, params=None, tags=(), description=(), name="node"):
        self.type_id = type_id
        self.params = dict(params or {})
        self.tags = list(tags)
        self.description = list(description)
        self.parent = None
        self.children = []
        self.name = name

    def GetType(self):
        return self.type_id

    def GetName(self):
        return self.name

    def GetTag(self, type_id):
        for tag in self.tags:
            if tag.GetType() == type_id:
                return tag
        return None

    def GetUp(self):
        return self.parent

    def GetDown(self):
        return self.children[0] if self.children else None

    def GetNext(self):
        if self.parent is None:
            return None
        siblings = self.parent.children
        index = siblings.index(self)
        return siblings[index + 1] if index + 1 < len(siblings) else None

    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        return child

    def SetName(self, name):
        self.name = name

    def GetDescription(self, flags):
        return iter(self.description)

    def _key(self, key):
        return key if not isinstance(key, DescID) else ("descid",) + tuple(l.id for l in key.levels)

    def __getitem__(self, key):
        return self.params.get(self._key(key))

    def __setitem__(self, key, value):
        self.params[self._key(key)] = value


class FakeRenderData(FakeNode):
    pass


class FakeDoc(object):
    def __init__(self, engine=0, active=()):
        self.render_data = FakeRenderData(0, {RDATA_RENDERENGINE: engine})
        self.active = list(active)
        self.undo_log = []

    def GetActiveRenderData(self):
        return self.render_data

    def GetActiveObjects(self, flags):
        return list(self.active)

    def StartUndo(self):
        self.undo_log.append("start")

    def AddUndo(self, kind, obj):
        self.undo_log.append((kind, obj))

    def EndUndo(self):
        self.undo_log.append("end")


def BaseObject(type_id):
    return FakeNode(type_id)


LIGHT_TYPE = 90000
LIGHT_TYPE_AREA = 8
LIGHT_TYPE_SPOT = 1
LIGHT_AREADETAILS_SHAPE = 90001
LIGHT_AREADETAILS_SHAPE_DISC = 0
LIGHT_AREADETAILS_SHAPE_RECTANGLE = 1
LIGHT_AREADETAILS_SHAPE_SPHERE = 2
LIGHT_AREADETAILS_SIZEX = 90002
LIGHT_AREADETAILS_SIZEY = 90003
RDATA_RENDERENGINE = 90004
GETACTIVEOBJECTFLAGS_CHILDREN = 2
UNDOTYPE_CHANGE_SMALL = 41

DESCFLAGS_DESC_NONE = 0
DTYPE_REAL = 19
DTYPE_BOOL = 400006001
DESC_NAME = 1
DESC_IDENT = 43


def install(extra_symbols=None):
    """Install a fresh fake ``c4d`` into sys.modules and return it."""
    module = types.ModuleType("c4d")
    for name, value in globals().items():
        if name.isupper() or name in ("DescID", "DescLevel", "BaseObject"):
            setattr(module, name, value)
    for name, value in (extra_symbols or {}).items():
        setattr(module, name, value)
    sys.modules["c4d"] = module
    # Re-import the c4d-dependent modules (and their caches) against the
    # fresh fake on the next import.
    package = sys.modules.get("snootlib")
    for name in list(sys.modules):
        if name.startswith("snootlib.") and name != "snootlib.geometry":
            del sys.modules[name]
            if package is not None and hasattr(package, name.split(".", 1)[1]):
                delattr(package, name.split(".", 1)[1])
    return module
