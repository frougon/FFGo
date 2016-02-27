# -*- coding: utf-8 -*-
# pressure_converter.py --- A dialog for performing basic pressure conversions
#                           in order to set one's altimeter
#
# Copyright (c) 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import locale
import tkinter as tk
from tkinter import ttk

from .. import misc
from .tooltip import ToolTip


def setupTranslationHelper(config):
    global pgettext, ngettext, npgettext
    from .. import misc

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext
    ngettext = translationHelper.ngettext
    npgettext = translationHelper.npgettext


class PressureConverterDialog:
    """Dialog for performing basic pressure conversions.

    Goal: make it easy to set one's altimeter even if the METAR or ATIS
    doesn't give the info in the right unit for your aircraft (hPa
    versus inHg)."""

    def _newWidget(self, widget):
        self.widgets.append(widget)
        return widget

    def __init__(self, master, config, app):
        for attr in ("master", "config", "app"):
            setattr(self, attr, locals()[attr])

        setupTranslationHelper(config)

        # These are used to break observer loops with widget A being modified,
        # causing an update of widget B, itself causing an update of widget
        # A...
        self.dontUpdateAltSetting = self.dontUpdateQNH = False
        # Will be used to record all widgets that should be destroy()ed when
        # the dialog is closed. The Tkinter reference at
        # <http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html> says
        # “Calling w.destroy() on a widget w destroys w and all its children”,
        # but previous memory measurements didn't convince me of this...
        self.widgets = []

        self.top = self._newWidget(tk.Toplevel(self.master))
        self.top.transient(self.master)
        # Uncomment this to disallow interacting with other windows
        # self.top.grab_set()
        self.top.title(_('Pressure Converter'))

        outerFrame = self._newWidget(
            ttk.Frame(self.top, padding=("12p", "12p", "12p", "12p")))
        outerFrame.grid(row=0, column=0, sticky="nsew")
        self.top.grid_rowconfigure(0, weight=100)
        self.top.grid_columnconfigure(0, weight=100)

# ----- Main frame ------------------------------------------------------------
        mainFrame = self._newWidget(ttk.Frame(outerFrame))
        mainFrame.grid(row=0, column=0, sticky="nsew")
        outerFrame.grid_rowconfigure(0, weight=100)
        outerFrame.grid_columnconfigure(0, weight=100)

        defaultHorizSpacerWidth = "16p"
        verticalSpaceBetweenRows = "6p"
        # Common width for all Spinbox instances that are going to be created
        spinboxWd = 8

        def addHorizSpacer(container, rowNum, colNum,
                           minWidth=defaultHorizSpacerWidth,
                           weight=0):
            """Add a horizontal spacer."""
            hSpacer = ttk.Frame(container)
            hSpacer.grid(row=rowNum, column=colNum, sticky="ew")
            container.grid_columnconfigure(colNum, minsize=minWidth,
                                           weight=weight)

        def addVertSpacer(container, rowNum, colNum=0,
                          minHeight=verticalSpaceBetweenRows, weight=100):
            """Add a vertical spacer."""
            spacer = ttk.Frame(container)
            spacer.grid(row=rowNum, column=colNum, sticky="ns")
            container.grid_rowconfigure(
                rowNum, minsize=minHeight, weight=weight)

        # Altimeter setting
        #
        # lRowNum: logical row number (because of spacer rows, the real row
        #          number is twice the logical row number for non-spacer rows)
        # colNum:  physical column number (we don't systematically use spacers
        #          between columns)
        lRowNum = colNum = 0
        label = self._newWidget(ttk.Label(mainFrame,
                                          text=_("Altimeter setting (inHg):")))
        label.grid(row=2*lRowNum, column=colNum, sticky="w")
        mainFrame.grid_rowconfigure(2*lRowNum, weight=0) # not stretchable
        mainFrame.grid_columnconfigure(colNum, pad="20p", weight=100)

        altSettingValidateCmd = self.master.register(
            self._altSettingValidateFunc)

        colNum += 1
        self.altSetting = tk.StringVar()
        self.altSettingSpinbox = self._newWidget(
            tk.Spinbox(mainFrame, from_=0, to=100, increment=0.01,
                       repeatinterval=20, textvariable=self.altSetting,
                       width=spinboxWd, validate="all",
                       validatecommand=(altSettingValidateCmd, "%P")))
        self.altSettingSpinbox.grid(row=2*lRowNum, column=colNum, sticky="ew")
        mainFrame.grid_columnconfigure(colNum, weight=100)

        addVertSpacer(mainFrame, 2*lRowNum+1)

        # QNH
        lRowNum += 1
        colNum = 0
        label = self._newWidget(ttk.Label(mainFrame, text=_("QNH (hPa):")))
        label.grid(row=2*lRowNum, column=colNum, sticky="w")
        mainFrame.grid_rowconfigure(2*lRowNum, weight=0) # not stretchable

        qnhValidateCmd = self.master.register(self._qnhValidateFunc)

        colNum += 1
        self.qnh = tk.StringVar()
        self.qnhSpinbox = self._newWidget(
            tk.Spinbox(mainFrame, from_=0, to=10**6, increment=1,
                       repeatinterval=20, textvariable=self.qnh,
                       width=spinboxWd, validate="all",
                       validatecommand=(qnhValidateCmd, "%P")))
        self.qnhSpinbox.grid(row=2*lRowNum, column=colNum, sticky="ew")

        colNum += 1
        addHorizSpacer(mainFrame, 2*lRowNum, colNum)

        # QNH value rounded to the nearest integer
        colNum += 1
        self.roundedQnh = tk.StringVar()
        label = self._newWidget(ttk.Label(mainFrame,
                                          textvariable=self.roundedQnh))
        label.grid(row=2*lRowNum, column=colNum, sticky="w")
        mainFrame.grid_columnconfigure(colNum, pad="20p", weight=100)

        colNum += 1
        stdButton = self._newWidget(
            ttk.Button(mainFrame, text=pgettext('pressure', 'Standard'),
                       command=self.setStandardValues, padding="4p"))
        stdButton.grid(row=0, column=colNum, sticky="e")
        mainFrame.grid_columnconfigure(colNum, weight=0) # not stretchable
        ToolTip(stdButton,
                _("Set the standard pressure\n"
                  "({std_hPa} hPa = {std_inHg} inHg)").format(
                      std_hPa=locale.format("%.02f", 1013.25),
                      std_inHg=locale.format("%.02f", 29.92)))

