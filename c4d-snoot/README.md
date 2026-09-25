# Snoot for Cinema 4D

A Python plugin that mounts a snoot on an area light to shape its beam. It is
modelled on Greyscalegorilla's Snoot:

- A tube generator that sits on the light and follows its size. Resize the
  light and the snoot resizes with it.
- **Length** (throw), **Opening Width / Height** (the size of the far opening,
  tapered or flared) and **Roundness** (square corners to fully rounded; a
  square light becomes a circle, a rectangular one a slot).
- Four orange viewport handles for length, opening width, opening height and
  roundness.
- White-inside, black-outside materials created natively for **Redshift**,
  **Arnold** and **Octane**, with Standard materials as a fallback.
- The snoot is hidden from the camera but still casts shadows, so it blocks
  light without appearing in the render.

## Install

1. Copy the `snoot` folder into your Cinema 4D plugins folder. Either:
   - add its parent folder under *Preferences > Plugins > Plugins > Add Folder*, or
   - copy it into the user plugins folder (*Preferences > Open Preferences Folder…* > `plugins`).
2. Restart Cinema 4D.

Requires Cinema 4D 2023 or later (Python 3).

## Use

1. Select one or more lights.
2. Run *Extensions > Add Snoot to Light*.

The command adds a **Snoot** object as a child of each light, picks the
renderer, and then:

- creates `Snoot Inside (<Renderer>)` / `Snoot Outside (<Renderer>)` materials
  (reusing them if they already exist in the scene) and assigns them to the
  `SnootInside` / `SnootOutside` polygon selections;
- adds a Compositing tag with *Seen by Camera* off and *Cast Shadows* on (and
  an Octane Object tag with camera visibility off when rendering with Octane);
- for Standard/Physical renders, switches the light's shadow from *None* to
  *Area*, because the snoot can only block light that casts shadows.

To switch renderer later, pick one under *Render > Renderer* on the Snoot and
press **Set Up Materials and Visibility**.

### Parameters

| Tab | Parameter | Meaning |
| --- | --- | --- |
| Object | Length | How far the snoot extends in front of the light (the throw). |
| | Opening Width / Height | Size of the far opening relative to the base. Below 100% narrows the beam; above 100% flares it. Different values turn a circle into a slot. |
| | Roundness | 0% gives square corners, 100% fully rounded corners. |
| | Wall Thickness | Thickness of the snoot wall. |
| | Corner Subdivision | Segments per rounded corner. |
| Fit | *(status line)* | Which light the snoot found and the size it read. |
| | Size | *From Light* follows the light, *Manual* uses Manual Width/Height. |
| | Padding | Gap between the light's edge and the inner wall. |
| | Offset | Moves the snoot's base along the light axis. |
| | Flip Direction | Points the snoot along -Z instead of +Z. |
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
| Resource files (`res/`) | Checked for consistency with `ids.py`; not yet loaded by Cinema 4D. |
| Object/command plugin, handles, drawing (`snoot.pyp`) | Written against the Cinema 4D Python SDK; **not yet run in Cinema 4D.** |
| Redshift and Arnold node materials | Built on the node-material API (`CreateDefaultGraph` + base colour port). **Not yet run.** If anything fails, the snoot falls back to Standard materials and logs why in the Console. |
| Octane material and Object tag | Uses the Octane material type/diffuse colour symbols and finds the Object tag's visibility switches by name. **Not yet run.** Same fallback. |
| Visibility | Compositing tag (*Seen by Camera* off, *Cast Shadows* on). Redshift and Arnold are expected to honour it; check the first render. |

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
python3 -m unittest discover -s tests   # geometry, light detection, resources
python3 tools/make_icon.py              # regenerate res/icons/snoot.png
```

Layout:

```
snoot/                     <- the plugin folder you install
  snoot.pyp                object + command plugins
  snootlib/geometry.py     mesh + handles (no c4d dependency)
  snootlib/lights.py       light detection and size lookup
  snootlib/render_setup.py materials, tags, shadows
  snootlib/ids.py          plugin and parameter IDs
  res/                     description, strings, icon
tests/                     unit tests (run without Cinema 4D)
tools/make_icon.py         icon generator
```
