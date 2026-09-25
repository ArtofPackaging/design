"""Materials, visibility and shadow setup for a snoot.

``setup`` creates (or reuses) a white inside / black outside material pair
for the chosen renderer, assigns them to the snoot's polygon selections,
hides the snoot from the camera while keeping it in shadow rays, and makes
sure the light casts shadows.

Each renderer path is guarded: if a renderer's material cannot be built
(plugin missing, API changed), the snoot falls back to Cinema 4D Standard
materials and the reason is printed to the Console.
"""

import c4d

from . import geometry, ids, lights

RENDERER_REDSHIFT = "redshift"
RENDERER_ARNOLD = "arnold"
RENDERER_OCTANE = "octane"
RENDERER_STANDARD = "standard"

_LABELS = {
    RENDERER_REDSHIFT: "Redshift",
    RENDERER_ARNOLD: "Arnold",
    RENDERER_OCTANE: "Octane",
    RENDERER_STANDARD: "Standard",
}

_CHOICES = {
    ids.SNOOT_RENDERER_REDSHIFT: RENDERER_REDSHIFT,
    ids.SNOOT_RENDERER_ARNOLD: RENDERER_ARNOLD,
    ids.SNOOT_RENDERER_OCTANE: RENDERER_OCTANE,
    ids.SNOOT_RENDERER_STANDARD: RENDERER_STANDARD,
}

# Render engine IDs stored in RDATA_RENDERENGINE.
_ENGINES = {
    1036219: RENDERER_REDSHIFT,
    1029988: RENDERER_ARNOLD,
    1029525: RENDERER_OCTANE,
}

INSIDE_COLOR = (0.9, 0.9, 0.9)
OUTSIDE_COLOR = (0.0, 0.0, 0.0)

REDSHIFT_NODESPACE = "com.redshift3d.redshift4c4d.class.nodespace"
ARNOLD_NODESPACE = "com.autodesk.arnold.nodespace"

# Candidate base colour ports: Redshift Standard Material (2024+), Redshift
# Material (older default graph), Arnold standard_surface.
_BASE_COLOR_PORTS = {
    REDSHIFT_NODESPACE: (
        "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color",
        "com.redshift3d.redshift4c4d.nodes.core.material.diffuse_color",
    ),
    ARNOLD_NODESPACE: (
        "base_color",
        "com.autodesk.arnold.shader.standard_surface.base_color",
    ),
}

ID_OCTANE_MATERIAL = 1029501
OCT_MAT_TYPE_DIFFUSE = 2510
ID_OCTANE_OBJECT_TAG = 1029603


def log(message):
    print("[Snoot] %s" % message)


def renderer_label(renderer):
    return _LABELS.get(renderer, renderer)


def resolve_renderer(doc, light, choice=ids.SNOOT_RENDERER_AUTO):
    """Map the Renderer dropdown to a renderer, resolving Auto.

    Auto prefers the light's own renderer, then the document's render engine.
    """
    if choice in _CHOICES:
        return _CHOICES[choice]
    kind = lights.light_kind(light)
    if kind in (lights.KIND_REDSHIFT, lights.KIND_ARNOLD, lights.KIND_OCTANE):
        return kind
    render_data = doc.GetActiveRenderData() if doc is not None else None
    if render_data is not None:
        return _ENGINES.get(render_data[c4d.RDATA_RENDERENGINE], RENDERER_STANDARD)
    return RENDERER_STANDARD


def setup(doc, snoot, choice=ids.SNOOT_RENDERER_AUTO, manage_undo=True):
    """Materials, visibility and shadows for ``snoot``. Returns the renderer used.

    With ``manage_undo`` the changes form their own undo step; pass False
    when the caller already opened one.
    """
    light = lights.parent_light(snoot)
    renderer = resolve_renderer(doc, light, choice)
    if manage_undo:
        doc.StartUndo()
    try:
        inside, outside, used = _material_pair(doc, renderer)
        _assign(doc, snoot, inside, geometry.INSIDE_SELECTION)
        _assign(doc, snoot, outside, geometry.OUTSIDE_SELECTION)
        _visibility(doc, snoot, renderer)
        _light_shadows(doc, light, renderer)
    finally:
        if manage_undo:
            doc.EndUndo()
    return used


