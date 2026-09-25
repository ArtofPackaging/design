"""Snoot for Cinema 4D.

A generator that mounts onto an area light and shapes its beam: a tube that
follows the light's size, with length, opening and roundness controls, four
viewport handles, white-inside / black-outside materials and camera-invisible
visibility for Redshift, Arnold, Octane and the Standard/Physical renderers.

Usage: select one or more area lights, run Extensions > Add Snoot to Light.
"""

import math
import os
import sys

import c4d

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

from snootlib import geometry, ids, lights, render_setup  # noqa: E402

HANDLE_COLOR = c4d.Vector(1.0, 0.55, 0.0)
HANDLE_HIGHLIGHT = c4d.Vector(1.0, 0.85, 0.35)
PHONG_ANGLE = math.radians(60.0)

# Manual size used when a snoot is added to a light without an area size.
POINT_LIGHT_SIZE = 20.0

_DEFAULTS = (
    (ids.SNOOT_LENGTH, 100.0),
    (ids.SNOOT_OPENING_X, 1.0),
    (ids.SNOOT_OPENING_Y, 1.0),
    (ids.SNOOT_ROUNDNESS, 0.0),
    (ids.SNOOT_THICKNESS, 0.5),
    (ids.SNOOT_SUBDIVISION, 8),
    (ids.SNOOT_SIZE_MODE, ids.SNOOT_SIZE_MODE_LIGHT),
    (ids.SNOOT_SIZE_X, 200.0),
    (ids.SNOOT_SIZE_Y, 200.0),
    (ids.SNOOT_PADDING, 0.5),
    (ids.SNOOT_OFFSET, 0.0),
    (ids.SNOOT_FLIP, False),
    (ids.SNOOT_RENDERER, ids.SNOOT_RENDERER_AUTO),
)
_DEFAULT_VALUES = dict(_DEFAULTS)

_HANDLE_FIELDS = {
    "length": ids.SNOOT_LENGTH,
    "opening_x": ids.SNOOT_OPENING_X,
    "opening_y": ids.SNOOT_OPENING_Y,
    "roundness": ids.SNOOT_ROUNDNESS,
}


def _get(op, param_id):
    value = op[param_id]
    return _DEFAULT_VALUES[param_id] if value is None else value


def _uses_manual_size(op, info):
    return (_get(op, ids.SNOOT_SIZE_MODE) == ids.SNOOT_SIZE_MODE_MANUAL
            or not lights.has_size(info))


def read_params(op, info):
    """SnootParams from the object's parameters and its light."""
    if _uses_manual_size(op, info):
        width, height = _get(op, ids.SNOOT_SIZE_X), _get(op, ids.SNOOT_SIZE_Y)
    else:
        width, height = info.width, info.height
    return geometry.SnootParams(
        width=float(width),
        height=float(height),
        length=float(_get(op, ids.SNOOT_LENGTH)),
        opening_x=float(_get(op, ids.SNOOT_OPENING_X)),
        opening_y=float(_get(op, ids.SNOOT_OPENING_Y)),
        roundness=float(_get(op, ids.SNOOT_ROUNDNESS)),
        thickness=float(_get(op, ids.SNOOT_THICKNESS)),
        padding=float(_get(op, ids.SNOOT_PADDING)),
        offset=float(_get(op, ids.SNOOT_OFFSET)),
        subdivision=int(_get(op, ids.SNOOT_SUBDIVISION)),
        flip=bool(_get(op, ids.SNOOT_FLIP)),
    )


def current_params(op):
    """Parameters for handles and drawing."""
    info = lights.read_light(
        lights.parent_light(op),
        allow_description_scan=c4d.threading.GeIsMainThread())
    return read_params(op, info)


