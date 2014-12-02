"""Generic message window with the close button deactivated"""


from string import punctuation

from tkinter import Toplevel, Label

import tkinter.font


class InfoWindow(Toplevel):

    def __init__(self, master=None, text=None,
                 font=tkinter.font.nametofont("TkHeadingFont"), cnf={}, **kw):
        Toplevel.__init__(self, master, cnf, **kw)
        self._window(master, text, font)

    def _window(self, master, text, font):
        self.title(self.getFirstLine(text))
        self.protocol("WM_DELETE_WINDOW", self._doNotQuit)
        self.resizable(width=False, height=False)
        self.grab_set()  # Focus input on that window.
        self.transient(master)

        self.label = Label(self, borderwidth=20, text=text, font=font)
        self.label.pack()

    def getFirstLine(self, s):
        first_line = s.split('\n')[0]
        return first_line.rstrip(punctuation)

    def _doNotQuit(self):
        """Dumb method to override window's close button."""
        return
