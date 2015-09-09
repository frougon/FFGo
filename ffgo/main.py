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

import locale
import gettext
import sys
import os
import argparse
import tkinter
import time
import platform
import traceback

from . import constants
from .constants import PROGNAME, PROGVERSION, LOCALE_DIR, LOG_DIR
from . import misc
# Make it clear this is not the 'logging' module from the standard library
from .logging import logger, LogLevel, allLogLevels

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

    parser.add_argument('--log-level', default="notice",
                        choices=allLogLevels,
                        help="""\
      only messages with the same or a higher priority will be printed to the
      terminal (default: %(default)s)""")
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
    # Initialize config object (passing 'master' allows things such as
    # obtaining the screen dpi in Config methods using
    # master.winfo_fpixels('1i')).
    try:
        config = Config(master)
    except AbortConfig:
        # We have a temporary translation setup at this point, based on the
        # environment.
        logger.criticalNP(
            _("{prg}: initialization of the configuration aborted. Exiting.")
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


def reportTkinterCallbackException(type_, val, tb):
    message = 'Error in a Tkinter callback'
    detail = ''.join(traceback.format_exception(type_, val, tb))
    logger.criticalNP('\n{}:\n{}'.format(message, detail))
    tkinter.messagebox.showerror(_('{prg}').format(prg=PROGNAME), message,
                                 detail=detail)


def main():
    global params

    params = processCommandLine()
    logger.logLevel = getattr(LogLevel, params.log_level)
    os.makedirs(LOG_DIR, exist_ok=True)

    with logger.open(os.path.join(LOG_DIR, PROGNAME + ".log"),
                     "w", encoding="utf-8"):
        timeFormatString = "%a, %d %b %Y %H:%M:%S %z"
        logger.logToFile("Starting {prg_with_ver} at {date}\n"
                         "Platform is {platform}\n"
                         "Python is {python_version}\n".format(
            prg_with_ver=constants.NAME_WITH_VERSION,
            date=time.strftime(timeFormatString),
            platform=platform.platform(),
            python_version=misc.pythonVersionString()))

        try:
            master.report_callback_exception = reportTkinterCallbackException
            res = run(master)
        except:
            logger.logToFile(traceback.format_exc())
            raise
        finally:
            # Locales weren't initialized for the start time, so let's be
            # consistent
            locale.setlocale(locale.LC_TIME, 'C')
            logger.logToFile("{prg} terminated at {date}.".format(
                prg=PROGNAME, date=time.strftime(timeFormatString)))

    sys.exit(res)


if __name__ == '__main__':
    main()
