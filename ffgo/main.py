#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, 2015  Florent Rougon
# Copyright (c) 2009-2014   Robert Leda
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

"""FFGo - a simple GUI launcher for the FlightGear flight simulator.

(forked from FGo!)

"""

from . import constants
from .constants import PROGNAME, PROGVERSION, LOCALE_DIR
import locale
import gettext
import sys
import os
import argparse
import tkinter


def earlyTkInit():
    master = tkinter.Tk()
    master.title(PROGNAME)
    return master

# When importing 'config', the 'infowindow' module is itself imported, which
# defines an InfoWindow class. This in turn requires the tkinter.Tk() object
# (at class definition time) because of the constructor's
# 'font=tkFont.nametofont("TkTextFont")' optional argument.
master = earlyTkInit()
from .config import Config, AbortConfig
from .gui.mainwindow import App


def processCommandLine():
    params = argparse.Namespace()

    parser = argparse.ArgumentParser(
        usage="""\
%(prog)s [OPTION ...]
Graphical launcher for the FlightGear flight simulator.""",
        description="""\
Start a graphical user interface to make it easy to launch fgfs, the
FlightGear executable, with suitable arguments.""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # I want --help but not -h (it might be useful for something else)
        add_help=False)

    parser.add_argument('--help', action="help",
                        help="display this message and exit")
    # The version text is not wrapped when using
    # formatter_class=argparse.RawDescriptionHelpFormatter
    parser.add_argument('--version', action='version',
                        version="{name} {version}\n{copyright}\n\n{license}"
                                .format(
                                    name=PROGNAME, version=PROGVERSION,
                                    copyright=constants.COPYRIGHT_HELP,
                                    license=constants.LICENSE))

    params = parser.parse_args(namespace=params)

    return params


def run(master):
    """Initialize the application."""
    global params
    params = processCommandLine()

    # Initialize config object (passing 'master' allows things such as
    # obtaining the screen dpi in Config methods using
    # master.winfo_fpixels('1i')).
    try:
        config = Config(master)
    except AbortConfig:
        # We have a temporary translation setup at this point, based on the
        # environment.
        print(_("{prg}: initialization of the configuration aborted. Exiting.")
              .format(prg=PROGNAME))
        sys.exit(1)

    if not config.language.get():
        # Allow localized error messages, proper encoding detection by
        # 'locale.getpreferredencoding(False)' which is used in many
        # places of the Python standard library, etc.
        locale.setlocale(locale.LC_ALL, '')
    else:
        locale.setlocale(locale.LC_CTYPE, '') # encoding only

    # Initialize main window.
    app = App(master, config)

    # Override the window close button in order to allow a controlled, clean
    # shutdown.
    master.protocol("WM_DELETE_WINDOW", app.quit)

    return master.mainloop()


def main():
    sys.exit(run(master))


if __name__ == '__main__':
    main()
