"""Plugin and parameter IDs.

The Snoot tab is built from the parameter IDs in snootlib/ui.py.
"""

# Plugin IDs. 1000001-1000010 is the range Maxon reserves for development,
# shared by every in-development plugin, so it collides easily (Megapixels
# uses 1000001). Snoot takes the top of the range. Replace these with two IDs
# registered at https://developers.maxon.net/forum/pid -- scenes saved with
# the development IDs will not load the Snoot object once the IDs change.
ID_SNOOT_OBJECT = 1000009
ID_ADD_SNOOT_COMMAND = 1000010

# Parameter IDs start at 10000, well clear of the base object's own IDs.
# The Snoot tab is built from these in snootlib/ui.py.

# Snoot tab
SNOOT_GROUP_MAIN = 10000
SNOOT_INFO = 10001

# Opening section
SNOOT_GROUP_OPENING = 10010
SNOOT_LENGTH = 10011
SNOOT_OPENING_X = 10012
SNOOT_OPENING_Y = 10013
SNOOT_UNIFORM = 10014
SNOOT_ROUNDNESS = 10015

# Fit section
SNOOT_GROUP_FIT = 10020
SNOOT_THICKNESS = 10021
SNOOT_PADDING = 10022
SNOOT_OFFSET = 10023
SNOOT_FLIP = 10024
SNOOT_SUBDIVISION = 10025

# Light Size section
SNOOT_GROUP_SIZE = 10030
SNOOT_SIZE_MODE = 10031
SNOOT_SIZE_X = 10032
SNOOT_SIZE_Y = 10033

SNOOT_SIZE_MODE_LIGHT = 0
SNOOT_SIZE_MODE_MANUAL = 1

# Render section
SNOOT_GROUP_RENDER = 10040
SNOOT_RENDERER = 10041
SNOOT_SETUP_RENDER = 10042

SNOOT_RENDERER_AUTO = 0
SNOOT_RENDERER_REDSHIFT = 1
SNOOT_RENDERER_ARNOLD = 2
SNOOT_RENDERER_OCTANE = 3
SNOOT_RENDERER_STANDARD = 4
