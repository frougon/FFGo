"""Generic message window with the close button deactivated"""


from string import punctuation

from tkinter import Toplevel, Label
import tkinter.font
from tkinter import ttk

from ..constants import PROGNAME


# <https://effbot.org/tkinterbook/tkinter-dialog-windows.htm> can be
# useful to study.
class InfoWindow(Toplevel):

    def __init__(self, master=None, text=None, textvariable=None, title=None,
                 font=tkinter.font.nametofont("TkHeadingFont"),
                 withProgress=False, progressLabelArgs=None,
                 progressLabelKwargs=None, progressWidgetArgs=None,
                 progressWidgetKwargs=None,
                 **kw):
        Toplevel.__init__(self, master, **kw)
        self._window(master, title, text, textvariable, font,
                     withProgress, progressLabelArgs, progressLabelKwargs,
                     progressWidgetArgs, progressWidgetKwargs)

    def _window(self, master, title, text, textvariable, font,
                withProgress, progressLabelArgs, progressLabelKwargs,
                progressWidgetArgs, progressWidgetKwargs):
        title = title if title is not None else _("{prg}").format(prg=PROGNAME)
        self.title(title)
        self.protocol("WM_DELETE_WINDOW", self._doNotQuit)
        self.resizable(width=False, height=False)
        self.transient(master)

        if text is not None:
            kwargs = {"text": text}
        else:
            kwargs = {"textvariable": textvariable}

        self.label = ttk.Label(self, borderwidth=20, font=font, **kwargs)
        self.label.pack()

        if withProgress:
            if progressLabelArgs is None:
                progressLabelArgs = []
            if progressLabelKwargs is None:
                progressLabelKwargs = {}

            if progressWidgetArgs is None:
                progressWidgetArgs = []
            if progressWidgetKwargs is None:
                progressWidgetKwargs = {}

            self.progressLabel = ttk.Label(self, *progressLabelArgs,
                                           **progressLabelKwargs)
            self.progressLabel.pack(pady=3)
            self.progressWidget = ttk.Progressbar(self, *progressWidgetArgs,
                                                  **progressWidgetKwargs)
            self.progressWidget.pack(fill="x", expand=True, padx=3, pady=3)

        self.update_idletasks()
        self.grab_set()         # make the dialog modal

    def _doNotQuit(self):
        """Dumb method to override window's close button."""
        return
