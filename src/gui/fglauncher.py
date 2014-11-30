"""Launch FG and create new window indicating that FG is running."""


import subprocess
from Tkinter import *

from infowindow import InfoWindow


class FGLauncher:

    def __init__(self, master, options, FG_working_dir):
        self.master = master
        self.options = options
        self.FG_working_dir = FG_working_dir

        self._window()
        self.master.update()
        self._runFG()

    def quit(self):
        """Clean up data and destroy the window."""
        del self.master
        del self.options
        self.top.destroy()

    def _checkIfFGHasQuit(self):
        if self.process.poll() is None:
            self.master.after(1000, self._checkIfFGHasQuit)
        else:
            self.quit()

    def _runFG(self):
        try:
            self.process = subprocess.Popen(self.options,
                                            cwd=self.FG_working_dir)
            self._checkIfFGHasQuit()
        except OSError:
            self.quit()
            raise OSError

    def _window(self):
        message = _('FlightGear is running...')
        self.top = InfoWindow(self.master, message)
