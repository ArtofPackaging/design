"""Plugin and parameter IDs.

The parameter IDs mirror ``res/description/Osnoot.h``; tests/test_resources.py
checks that the two stay in sync.
"""

# Plugin IDs. 1000001-1000010 is the range Maxon reserves for development.
# Before distributing the plugin, replace these with two IDs registered at
# https://developers.maxon.net/forum/pid -- scenes saved with the development
# IDs will not load the Snoot object once the IDs change.
ID_SNOOT_OBJECT = 1000001
ID_ADD_SNOOT_COMMAND = 1000002

# Object tab
SNOOT_LENGTH = 1000
SNOOT_OPENING_X = 1001
SNOOT_OPENING_Y = 1002
SNOOT_ROUNDNESS = 1003
SNOOT_THICKNESS = 1004
SNOOT_SUBDIVISION = 1005

# Fit tab
SNOOT_GROUP_FIT = 1100
SNOOT_INFO = 1101
SNOOT_SIZE_MODE = 1102
SNOOT_SIZE_X = 1103
SNOOT_SIZE_Y = 1104
SNOOT_PADDING = 1105
SNOOT_OFFSET = 1106
SNOOT_FLIP = 1107

SNOOT_SIZE_MODE_LIGHT = 0
SNOOT_SIZE_MODE_MANUAL = 1

# Render tab
SNOOT_GROUP_RENDER = 1200
SNOOT_RENDERER = 1201
SNOOT_SETUP_RENDER = 1202

SNOOT_RENDERER_AUTO = 0
SNOOT_RENDERER_REDSHIFT = 1
SNOOT_RENDERER_ARNOLD = 2
SNOOT_RENDERER_OCTANE = 3
SNOOT_RENDERER_STANDARD = 4
