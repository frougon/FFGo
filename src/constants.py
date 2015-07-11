"""Here are defined all global constants."""


from os.path import expanduser, join, pardir


# FGo! related constants.

PROGNAME = 'FGo!'
NAME_WITH_VERSION = '{} 1.6.0 Alpha_log_and_command_window_test'.format(PROGNAME)
USER_AGENT = '{}/1.6.0 (+http://sites.google.com/site/erobosprojects/flightgear/add-ons/fgo)'.format(PROGNAME)
COPYRIGHT = "Copyright 2009-2015 by\nRobert 'erobo' Leda  <erobo@wp.pl>"
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
USER_DATA_DIR = join(HOME_DIR, '.fgo')
# Place to store FG output logs.
LOG_DIR = join(USER_DATA_DIR, 'Logs')
# Path to airport data file.
APT = join(USER_DATA_DIR, 'apt')
# Path to locally installed airport list.
INSTALLED_APT = join(USER_DATA_DIR, 'apt_installed')
# Path to config file.
CONFIG = join(USER_DATA_DIR, 'config')
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