def build_polygon_object(mesh):
    poly = c4d.PolygonObject(len(mesh.points), len(mesh.polygons))
    poly.SetAllPoints([c4d.Vector(*point) for point in mesh.points])

    uvw = c4d.UVWTag(len(mesh.polygons))
    for index, (polygon, uv) in enumerate(zip(mesh.polygons, mesh.uvs)):
        poly.SetPolygon(index, c4d.CPolygon(*polygon))
        uvw.SetSlow(index, *[c4d.Vector(u, v, 0.0) for u, v in uv])
    poly.InsertTag(uvw)

    for name, indices in ((geometry.INSIDE_SELECTION, mesh.inside),
                          (geometry.OUTSIDE_SELECTION, mesh.outside)):
        tag = c4d.SelectionTag(c4d.Tpolygonselection)
        tag.SetName(name)
        selection = tag.GetBaseSelect()
        for index in indices:
            selection.Select(index)
        poly.InsertTag(tag)

    phong = poly.MakeTag(c4d.Tphong)
    phong[c4d.PHONGTAG_PHONG_ANGLELIMIT] = True
    phong[c4d.PHONGTAG_PHONG_ANGLE] = PHONG_ANGLE

    poly.SetName("Snoot")
    poly.Message(c4d.MSG_UPDATE)
    return poly


class SnootObject(c4d.plugins.ObjectData):

    def __init__(self):
        super(SnootObject, self).__init__()
        self._signature = None

    def Init(self, node, isCloneInit=False):
        for param_id, value in _DEFAULTS:
            self.InitAttr(node, type(value), param_id)
        if not isCloneInit:
            for param_id, value in _DEFAULTS:
                node[param_id] = value
        return True

    # -- Geometry ------------------------------------------------------------

    def GetVirtualObjects(self, op, hh):
        # The light is read on every pass so resizing it rebuilds the snoot;
        # the params tuple is the cache signature.
        info = lights.read_light(
            lights.parent_light(op),
            allow_description_scan=c4d.threading.GeIsMainThread())
        params = read_params(op, info)
        dirty = (op.CheckCache(hh) or op.IsDirty(c4d.DIRTYFLAGS_DATA)
                 or params != self._signature)
        if not dirty:
            cache = op.GetCache(hh)
            if cache is not None:
                return cache
        self._signature = params
        return build_polygon_object(geometry.build_mesh(params))

    # -- Handles -------------------------------------------------------------

    def GetHandleCount(self, op):
        return geometry.HANDLE_COUNT

    def GetHandle(self, op, i, info):
        position, direction, _anchor = geometry.handles(current_params(op))[i]
        info.position = c4d.Vector(*position)
        info.direction = c4d.Vector(*direction)
        info.type = c4d.HANDLECONSTRAINTTYPE_LINEAR

    def SetHandle(self, op, i, p, info):
        changes = geometry.apply_handle(current_params(op), i, (p.x, p.y, p.z))
        for field, value in changes.items():
            op[_HANDLE_FIELDS[field]] = value

    def Draw(self, op, drawpass, bd, bh):
        if drawpass != c4d.DRAWPASS_HANDLES:
            return c4d.DRAWRESULT_SKIP
        bd.SetMatrix_Matrix(op, bh.GetMg())
        highlight = op.GetHighlightHandle(bd)
        for index, (position, _direction, anchor) in enumerate(
                geometry.handles(current_params(op))):
            point = c4d.Vector(*position)
            bd.SetPen(HANDLE_COLOR)
            bd.DrawLine(c4d.Vector(*anchor), point, 0)
            bd.SetPen(HANDLE_HIGHLIGHT if index == highlight else HANDLE_COLOR)
            bd.DrawHandle(point, c4d.DRAWHANDLE_BIG, 0)
        return c4d.DRAWRESULT_OK

    # -- Attribute Manager ---------------------------------------------------

    def GetDDescription(self, node, description, flags):
        if not description.LoadDescription(node.GetType()):
            return False
        info_id = c4d.DescID(c4d.DescLevel(ids.SNOOT_INFO, c4d.DTYPE_STATICTEXT, 0))
        single_id = description.GetSingleDescID()
        if single_id is None or info_id.IsPartOf(single_id)[0]:
            bc = description.GetParameterI(info_id, None)
            if bc is not None:
                bc[c4d.DESC_NAME] = self._info_text(node)
        return (True, flags | c4d.DESCFLAGS_DESC_LOADED)

    def GetDEnabling(self, node, id, t_data, flags, itemdesc):
        if id[0].id in (ids.SNOOT_SIZE_X, ids.SNOOT_SIZE_Y):
            info = lights.read_light(lights.parent_light(node), allow_description_scan=True)
            return _uses_manual_size(node, info)
        return True

    @staticmethod
    def _info_text(node):
        info = lights.read_light(lights.parent_light(node), allow_description_scan=True)
        text = lights.describe(info)
        if _get(node, ids.SNOOT_SIZE_MODE) == ids.SNOOT_SIZE_MODE_MANUAL:
            return text + "  - manual size"
        if not lights.has_size(info):
            return text + "  - using manual size"
        return text

    def Message(self, node, type, data):
        if type == c4d.MSG_DESCRIPTION_COMMAND and isinstance(data, dict):
            desc_id = data.get("id")
            if desc_id is not None and desc_id[0].id == ids.SNOOT_SETUP_RENDER:
                doc = node.GetDocument()
                if doc is not None:
                    used = render_setup.setup(doc, node, _get(node, ids.SNOOT_RENDERER))
                    render_setup.log("Set up %s materials and visibility on '%s'."
                                     % (render_setup.renderer_label(used), node.GetName()))
                    c4d.EventAdd()
        return True


