"""Generic message window with the close button deactivated"""


from string import punctuation

from tkinter import Toplevel, Label
import tkinter.font

from ..constants import PROGNAME


# <http://effbot.org/tkinterbook/tkinter-dialog-windows.htm> can be
# useful to study.
class InfoWindow(Toplevel):

    def __init__(self, master=None, text=None, textvariable=None, title=None,
                 font=tkinter.font.nametofont("TkHeadingFont"), **kw):
        Toplevel.__init__(self, master, **kw)
        self._window(master, title, text, textvariable, font)

    def _window(self, master, title, text, textvariable, font):
        title = title if title is not None else _("{prg}").format(prg=PROGNAME)
        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self._doNotQuit)
        self.resizable(width=False, height=False)
        self.transient(master)

        if text is not None:
            kwargs = {"text": text}
        else:
            kwargs = {"textvariable": textvariable}

        self.label = Label(self, borderwidth=20, font=font, **kwargs)
        self.label.pack()
        self.update_idletasks()
        self.grab_set()         # make the dialog modal

    def _doNotQuit(self):
        """Dumb method to override window's close button."""
        return
