#!/usr/bin/env python


"""FFGo - a simple GUI launcher for the FlightGear flight simulator.

(forked from FGo!)

"""


from .constants import PROGNAME, LOCALE_DIR
import locale
import gettext
import sys
from os import chdir
from tkinter import Tk


def early_tk_init():
    root = Tk()
    root.title(PROGNAME)
    return root

# When importing 'config', the 'infowindow' module is itself imported, which
# defines an InfoWindow class. This in turn requires the Tk() object (at class
# definition time) because of the constructor's
# 'font=tkFont.nametofont("TkTextFont")' optional argument.
root = early_tk_init()
from .config import Config, AbortConfig
from .gui.mainwindow import App


def promptToNotUseCli():
    message = _("""Usage: ffgo

This program does not use command line options for now. Edit the
data/config/presets file if you need to run {prg} with some pre-configuration.\
""").format(prg=PROGNAME)

    if len(sys.argv) > 1:
        print(message + '\n')


def run(working_dir, root=root):
    """Initialize application.

    The 'root=root' optional argument allows to keep a reference to the Tk()
    object without affecting the callers that provide only one argument.

    """
    # Set current working directory.
    chdir(working_dir)

    # Initialize config object (passing 'root' allows things such as obtaining
    # the screen dpi in Config methods using root.winfo_fpixels('1i')).
    try:
        config = Config(root)
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
    app = App(root, config)

    # Set window resolution.
    window_geometry = config.window_geometry.get()
    if window_geometry:
        root.geometry(window_geometry)

    # Override the window close button in order to allow a controlled, clean
    # shutdown.
    root.protocol("WM_DELETE_WINDOW", app.quit)

    root.mainloop()


del root, early_tk_init


if __name__ == '__main__':
    from sys import path

    WORKING_DIR = path[0]
    run(WORKING_DIR)
