"""Launch FG in a separate process."""


import subprocess
from tkinter import *


class FGLauncher:

    def __init__(self, master, FG_args, FG_working_dir):
        self.master = master
        self.FG_args = FG_args
        self.FG_working_dir = FG_working_dir
        self.exitStatus = IntVar()

    def quit(self, exitStatus):
        """Clean up data and set self.exitStatus."""
        del self.master
        del self.FG_args
        del self.FG_working_dir
        self.exitStatus.set(exitStatus)

    def _checkIfFGHasQuit(self):
        exitStatus = self.process.poll()

        if exitStatus is None:
            self.master.after(100, self._checkIfFGHasQuit)
        else:
            self.quit(exitStatus)

    def run(self):
        try:
            self.process = subprocess.Popen(self.FG_args,
                                            cwd=self.FG_working_dir)
        except OSError:
            # Same code as for "command not found" in Bash and Zsh...
            self.quit(127)
            raise

        self._checkIfFGHasQuit()
