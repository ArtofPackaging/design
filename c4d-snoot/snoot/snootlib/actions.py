"""Adding snoots to lights."""

import c4d

from . import ids, lights, render_setup

# Manual size used when a snoot is added to a light without an area size.
POINT_LIGHT_SIZE = 20.0


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
