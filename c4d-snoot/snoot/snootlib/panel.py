"""Dockable Snoot panel with every shape control in one place.

It edits the selected Snoot objects and the snoots mounted on selected
lights, so the light itself can stay selected while the beam is shaped.
Open it from Extensions > Snoot Panel; it can be docked into a layout.
"""

import c4d

from . import actions, ids, lights, render_setup

G_STATUS = 5000
G_LENGTH = 5001
G_OPENING_X = 5002
G_OPENING_Y = 5003
G_ROUNDNESS = 5004
G_THICKNESS = 5005
G_PADDING = 5006
G_OFFSET = 5007
G_UNIFORM = 5010
G_FLIP = 5011
G_ADD = 5020
G_SETUP = 5021
_LABEL = 100  # label gadget = control gadget + _LABEL

# gadget: (param, label, format, min, max, slider min, slider max, step)
# Percent values are fractions (1.0 = 100%), distances are centimetres.
_FLOATS = {
    G_LENGTH: (ids.SNOOT_LENGTH, "Length", c4d.FORMAT_METER, 0.0, 100000.0, 0.0, 500.0, 1.0),
    G_OPENING_X: (ids.SNOOT_OPENING_X, "Opening Width", c4d.FORMAT_PERCENT, 0.01, 10.0, 0.1, 2.0, 0.01),
    G_OPENING_Y: (ids.SNOOT_OPENING_Y, "Opening Height", c4d.FORMAT_PERCENT, 0.01, 10.0, 0.1, 2.0, 0.01),
    G_ROUNDNESS: (ids.SNOOT_ROUNDNESS, "Opening Roundness", c4d.FORMAT_PERCENT, 0.0, 1.0, 0.0, 1.0, 0.01),
    G_THICKNESS: (ids.SNOOT_THICKNESS, "Wall Thickness", c4d.FORMAT_METER, 0.01, 1000.0, 0.01, 5.0, 0.1),
    G_PADDING: (ids.SNOOT_PADDING, "Padding", c4d.FORMAT_METER, 0.0, 1000.0, 0.0, 10.0, 0.1),
    G_OFFSET: (ids.SNOOT_OFFSET, "Offset", c4d.FORMAT_METER, -100000.0, 100000.0, -50.0, 50.0, 1.0),
}

_INDRAG = getattr(c4d, "BFM_ACTION_INDRAG", None)


def _mouse_down():
    state = c4d.BaseContainer()
    if c4d.gui.GetInputState(c4d.BFM_INPUT_MOUSE, c4d.BFM_INPUT_MOUSELEFT, state):
        return state.GetInt32(c4d.BFM_INPUT_VALUE) == 1
    return False