def create_snoot(light):
    """A new Snoot object configured for ``light`` (not inserted)."""
    snoot = c4d.BaseObject(ids.ID_SNOOT_OBJECT)
    if snoot is None:
        raise RuntimeError("Snoot object is not registered")
    snoot.SetName("Snoot")
    info = lights.read_light(light, allow_description_scan=True)
    if info.shape == lights.SHAPE_DISC:
        snoot[ids.SNOOT_ROUNDNESS] = 1.0
    elif info.roundness:
        snoot[ids.SNOOT_ROUNDNESS] = max(0.0, min(1.0, info.roundness))
    if not info.is_area:
        snoot[ids.SNOOT_SIZE_MODE] = ids.SNOOT_SIZE_MODE_MANUAL
        snoot[ids.SNOOT_SIZE_X] = POINT_LIGHT_SIZE
        snoot[ids.SNOOT_SIZE_Y] = POINT_LIGHT_SIZE
    if info.message:
        render_setup.log("'%s': %s" % (light.GetName(), lights.describe(info)))
    return snoot


class AddSnootCommand(c4d.plugins.CommandData):

    def Execute(self, doc):
        targets = [obj for obj in doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)
                   if lights.is_light(obj)]
        if not targets:
            c4d.gui.MessageDialog(
                "Select an area light (Cinema 4D, Octane, Redshift or Arnold) "
                "to attach a snoot to.")
            return True

        doc.StartUndo()
        try:
            snoots = []
            for light in targets:
                snoot = create_snoot(light)
                doc.InsertObject(snoot, parent=light)
                doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, snoot)
                used = render_setup.setup(doc, snoot, manage_undo=False)
                render_setup.log("Added a snoot to '%s' (%s materials)."
                                 % (light.GetName(), render_setup.renderer_label(used)))
                snoots.append(snoot)

            for light in targets:
                doc.AddUndo(c4d.UNDOTYPE_BITS, light)
            for index, snoot in enumerate(snoots):
                doc.SetActiveObject(snoot, c4d.SELECTION_NEW if index == 0 else c4d.SELECTION_ADD)
        finally:
            doc.EndUndo()
        c4d.EventAdd()
        return True

    def GetState(self, doc):
        return c4d.CMD_ENABLED


def _load_icon():
    bitmap = c4d.bitmaps.BaseBitmap()
    path = os.path.join(_PLUGIN_DIR, "res", "icons", "snoot.png")
    if bitmap.InitWith(path)[0] != c4d.IMAGERESULT_OK:
        return None
    return bitmap


if __name__ == "__main__":
    icon = _load_icon()
    c4d.plugins.RegisterObjectPlugin(
        id=ids.ID_SNOOT_OBJECT,
        str="Snoot",
        g=SnootObject,
        description="Osnoot",
        icon=icon,
        info=c4d.OBJECT_GENERATOR | c4d.PLUGINFLAG_HIDEPLUGINMENU,
    )
    c4d.plugins.RegisterCommandPlugin(
        id=ids.ID_ADD_SNOOT_COMMAND,
        str="Add Snoot to Light",
        info=0,
        icon=icon,
        help="Attach a Snoot to the selected area light(s)",
        dat=AddSnootCommand(),
    )
