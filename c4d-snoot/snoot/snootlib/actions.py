"""Operations shared by the commands and the Snoot panel."""

import c4d

from . import ids, lights, render_setup

# Manual size used when a snoot is added to a light without an area size.
POINT_LIGHT_SIZE = 20.0


def is_snoot(obj):
    return obj is not None and obj.GetType() == ids.ID_SNOOT_OBJECT


def snoots_on(light):
    """Snoot objects directly under ``light``."""
    found = []
    child = light.GetDown()
    while child is not None:
        if is_snoot(child):
            found.append(child)
        child = child.GetNext()
    return found


def _append_unique(items, obj):
    if not any(obj == item for item in items):
        items.append(obj)


def selection(doc):
    """(snoots, bare_lights) for the current object selection.

    Selecting a light counts as selecting the snoots mounted on it; lights
    without a snoot are returned separately so a snoot can be added.
    """
    snoots, bare_lights = [], []
    for obj in doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN):
        if is_snoot(obj):
            _append_unique(snoots, obj)
        elif lights.is_light(obj):
            mounted = snoots_on(obj)
            for snoot in mounted:
                _append_unique(snoots, snoot)
            if not mounted:
                _append_unique(bare_lights, obj)
    return snoots, bare_lights


def create_snoot(light):
    """A new Snoot object configured for ``light`` (not inserted)."""
    snoot = c4d.BaseObject(ids.ID_SNOOT_OBJECT)
    if snoot is None:
        raise RuntimeError("Snoot object is not registered")
    snoot.SetName("Snoot")
    info = lights.read_light(light, allow_description_scan=True)
    # Start with an opening the same shape as the light.
    snoot[ids.SNOOT_ROUNDNESS] = lights.base_roundness(info)
    if not info.is_area:
        snoot[ids.SNOOT_SIZE_MODE] = ids.SNOOT_SIZE_MODE_MANUAL
        snoot[ids.SNOOT_SIZE_X] = POINT_LIGHT_SIZE
        snoot[ids.SNOOT_SIZE_Y] = POINT_LIGHT_SIZE
    if info.message:
        render_setup.log("'%s': %s" % (light.GetName(), lights.describe(info)))
    return snoot


def add_snoots(doc, targets):
    """Mount a snoot on each light in ``targets`` as one undo step.

    Sets up materials and visibility and selects the new snoots.
    """
    snoots = []
    doc.StartUndo()
    try:
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
    return snoots


def set_params(doc, snoots, changes, record_undo=True):
    """Apply ``{param_id: value}`` to every snoot.

    ``record_undo`` False skips the undo snapshot, for the later steps of a
    slider drag whose first step already recorded one.
    """
    if record_undo:
        doc.StartUndo()
        for snoot in snoots:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, snoot)
    for snoot in snoots:
        for param_id, value in changes.items():
            snoot[param_id] = value
    if record_undo:
        doc.EndUndo()