# ----- Close button ----------------------------------------------------------
        self.buttonFrame = self._newWidget(
            ttk.Frame(outerFrame, padding=(0, "25p", 0, 0)))
        self.buttonFrame.grid(row=1, column=0, sticky="nse")
        outerFrame.grid_rowconfigure(1, weight=100)

        closeButton = self._newWidget(
            ttk.Button(self.buttonFrame, text=_('Close'),
                       command=self.quit, padding="4p"))
        closeButton.grid(row=0, column=0)

        self.top.protocol("WM_DELETE_WINDOW", closeButton.invoke)
        self.top.bind('<Escape>', lambda event, b=closeButton: b.invoke())

        # Setup callbacks for when the pressure values are changed
        self.altSetting.trace("w", self.updateQNHValue)
        self.qnh.trace("w", self.updateAltSetting)
        self.qnh.trace("w", self.updateRoundedQnh)

        self.setStandardValues() # 1013.25 hPa, or 29.92 in Hg
        self.altSettingSpinbox.focus_set() # set the initial focus

    def _altSettingValidateFunc(self, text):
        """Validate a string for the 'Altimeter setting' field."""
        if not text.strip():
            return True         # allow the field to be empty
        else:
            try:
                f = locale.atof(text)
            except ValueError:
                return False

            return (f >= 0.0)

    def _qnhValidateFunc(self, text):
        """Validate a string for the 'QNH' field."""
        if not text.strip():
            return True         # allow the field to be empty
        else:
            try:
                f = locale.atof(text)
            except ValueError:
                return False

            return (f >= 0.0)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateQNHValue(self, *args):
        if self.dontUpdateQNH:
            self.dontUpdateQNH = False
            return

        # Every code path below sets self.qnh. This must not in turn cause an
        # update to the altimeter setting...
        self.dontUpdateAltSetting = True

        altSetting = self.altSetting.get()
        if not altSetting.strip():
            self.qnh.set('')
        else:
            self.qnh.set(locale.format("%.02f",
                                       locale.atof(altSetting)*33.8639))

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateRoundedQnh(self, *args):
        """
        Update the value of the QNH that is rounded to the nearest integer."""
        qnh = self.qnh.get()
        if not qnh.strip():
            self.roundedQnh.set('')
        else:
            self.roundedQnh.set("({})".format(round(locale.atof(qnh))))

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateAltSetting(self, *args):
        if self.dontUpdateAltSetting:
            self.dontUpdateAltSetting = False
            return

        # Every code path below sets self.altSetting. This must not in turn
        # cause an update to the QNH...
        self.dontUpdateQNH = True

        qnh = self.qnh.get()
        if not qnh.strip():
            self.altSetting.set('')
        else:
            self.altSetting.set(locale.format("%.02f",
                                              locale.atof(qnh)*0.02953))

    def setStandardValues(self):
        # This will cause the altimeter setting and the rounded QNH value to be
        # updated.
        self.qnh.set(locale.format("%.02f", 1013.25))

    def show(self):
        """Make sure the Pressure Converter dialog is visible."""
        self.top.deiconify()
        self.top.lift()         # put self.top above other windows

        focusedWidget = self.master.focus_get()
        # If the currently-focused widget doesn't belong to this dialog, set
        # focus to the last widget that had focus inside self.top.
        if not misc.isDescendantWidget(self.top, focusedWidget):
            lastFocused = self.top.focus_lastfor()
            lastFocused.focus_set()

    def quit(self):
        """Destroy this window and tell the App object about it."""
        for widget in self.widgets:
            # According to
            # <http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/index.html>,
            # simply destroying self.top should be enough to get rid of its
            # descendants, but previous memory measurements made me doubt...
            widget.destroy()

        self.app.setPressureConverterToNone()
