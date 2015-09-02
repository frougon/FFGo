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

from .constants import PROGNAME, LOCALE_DIR
import locale
import gettext
import sys
import os
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


def promptToNotUseCli():
    message = _("""Usage: ffgo

This program does not use command line options for now. Edit the
ffgo/data/config/presets file if you need to run {prg} with some
pre-configuration.""").format(prg=PROGNAME)

    if len(sys.argv) > 1:
        print(message + '\n')


def run(master):
    """Initialize the application."""
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

    promptToNotUseCli()
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