# -- Materials --------------------------------------------------------------

def _material_pair(doc, renderer):
    try:
        pair = _get_or_build_pair(doc, renderer)
    except Exception as error:
        if renderer == RENDERER_STANDARD:
            raise
        log("Could not create %s materials (%s). Using Standard materials; "
            "replace them with %s materials by hand."
            % (renderer_label(renderer), error, renderer_label(renderer)))
        renderer = RENDERER_STANDARD
        pair = _get_or_build_pair(doc, renderer)

    # Insert only once both materials exist so a failure leaves no orphans.
    for mat, is_new in pair:
        if is_new:
            doc.InsertMaterial(mat)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, mat)
    return pair[0][0], pair[1][0], renderer


def _material_name(renderer, role):
    return "Snoot %s (%s)" % (role, renderer_label(renderer))


def _find_material(doc, name):
    mat = doc.GetFirstMaterial()
    while mat is not None:
        if mat.GetName() == name:
            return mat
        mat = mat.GetNext()
    return None


def _get_or_build_pair(doc, renderer):
    """[(inside, is_new), (outside, is_new)], reusing materials by name."""
    builder = {
        RENDERER_REDSHIFT: lambda c: _node_material(REDSHIFT_NODESPACE, c),
        RENDERER_ARNOLD: lambda c: _node_material(ARNOLD_NODESPACE, c),
        RENDERER_OCTANE: _octane_material,
        RENDERER_STANDARD: _standard_material,
    }[renderer]
    pair = []
    for role, color in (("Inside", INSIDE_COLOR), ("Outside", OUTSIDE_COLOR)):
        name = _material_name(renderer, role)
        existing = _find_material(doc, name)
        if existing is not None:
            pair.append((existing, False))
            continue
        mat = builder(color)
        mat.SetName(name)
        pair.append((mat, True))
    return pair


def _standard_material(color):
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat[c4d.MATERIAL_COLOR_COLOR] = c4d.Vector(*color)
    mat[c4d.MATERIAL_USE_REFLECTION] = False
    return mat


def _octane_material(color):
    mat = c4d.BaseMaterial(ID_OCTANE_MATERIAL)
    if mat is None:
        raise RuntimeError("Octane is not installed")
    type_id = getattr(c4d, "OCT_MATERIAL_TYPE", None)
    color_id = getattr(c4d, "OCT_MATERIAL_DIFFUSE_COLOR", None)
    if type_id is None or color_id is None:
        raise RuntimeError("Octane material parameters not found")
    mat[type_id] = getattr(c4d, "OCT_MAT_TYPE_DIFFUSE", OCT_MAT_TYPE_DIFFUSE)
    mat[color_id] = c4d.Vector(*color)
    return mat


def _node_material(nodespace, color):
    """Node material with the node space's default graph and its base colour set."""
    import maxon

    mat = c4d.BaseMaterial(c4d.Mmaterial)
    if mat is None:
        raise RuntimeError("could not allocate a material")
    node_material = mat.GetNodeMaterialReference()
    space = maxon.Id(nodespace)
    graph = node_material.CreateDefaultGraph(space)
    if graph is None or (hasattr(graph, "IsNullValue") and graph.IsNullValue()):
        raise RuntimeError("node space %s is not available" % nodespace)

    value = maxon.Color(*color)
    done = False
    with graph.BeginTransaction() as transaction:
        for node in _graph_nodes(graph):
            inputs = node.GetInputs()
            for port_id in _BASE_COLOR_PORTS[nodespace]:
                port = inputs.FindChild(port_id)
                if port is not None and port.IsValid():
                    if hasattr(port, "SetPortValue"):
                        port.SetPortValue(value)
                    else:  # 2023 and older
                        port.SetDefaultValue(value)
                    done = True
                    break
        transaction.Commit()
    if not done:
        raise RuntimeError("base colour port not found in the default %s graph" % nodespace)
    return mat