class SnootPanel(c4d.gui.GeDialog):

    def __init__(self):
        super(SnootPanel, self).__init__()
        self._in_drag = False
        self._uniform = True

    # -- Layout --------------------------------------------------------------

    def CreateLayout(self):
        self.SetTitle("Snoot")
        self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1)
        self.GroupBorderSpace(8, 6, 8, 8)
        self.AddStaticText(G_STATUS, c4d.BFH_SCALEFIT, name="")

        self._section("Opening")
        self._slider(G_LENGTH)
        self._slider(G_OPENING_X)
        self._slider(G_OPENING_Y)
        self._checkbox(G_UNIFORM, "Uniform Opening")
        self._slider(G_ROUNDNESS)
        self.GroupEnd()

        self._section("Fit")
        self._slider(G_THICKNESS)
        self._slider(G_PADDING)
        self._slider(G_OFFSET)
        self._checkbox(G_FLIP, "Flip Direction")
        self.GroupEnd()

        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2)
        self.AddButton(G_ADD, c4d.BFH_SCALEFIT, name="Add Snoot to Light")
        self.AddButton(G_SETUP, c4d.BFH_SCALEFIT, name="Set Up Materials")
        self.GroupEnd()

        self.GroupEnd()
        return True

    def _section(self, title):
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, title=title)
        self.GroupBorder(c4d.BORDER_GROUP_IN | getattr(c4d, "BORDER_WITH_TITLE", 0))
        self.GroupBorderSpace(6, 4, 6, 6)

    def _slider(self, gadget):
        self.AddStaticText(gadget + _LABEL, c4d.BFH_LEFT, name=_FLOATS[gadget][1])
        self.AddEditSlider(gadget, c4d.BFH_SCALEFIT, initw=160)

    def _checkbox(self, gadget, label):
        self.AddStaticText(gadget + _LABEL, c4d.BFH_LEFT, name="")
        self.AddCheckbox(gadget, c4d.BFH_LEFT, 0, 0, label)

    def InitValues(self):
        self.SetBool(G_UNIFORM, self._uniform)
        self.refresh()
        return True

    # -- Sync ----------------------------------------------------------------

    def refresh(self):
        doc = c4d.documents.GetActiveDocument()
        snoots, bare_lights = actions.selection(doc) if doc is not None else ([], [])
        has_snoot = bool(snoots)
        for gadget in list(_FLOATS) + [G_UNIFORM, G_FLIP, G_SETUP]:
            self.Enable(gadget, has_snoot)
        self.Enable(G_ADD, bool(bare_lights))
        if has_snoot:
            snoot = snoots[0]
            for gadget in _FLOATS:
                self._set_float(gadget, snoot[_FLOATS[gadget][0]])
            self.SetBool(G_FLIP, bool(snoot[ids.SNOOT_FLIP]))
        self.SetString(G_STATUS, self._status(snoots, bare_lights))

    def _set_float(self, gadget, value):
        _param, _label, fmt, lo, hi, slider_lo, slider_hi, step = _FLOATS[gadget]
        self.SetFloat(gadget, float(value or 0.0), lo, hi, step, fmt, slider_lo, slider_hi)

    @staticmethod
    def _status(snoots, bare_lights):
        if len(snoots) > 1:
            return "Editing %d snoots" % len(snoots)
        if snoots:
            light = lights.parent_light(snoots[0])
            if light is None:
                return "Snoot is not mounted on a light"
            info = lights.read_light(light, allow_description_scan=True)
            return "%s: %s" % (light.GetName(), lights.describe(info))
        if bare_lights:
            return "%s has no snoot yet" % bare_lights[0].GetName()
        return "Select a light or a Snoot"

    def CoreMessage(self, id, msg):
        if id == c4d.EVMSG_CHANGE:
            if self._in_drag and not _mouse_down():
                self._in_drag = False
            if not self._in_drag:
                self.refresh()
        return c4d.gui.GeDialog.CoreMessage(self, id, msg)

    # -- Edits ---------------------------------------------------------------

    def _record_undo(self, msg):
        """One undo step per slider drag rather than one per mouse move."""
        in_drag = bool(msg is not None and _INDRAG is not None and msg.GetBool(_INDRAG))
        record = not self._in_drag
        self._in_drag = in_drag
        return record

    def Command(self, id, msg):
        if id == G_UNIFORM:
            self._uniform = self.GetBool(G_UNIFORM)
            return True
        doc = c4d.documents.GetActiveDocument()
        if doc is None:
            return True
        snoots, bare_lights = actions.selection(doc)

        if id == G_ADD:
            actions.add_snoots(doc, bare_lights)
            c4d.EventAdd()
            return True

        if id == G_SETUP:
            doc.StartUndo()
            try:
                for snoot in snoots:
                    render_setup.setup(doc, snoot, snoot[ids.SNOOT_RENDERER], manage_undo=False)
            finally:
                doc.EndUndo()
            c4d.EventAdd()
            return True

        changes = self._changes(id)
        if changes and snoots:
            actions.set_params(doc, snoots, changes, record_undo=self._record_undo(msg))
            c4d.EventAdd()
        return True

    def _changes(self, gadget):
        if gadget == G_FLIP:
            return {ids.SNOOT_FLIP: self.GetBool(G_FLIP)}
        if gadget not in _FLOATS:
            return {}
        value = self.GetFloat(gadget)
        changes = {_FLOATS[gadget][0]: value}
        if self._uniform and gadget in (G_OPENING_X, G_OPENING_Y):
            other = G_OPENING_Y if gadget == G_OPENING_X else G_OPENING_X
            changes[_FLOATS[other][0]] = value
            self._set_float(other, value)
        return changes


_panel = None


def _get_panel():
    global _panel
    if _panel is None:
        _panel = SnootPanel()
    return _panel


def open_panel(plugin_id):
    panel = _get_panel()
    if panel.IsOpen():
        panel.refresh()
        return True
    return panel.Open(c4d.DLG_TYPE_ASYNC, pluginid=plugin_id, defaultw=340, defaulth=0)


def restore_panel(plugin_id, secret):
    return _get_panel().Restore(pluginid=plugin_id, secret=secret)
