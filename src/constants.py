"""Here are defined all global constants."""


import platform
from os.path import expanduser, join, pardir, normpath
from .version import __version__ as PROGVERSION


# FFGo-related constants

PROGNAME = 'FFGo'
NAME_WITH_VERSION = '{prg} {version}'.format(prg=PROGNAME, version=PROGVERSION)
USER_AGENT = \
 '{prg}/{version} ' \
 '(+http://people.via.ecp.fr/~flo/projects/FFGo/)'.format(
     prg=PROGNAME, version=PROGVERSION)
COPYRIGHT = "Copyright © 2009-2015\nRobert 'erobo' Leda <erobo@wp.pl>\n" \
            "Copyright © 2014-2015\nFlorent Rougon <f.rougon@free.fr>"
AUTHORS = 'Robert Leda\nFlorent Rougon'
LICENSE = \
    """This program is free software. It comes without any warranty, to
the extent permitted by applicable law. You can redistribute it
and/or modify it under the terms of the Do What The Fuck You Want
To Public License, Version 2, as published by Sam Hocevar. See
http://sam.zoy.org/wtfpl/COPYING for more details.
"""
# User's home directory.
HOME_DIR = expanduser('~')
# Default directory for user data files.
if platform.system() == "Windows":
    # normpath() converts / to \ on Windows, which can be useful when
    # displaying paths to users.
    USER_DATA_DIR = normpath(join(os.getenv("APPDATA", "C:/"), "FFGo"))
else:
    USER_DATA_DIR = join(HOME_DIR, '.ffgo')
# Place to store FG output logs.
LOG_DIR = join(USER_DATA_DIR, 'Logs')
# Path to airport data file.
APT = join(USER_DATA_DIR, 'apt')
# Path to locally installed airport list.
INSTALLED_APT = join(USER_DATA_DIR, 'apt_installed')
# Path to config file.
CONFIG = join(USER_DATA_DIR, 'config')
# To allow easy migration from FGo! to FFGo
FGO_CONFIG = join(HOME_DIR, '.fgo', 'config')

# Path to apt.dat.gz timestamp file.
APT_TIMESTAMP = join(USER_DATA_DIR, 'timestamp')
# Path to default config directory.
DATA_DIR = join(pardir, 'data')

DEFAULT_LOG_NAME = 'FlightGear.log'

DEFAULT_CONFIG_DIR = join(DATA_DIR, 'config')
# Path to config file with predefined settings.
PRESETS = join(DEFAULT_CONFIG_DIR, 'presets')
# Path to help directory.
HELP_DIR = join(DATA_DIR, 'help')
# Name of directory where localization files are stored.
LOCALE_DIR = join(DATA_DIR, 'locale')
# Name of localization file.
MESSAGES = 'messages'
# Path to substitutionary thumbnail.
NO_PIL_PIC = join(DATA_DIR, 'pics', 'thumbnail.ppm')
# Path to substitutionary thumbnail.
NO_THUMBNAIL_PIC = join(DATA_DIR, 'pics', 'thumbnail.jpg')
# Line used in config file.
CUT_LINE = ' INTERNAL OPTIONS ABOVE. EDIT CAREFULLY! '.center(80, 'x')
# Default aircraft.
DEFAULT_AIRCRAFT = 'c172p'
# Default airport.
DEFAULT_AIRPORT = 'KSFO'
# Tooltip delay in milliseconds.
TOOLTIP_DELAY = '600'
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
# Color to apply to rwy button when inactive.
GRAYED_OUT_COL = '#b2b2b2'
# Background color for various messages.
MESSAGE_BG_COL = '#fffeb2'
# Background color for various text windows.
TEXT_BG_COL = '#ffffff'


# FG related constants.

# FG_DATA/AI directory name.
AI_DIR = 'AI'
# FG_DATA/Aircraft directory name.
DEFAULT_AIRCRAFT_DIR = 'Aircraft'
# FG_DATA(or FG_SCENERY)/Airports directory name.
DEFAULT_AIRPORTS_DIR = 'Airports'
# FG_DATA/Airports/apt.dat.gz file path.
APT_DAT = join('Airports', 'apt.dat.gz')
# FG_DATA/Airports/apt.dat.gz file path.
METAR_DAT = join('Airports', 'metar.dat.gz')


__all__ = tuple(i for i in locals().keys() if i.isupper())