def _graph_nodes(graph):
    import maxon

    root = graph.GetViewRoot() if hasattr(graph, "GetViewRoot") else graph.GetRoot()
    if hasattr(root, "GetInnerNodes"):
        return list(root.GetInnerNodes(mask=maxon.NODE_KIND.NODE, includeThis=False))
    nodes = []
    root.GetChildren(nodes, maxon.NODE_KIND.NODE)
    return nodes


# -- Tags -------------------------------------------------------------------

def _append_tag(obj, tag):
    tags = obj.GetTags()
    obj.InsertTag(tag, tags[-1] if tags else None)


def _assign(doc, snoot, mat, selection):
    tag = None
    for candidate in snoot.GetTags():
        if (candidate.GetType() == c4d.Ttexture
                and candidate[c4d.TEXTURETAG_RESTRICTION] == selection):
            tag = candidate
            break
    if tag is None:
        tag = c4d.TextureTag()
        _append_tag(snoot, tag)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
    else:
        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, tag)
    tag.SetMaterial(mat)
    tag[c4d.TEXTURETAG_RESTRICTION] = selection
    tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW


def _get_or_add_tag(doc, obj, tag_type):
    tag = obj.GetTag(tag_type)
    if tag is not None:
        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, tag)
        return tag
    tag = c4d.BaseTag(tag_type)
    if tag is None:
        return None
    _append_tag(obj, tag)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
    return tag


def _visibility(doc, snoot, renderer):
    """Invisible to camera, still blocks light.

    The Compositing tag covers Standard/Physical, Redshift and Arnold. Octane
    reads its own Object tag, so that is configured as well.
    """
    tag = _get_or_add_tag(doc, snoot, c4d.Tcompositing)
    tag[c4d.COMPOSITINGTAG_SEENBYCAMERA] = False
    tag[c4d.COMPOSITINGTAG_CASTSHADOW] = True
    if renderer == RENDERER_OCTANE:
        _octane_visibility(doc, snoot)


def _octane_visibility(doc, snoot):
    existing = snoot.GetTag(ID_OCTANE_OBJECT_TAG)
    try:
        tag = existing if existing is not None else c4d.BaseTag(ID_OCTANE_OBJECT_TAG)
        camera = _find_bool_param(tag, ("camera", "visib"))
        shadow = _find_bool_param(tag, ("shadow", "visib"))
    except Exception as error:
        log("Octane Object tag unavailable (%s); set camera visibility by hand." % error)
        return
    if camera is None:
        log("Octane Object tag has no camera visibility parameter; set it by hand.")
        return
    if existing is None:
        _append_tag(snoot, tag)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)
    else:
        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, tag)
    tag[camera] = False
    if shadow is not None:
        tag[shadow] = True


def _find_bool_param(node, words):
    """DescID of the first BOOL parameter whose name contains all ``words``."""
    description = node.GetDescription(c4d.DESCFLAGS_DESC_NONE)
    for bc, param_id, _group in description:
        if param_id[0].dtype != c4d.DTYPE_BOOL:
            continue
        name = (bc[c4d.DESC_NAME] or "").lower()
        if all(word in name for word in words):
            return param_id
    return None


def _light_shadows(doc, light, renderer):
    """Standard/Physical lights default to no shadows; a snoot needs them."""
    if renderer != RENDERER_STANDARD or light is None or light.GetType() != lights.ID_OLIGHT:
        return
    if light[c4d.LIGHT_SHADOWTYPE] == c4d.LIGHT_SHADOWTYPE_NONE:
        doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, light)
        light[c4d.LIGHT_SHADOWTYPE] = c4d.LIGHT_SHADOWTYPE_AREA
        log("Enabled area shadows on '%s' so the snoot can block light." % light.GetName())
