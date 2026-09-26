# Snoot for Cinema 4D

A Python plugin that mounts a snoot on an area light to shape its beam. It is
modelled on Greyscalegorilla's Snoot:

- A tube generator that sits on the light and follows its size. Resize the
  light and the snoot resizes with it. The end attached to the light always
  keeps the light's own shape and size.
- **Length** (throw), **Opening Width / Height** (the size of the far opening,
  tapered or flared) and **Opening Roundness** (square corners to fully
  rounded; a square opening becomes a circle, a rectangular one a slot).
- All controls in one **Snoot** tab on the object, plus four orange viewport
  handles.
- White-inside, black-outside materials created natively for **Redshift**,
  **Arnold** and **Octane**, with Standard materials as a fallback.
- The snoot is hidden from the camera but still casts shadows, so it blocks
  light without appearing in the render (Octane Object tag under Octane,
  Compositing tag for the other renderers).

## Install

1. Copy the `snoot` folder into your Cinema 4D plugins folder. Either:
   - add its parent folder under *Preferences > Plugins > Plugins > Add Folder*, or
   - copy it into the user plugins folder (*Preferences > Open Preferences Folder…* > `plugins`).
2. Restart Cinema 4D.

Requires Cinema 4D 2023 or later (Python 3).

## Use

1. Select one or more lights.
2. Run *Extensions > Add Snoot to Light*.

The command adds a **Snoot** object as a child of each light, selects it so
its **Snoot** tab is showing in the Attribute Manager, picks the renderer, and
then:

- creates `Snoot Inside (<Renderer>)` / `Snoot Outside (<Renderer>)` materials
  (reusing them if they already exist in the scene) and assigns them to the
  `SnootInside` / `SnootOutside` polygon selections;
- hides the snoot from the camera while keeping its shadows: with Octane an
  Octane Object tag (*Camera visibility* off, *Shadow visibility* on), with
  Redshift, Arnold and Standard/Physical a Compositing tag (*Seen by Camera*
  off, *Cast Shadows* on);
- for Standard/Physical renders, switches the light's shadow from *None* to
  *Area*, because the snoot can only block light that casts shadows.

To switch renderer later, pick one under *Render > Renderer* in the Snoot
tab and press **Set Up Materials and Visibility**.

### The Snoot tab

Select the Snoot object (the child of the light) to see its **Snoot** tab in
the Attribute Manager. The status line at the top shows the light it found and
the size it read. Below it:

| Section | Parameter | Meaning |
| --- | --- | --- |
| Opening | Length | How far the snoot extends in front of the light (the throw). |
| | Opening Width / Height | Size of the far opening relative to the base. Below 100% narrows the beam; above 100% flares it. Different values turn a circle into a slot. |
| | Uniform Opening | On by default: the height follows the width, so the opening scales in proportion to the light. Turn it off to set the height separately. |
| | Opening Roundness | Corners of the far opening: 0% square, 100% fully rounded. The base always matches the light (rectangle, disc, or an Arnold quad's own roundness). |
| Fit | Wall Thickness | Thickness of the snoot wall. |
| | Padding | Gap between the light's edge and the inner wall. |
| | Offset | Moves the snoot's base along the light axis. |
| | Flip Direction | Points the snoot along -Z instead of +Z. |
| | Corner Subdivision | Segments per rounded corner. |
| Light Size | Size | *From Light* follows the light, *Manual* uses Manual Width/Height. Collapsed by default. |
| Render | Renderer | *Auto* uses the light's renderer (Redshift/Arnold/Octane light), otherwise the document's render engine. |
| | Set Up Materials and Visibility | Creates or reassigns the materials and visibility tags. |

The snoot must be a **direct child** of the light. If it cannot read the
light's size (for example on a spot or point light), it uses Manual
Width/Height, and the status line says so.

## Supported lights

| Light | Size read from |
| --- | --- |
| Cinema 4D area light (rectangle, disc; other shapes use Size X/Y) | `LIGHT_AREADETAILS_SIZEX/SIZEY` |
| Octane area light (Cinema 4D light + Octane Light tag) | same as above |
| Arnold quad / disk light (C4DtoA) | `quad_light.width/height`, `disk_light.radius` |
| Redshift light, area type | the Redshift `REDSHIFT_LIGHT_*AREA*SIZE*` parameters, found by name at runtime |

C4DtoA derives parameter IDs from Arnold names: the ID is
`abs(int32(djb2("node.param")))`. `lights.c4dtoa_id()` reproduces the
published C4DtoA constants (for example `C4DAIP_QUAD_LIGHT_WIDTH = 2034436501`),
and the tests check 28 of them.

## Verification status

This plugin was written and tested **outside Cinema 4D**, so read this before
relying on it in production.

| Part | Status |
| --- | --- |
| Snoot geometry, UVs, selections, handle math (`snootlib/geometry.py`) | Unit tested: closed, consistently wound shell, correct normals, handle round trips, round-to-slot welding. |
| Light size detection (`snootlib/lights.py`) | Unit tested against a stand-in `c4d` module. Cinema 4D and Arnold IDs are known values; **Redshift symbol names are matched by pattern and have not been checked against a live Redshift install.** |
| Resource files (`res/`) | Checked for consistency with `ids.py`. **In the first Cinema 4D test the parameters did not load** (the Attribute Manager showed only Basic/Coordinates). The IDs have since moved to 10000+ and the status line can no longer break the tab; not yet re-tested. If the tab is still missing, the Console prints `[Snoot] Could not load the Snoot parameters`. |
| Object/command plugin, handles, drawing (`snoot.pyp`) | Loaded and used in Cinema 4D with Octane (first user test). |
| Redshift and Arnold node materials | Built on the node-material API (`CreateDefaultGraph` + base colour port). **Not yet run.** If anything fails, the snoot falls back to Standard materials and logs why in the Console. |
| Octane material and Object tag | Uses the Octane material type/diffuse colour symbols and finds the Object tag's visibility switches by name. **Not yet run.** Same fallback. |
| Visibility | Octane: Octane Object tag, confirmed hiding the snoot in an Octane render. Redshift/Arnold/Standard: Compositing tag; Redshift and Arnold are expected to honour it, check the first render. |

Known open points:

- **Plugin IDs.** `snootlib/ids.py` uses 1000001 and 1000002 from Maxon's
  development range. Register two IDs at <https://developers.maxon.net/forum/pid>
  and replace them before sharing the plugin. Scenes saved with the old IDs
  will not load the Snoot object after the change.
- **Redshift size convention.** Redshift's area size is assumed to be the
  full width and height. If the snoot comes out half the size of the light,
  switch *Size* to *Manual* and report it so the lookup can be fixed.
- Lights are assumed to emit along their local +Z axis, which is the
  convention for all four renderers. *Flip Direction* covers the exception.

## Development

```sh
python3 -m unittest discover -s tests   # geometry, lights, actions, resources
python3 tools/make_icon.py              # regenerate res/icons/snoot.png
```

Layout:

```
snoot/                     <- the plugin folder you install
  snoot.pyp                object + command plugins
  snootlib/actions.py      add snoots to lights
  snootlib/geometry.py     mesh + handles (no c4d dependency)
  snootlib/lights.py       light detection and size lookup
  snootlib/render_setup.py materials, tags, shadows
  snootlib/ids.py          plugin and parameter IDs
  res/                     description, strings, icon
tests/                     unit tests (run without Cinema 4D)
tools/make_icon.py         icon generator
```
