"""Here are defined all global constants."""


import os
import platform
import textwrap
from os.path import expanduser, join, pardir, normpath

PROGNAME = 'FFGo'               # may be needed for some of these imports
from .version import __version__ as PROGVERSION
from . import misc
from .misc import resourceFilename


# FFGo-related constants
NAME_WITH_VERSION = '{prg} {version}'.format(prg=PROGNAME, version=PROGVERSION)
USER_AGENT = \
 '{prg}/{version} ' \
 '(+http://frougon.net/projects/FFGo/)'.format(
     prg=PROGNAME, version=PROGVERSION)
# See also COPYRIGHT_HELP below.
COPYRIGHT = "Copyright © 2009-2015  Robert 'erobo' Leda <erobo@wp.pl>\n" \
            "Copyright © 2014-2016  Florent Rougon <f.rougon@free.fr>"
# Format more suitable for --help output:
COPYRIGHT_HELP = textwrap.dedent("""\
  Copyright (c) 2009-2015  Robert 'erobo' Leda <erobo@wp.pl>
  Copyright (c) 2014-2020  Florent Rougon <f.rougon@free.fr>""")
AUTHORS = 'Robert Leda, Florent Rougon'
LICENSE = \
    """This program is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it
and/or modify it under the terms of the Do What The Fuck You Want
To Public License, Version 2, as published by Sam Hocevar. See
http://sam.zoy.org/wtfpl/COPYING for more details.
"""
# User's home directory.
HOME_DIR = expanduser('~')
# Default directories for user data files
if platform.system() == "Windows":
    USER_DATA_DIR = join(os.getenv("APPDATA", "C:/"), "FFGo")
else:
    USER_DATA_DIR = join(HOME_DIR, '.ffgo')

# normpath() converts / to \ on Windows, which can be useful when
# displaying paths to users.
USER_DATA_DIR = normpath(USER_DATA_DIR)

# Place to store FG output logs.
LOG_DIR = join(USER_DATA_DIR, 'Logs')
# Place to store some statistics (when each plane or airport was used...)
STATS_DIR = join(USER_DATA_DIR, 'Stats')
# File where statistics about airports are stored
AIRPORTS_STATS_FILE = join(STATS_DIR, "airports.json.gz")
# File where statistics about aircraft are stored (“aircrafts” shouldn't have
# an “s”, it is invariable...)
AIRCRAFT_STATS_FILE = join(STATS_DIR, "aircrafts.json.gz")
# Base name of the FlightGear executable (ends with '.exe' on Windows)
FG_EXECUTABLE = misc.executableFileName("fgfs")
# Path to airport data file.
APT = join(USER_DATA_DIR, 'apt')
# Path to locally installed airport list.
INSTALLED_APT = join(USER_DATA_DIR, 'apt_installed')
# Path to config file.
CONFIG = join(USER_DATA_DIR, 'config')
# To allow easy migration from FGo! to FFGo
FGO_CONFIG = join(HOME_DIR, '.fgo', 'config')

# Path to the obsolete (since apt digest file format version 4) timestamp file
# for the apt digest file. The timestamp is now stored inside the file.
OBSOLETE_APT_TIMESTAMP_FILE = join(USER_DATA_DIR, 'timestamp')

DEFAULT_LOG_NAME = 'FlightGear.log'

# Resource paths handled by the pkg_resources-style API implemented in misc.py
# must use the '/' separator, regardless of the platform.
DEFAULT_CONFIG_STEM = 'data/config/config_' # + two-letter language code
# Path to config file with predefined settings.
PRESETS = 'data/config/presets'

HELP_STEM = 'data/help/help_'   # + two-letter language code
# Name of directory where localization files are stored.
LOCALE_DIR = resourceFilename('data/locale')
# Name of localization file.
MESSAGES = 'FFGo'
# Seems to be the standard size for aircraft thumbnails in FlightGear
STD_AIRCRAFT_THUMBNAIL_SIZE = (171, 128) # (width, height) in pixels
# Path to substitutionary thumbnail (used when Pillow is not available).
# (apparently, Tkinter needs a file name [not a file-like object] when loading
# images without Pillow -> pkg_resources.resource_stream() doesn't work here)
NO_PIL_PIC = resourceFilename('data/pics/thumbnail-no-Pillow.gif')
# Substitutionary thumbnail (used when Pillow is installed but the aircraft has
# no thumbnail).
NO_THUMBNAIL_PIC = 'data/pics/thumbnail-not-avail.png'
# Line used in config file.
CUT_LINE = ' INTERNAL OPTIONS ABOVE. EDIT CAREFULLY! '.center(80, 'x')
# Default aircraft.
DEFAULT_AIRCRAFT = 'c172p'
# Default airport.
DEFAULT_AIRPORT = 'BIKF'
# Tooltip delay in milliseconds.
TOOLTIP_DELAY = '600'
# Standard width for automatically-wrapped tooltips.
AUTOWRAP_TOOLTIP_WIDTH = "400p"
# Used for the About box contents for instance...
STANDARD_TEXT_WRAP_WIDTH = "400p"
# Default value for the base font size in points. Should be 0, or in the range
# from MIN_BASE_FONT_SIZE to MAX_BASE_FONT_SIZE. 0 is special-cased by Tk and
# corresponds to a platform-dependent default size.
DEFAULT_BASE_FONT_SIZE = '0'
#  The minimum user-selectable value.
MIN_BASE_FONT_SIZE = '6'
#  The maximum user-selectable value.
MAX_BASE_FONT_SIZE = '36'


# Custom colors.

# Color to highlight background for carrier name in the main window.
CARRIER_COL = '#98afd9'
# Color to highlight comments in text window.
COMMENT_COL = '#0014a7'
# Background color for various messages.
MESSAGE_BG_COL = '#ededd1'
# Background color for tooltips.
TOOLTIP_BG_COL = '#ffffde'
# Background color for various text windows.
TEXT_BG_COL = '#ffffff'
# Colors for the FlightGear Output Window.
FG_OUTPUT_FG_COL = '#0014a7'
FG_OUTPUT_BG_COL = '#fffeb2'
# Background color of the FlightGear Command Window.
FG_COMMAND_BG_COL = '#eeeeec'
# Background color for the header line in popup menus (runway, parking...)
POPUP_HEADER_BG_COL = "#000066"

# FG related constants.

# $FG_ROOT/AI directory name.
AI_DIR = 'AI'
# $FG_ROOT/Aircraft directory name.
DEFAULT_AIRCRAFT_DIR = 'Aircraft'
# $FG_ROOT(or FG_SCENERY)/Airports directory name.
DEFAULT_AIRPORTS_DIR = 'Airports'
# $FG_ROOT/Airports/apt.dat.gz file path.
APT_DAT = join('Airports', 'apt.dat.gz')
# $FG_ROOT/Airports/apt.dat.gz file path.
METAR_DAT = join('Airports', 'metar.dat.gz')


__all__ = tuple(i for i in locals().keys() if i.isupper())
