#!/usr/bin/env python


"""FGo! - a simple GUI launcher for FlightGear Flight Simulator."""


import gettext
from sys import argv
from os import chdir
from Tkinter import Tk


def early_tk_init():
    root = Tk()
    root.title('FGo!')
    return root

# When importing 'config', the 'infowindow' module is itself imported, which
# defines an InfoWindow class. This in turn requires the Tk() object (at class
# definition time) because of the constructor's
# 'font=tkFont.nametofont("TkTextFont")' optional argument.
root = early_tk_init()
from config import Config
from gui.mainwindow import App
from constants import LOCALE_DIR


gettext.install('fgo', LOCALE_DIR, unicode=True)


CLI_MESSAGE = """Usage: fgo
This program does not use command line options. Edit fgo/data/config/presets
file if you need to run FGo! with some pre-configuration."""


def run(working_dir, root=root):
    """Initialize application.

    The 'root=root' optional argument allows to keep a reference to the Tk()
    object without affecting the callers that provide only one argument.

    """
    # Set current working directory.
    chdir(working_dir)
    # Initialize data object (passing 'root' allows things such as obtaining
    # the screen dpi in Config methods using root.winfo_fpixels('1i')).
    data = Config(root)
    promptToNotUseCli()
    # Initialize main window.
    app = App(root, data)

    # Set window resolution.
    window_geometry = data.window_geometry.get()
    if window_geometry:
        root.geometry(window_geometry)

    # Override window close button, so TerraSync
    # can be stopped before closing the program.
    root.protocol("WM_DELETE_WINDOW", app.quit)

    root.mainloop()

del root, early_tk_init


def promptToNotUseCli():
    if len(argv) > 1:
        print _(CLI_MESSAGE)

if __name__ == '__main__':
    from sys import path

    WORKING_DIR = path[0]
    run(WORKING_DIR)
