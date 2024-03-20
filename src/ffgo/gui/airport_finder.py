# airport_finder.py --- A dialog for finding airports
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import locale
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo, showerror

from ..constants import PROGNAME
from .. import common_transl
from . import widgets
from ..geo import geodesy
from ..misc import normalizeHeading
from . import infowindow
from .tooltip import ToolTip, TreeviewToolTip


def setupTranslationHelper(config):
    global pgettext, ngettext, npgettext
    from .. import misc

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext
    ngettext = translationHelper.ngettext
    npgettext = translationHelper.npgettext


def setupEarthMagneticFieldProvider(provider):
    global magField
    magField = provider


class ValidatingWidget:
    """Class holding widget-metadata to ease input validation.

    This class allows a number of widgets to have their input validated
    using the same code, with error reporting when the input is invalid.

    """
    def __init__(self, widget, var, validateFunc, invalidFunc):
        for attr in ("widget", "var", "validateFunc", "invalidFunc"):
            setattr(self, attr, locals()[attr])


class AirportFinder:
    "Airport finder dialog."""

    geodCalc = geodesy.GeodCalc()

    def __init__(self, master, config, app):
        for attr in ("master", "config", "app"):
            setattr(self, attr, locals()[attr])

        setupTranslationHelper(config)

        self.top = tk.Toplevel(self.master)
        self.top.transient(self.master)
        # Uncomment this to disallow interacting with other windows
        # self.top.grab_set()
        self.top.title(_('Airport finder'))
        # Currently, hiding is a better choice than destroying, because memory
        # occupation doesn't increase when the dialog is shown again after
        # being hidden.
        self.top.protocol("WM_DELETE_WINDOW", self.hide)
        self.top.bind('<Escape>', self.hide)

        panedWindow = ttk.PanedWindow(self.top, orient="vertical")
        panedWindow.grid(row=0, column=0, sticky="nsew")
        self.top.grid_rowconfigure(0, weight=100)
        self.top.grid_columnconfigure(0, weight=100)

        # Padding: all or (left, top, right, bottom)
        #
        # Padding outside the LabelFrame widgets
        outerFramesPadding = "12p"
        # Half of the vertical separation between two “adjacent” LabelFrame
        # widgets
        outerFramesHalfSep = "0p"
        # Padding inside the LabelFrame widgets
        labelFramesPadding = "15p"

        # Frame providing padding around the “Reference airport” LabelFrame
        refAirportOuterFrame = ttk.Frame(
            panedWindow,
            padding=(outerFramesPadding, outerFramesPadding,
                     outerFramesPadding, outerFramesHalfSep))
        panedWindow.add(refAirportOuterFrame, weight=100)

        # *********************************************************************
        # *                   The “Reference airport” frame                   *
        # *********************************************************************
        refAirportFrame = ttk.LabelFrame(refAirportOuterFrame,
                                         text=_("Reference airport"),
                                         padding=labelFramesPadding)
        refAirportFrame.grid(row=0, column=0, sticky="nsew")
        refAirportOuterFrame.grid_rowconfigure(0, weight=100)
        refAirportOuterFrame.grid_columnconfigure(0, weight=100)

        # In the current state, we could spare this frame, which was used to
        # align several things vertically.
        refAirportLeftSubframe = ttk.Frame(refAirportFrame,
                                           padding=(0, 0, "30p", 0))
        refAirportLeftSubframe.grid(row=0, column=0, sticky="nsew")
        refAirportFrame.grid_rowconfigure(0, weight=100)
        refAirportFrame.grid_columnconfigure(0, weight=60)

        refAirportLeftSubSubframe = ttk.Frame(refAirportLeftSubframe)
        refAirportLeftSubSubframe.grid(row=0, column=0, sticky="nsew")
        refAirportLeftSubframe.grid_rowconfigure(0, weight=100)
        refAirportLeftSubframe.grid_columnconfigure(0, weight=100)

        refAirportSearchLabel = ttk.Label(
            refAirportLeftSubSubframe, text=_("Search: "))
        refAirportSearchLabel.grid(row=0, column=0, sticky="w")
        refAirportLeftSubSubframe.grid_rowconfigure(0, weight=100)

        # The link to a StringVar is done in the AirportChooser class
        self.refAirportSearchEntry = ttk.Entry(refAirportLeftSubSubframe)
        self.refAirportSearchEntry.grid(row=0, column=1, sticky="ew")
        refAirportLeftSubSubframe.grid_columnconfigure(1, weight=100)

        # The button binding is done in the AirportChooser class
        self.refAirportSearchClearButton = ttk.Button(
            refAirportLeftSubSubframe, text=_('Clear'))
        self.refAirportSearchClearButton.grid(row=0, column=2, sticky="ew",
                                              padx="12p")
        refAirportLeftSubSubframe.grid_columnconfigure(2, weight=20)

        # The TreeviewSelect event binding is done in the AirportChooser class
        self.refAirportSearchTree = widgets.MyTreeview(
            refAirportFrame, columns=["icao", "name", "landRunways",
                                      "waterRunways", "helipads",
                                      "minRwyLength", "maxRwyLength"],
            show="headings", selectmode="browse", height=6)

        self.refAirportSearchTree.grid(row=0, column=1, sticky="nsew")
        refAirportFrame.grid_columnconfigure(1, weight=100)

        def refAirportSearchTreeTooltipFunc(region, itemID, column, self=self):
            if region == "cell":
                icao = self.refAirportSearchTree.set(itemID, "icao")
                found, airport = self.app.readAirportData(icao)

                return airport.tooltipText() if found else None
            else:
                return None

        self.airportChooserTooltip = TreeviewToolTip(
            self.refAirportSearchTree, refAirportSearchTreeTooltipFunc)

        def onRefAirportListScrolled(*args, self=self):
            self.refAirportScrollbar.set(*args)
            # Once the Treeview is scrolled, the tooltip is likely not to match
            # the airport under the mouse pointer anymore.
            self.airportChooserTooltip.hide()

        self.refAirportScrollbar = ttk.Scrollbar(
            refAirportFrame, orient='vertical',
            command=self.refAirportSearchTree.yview, takefocus=0)
        self.refAirportScrollbar.grid(row=0, column=2, sticky="ns")
        self.refAirportSearchTree.config(
            yscrollcommand=onRefAirportListScrolled)

        self.refIcao = tk.StringVar()
        self.refIcao.trace("w", self.onRefIcaoWritten)
        self.results = None

        def rwyLengthFormatFunc(length):
            return "" if length is None else str(round(length))

        def rwyLengthSortFunc(length):
            return (0 if length is None else 1, length)

        refAirportSearchColumnsList = [
            widgets.Column("icao", _("ICAO"), 0, "w", False, "width",
                           widthText="M"*4),
            widgets.Column("name", _("Name"), 1, "w", True, "width",
                           widthText="M"*25),
            widgets.Column("landRunways", _("Land rwys"), 2, "e", False,
                           formatFunc=str),
            widgets.Column("waterRunways", _("Water rwys"), 3, "e", False,
                           formatFunc=str),
            widgets.Column("helipads", _("Helipads"), 4, "e", False,
                           formatFunc=str),
            widgets.Column("minRwyLength", _("Shortest rwy (m)"), 5, "e",
                           False, formatFunc=rwyLengthFormatFunc,
                           sortFunc=rwyLengthSortFunc),
            widgets.Column("maxRwyLength", _("Longest rwy (m)"), 6, "e",
                           False, formatFunc=rwyLengthFormatFunc,
                           sortFunc=rwyLengthSortFunc) ]
        refAirportSearchColumns = { col.name: col
                                    for col in refAirportSearchColumnsList }

        refAirportSearchData = []
        for icao in config.sortedIcao():
            airport = config.airports[icao]
            refAirportSearchData.append(
                (icao, airport.name, airport.nbLandRunways,
                 airport.nbWaterRunways, airport.nbHelipads,
                 airport.minRwyLength, airport.maxRwyLength))

        self.airportChooser = widgets.AirportChooser(
            self.master, self.config,
            self.refIcao,       # output variable of the chooser
            refAirportSearchData,
            refAirportSearchColumns, "icao", # Initially, sort by ICAO
            self.refAirportSearchEntry, self.refAirportSearchClearButton,
            self.refAirportSearchTree,
            0, # delay before propagating the effect of nav keys (arrows...)
            treeUpdatedCallback=self.hideAirportChooserTooltip)

        self.searchDescrLabelVar = tk.StringVar()

        # Initial “reference airport” selection
        curIcao = config.airport.get()
        try:
            # This will set self.refIcao via the TreeviewSelect event handler.
            self.refAirportSearchTree.FFGoGotoItemWithValue("icao", curIcao)
        except widgets.NoSuchItem:
            self.refIcao.set('')

        # *********************************************************************
        # *                      Search parameters frame                      *
        # *********************************************************************

        # List of ValidatingWidget instances for “standard” input validation.
        self.validatingWidgets = []

        # Frame providing padding around the “Search parameters” LabelFrame
        searchParamsOuterFrame = ttk.Frame(
            panedWindow,
            padding=(outerFramesPadding, outerFramesHalfSep,
                     outerFramesPadding, outerFramesHalfSep))
        panedWindow.add(searchParamsOuterFrame, weight=0)

        searchParamsFrame = ttk.LabelFrame(searchParamsOuterFrame,
                                           text=_("Search parameters"),
                                           padding=labelFramesPadding)
        searchParamsFrame.grid(row=0, column=0, sticky="nsew")
        searchParamsOuterFrame.grid_rowconfigure(0, weight=100)
        searchParamsOuterFrame.grid_columnconfigure(0, weight=100)

        searchParamsLeftFrame = ttk.Frame(searchParamsFrame)
        searchParamsLeftFrame.grid(row=0, column=0, sticky="nsew")
        searchParamsFrame.grid_columnconfigure(0, weight=200)
        searchParamsFrame.grid_rowconfigure(0, weight=100)

        searchParamsLeftFrame.grid_columnconfigure(0, weight=100)
        paramsSpinboxWd = 6     # common width for several aligned spinboxes

        label = ttk.Label(searchParamsLeftFrame,
                          textvariable=self.searchDescrLabelVar)
        label.grid(row=0, column=0, sticky="w")
        searchParamsLeftFrame.grid_rowconfigure(0, weight=100)

        spacer = ttk.Frame(searchParamsLeftFrame)
        spacer.grid(row=0, column=1, sticky="nsew")
        searchParamsLeftFrame.grid_columnconfigure(1, minsize="7p", weight=100)

        label = ttk.Label(searchParamsLeftFrame,
                          text=pgettext("distance", "min: "))
        label.grid(row=0, column=2, sticky="e")

        distBoundValidateCmd = self.master.register(self._distBoundValidateFunc)
        distBoundInvalidCmd = self.master.register(self._distBoundInvalidFunc)

        # Minimum distance to the reference airport
        self.minDist = tk.StringVar()
        self.minDist.set('75')
        self.minDistSpinbox = tk.Spinbox(
            searchParamsLeftFrame, from_=0, to=10820, increment=1,
            repeatinterval=20, textvariable=self.minDist, width=paramsSpinboxWd,
            validate="focusout", validatecommand=(distBoundValidateCmd, "%P"),
            invalidcommand=(distBoundInvalidCmd, "%W", "%P"))
        # Used to run the validation code manually in case the spinbox
        # still has focus when the data is needed. Using
        # 'validate="all"' would *maybe* avoid the need to run manual
        # validation, but it is inconvenient for users (e.g., erasing is
        # a pain, because empty input is typically forbidden).
        self.validatingWidgets.append(
            ValidatingWidget(self.minDistSpinbox, self.minDist,
                             self._distBoundValidateFunc,
                             self._distBoundInvalidFunc))
        self.minDistSpinbox.grid(row=0, column=3, sticky="ew")
        searchParamsLeftFrame.grid_columnconfigure(3, weight=100)

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=" " + pgettext("length unit", "nm"))
        lbl.grid(row=0, column=4, sticky="w")

        spacer = ttk.Frame(searchParamsLeftFrame)
        spacer.grid(row=0, column=5, sticky="nsew")
        searchParamsLeftFrame.grid_columnconfigure(5, minsize="7p", weight=100)

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=pgettext("distance", "max: "))
        lbl.grid(row=0, column=6, sticky="e")

        # Maximum distance to the reference airport
        self.maxDist = tk.StringVar()
        self.maxDist.set('100')
        self.maxDistSpinbox = tk.Spinbox(
            searchParamsLeftFrame, from_=0, to=10820, increment=1,
            repeatinterval=20, textvariable=self.maxDist, width=paramsSpinboxWd,
            validate="focusout", validatecommand=(distBoundValidateCmd, "%P"),
            invalidcommand=(distBoundInvalidCmd, "%W", "%P"))
        self.validatingWidgets.append(
            ValidatingWidget(self.maxDistSpinbox, self.maxDist,
                             self._distBoundValidateFunc,
                             self._distBoundInvalidFunc))
        self.maxDistSpinbox.grid(row=0, column=7, sticky="ew")
        searchParamsLeftFrame.grid_columnconfigure(7, weight=100)

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=" " + pgettext("length unit", "nm"))
        lbl.grid(row=0, column=8, sticky="w")

        def addRunwayCountCriteria(rowNumber, startCol, labelText, minName,
                                   maxName, self=self,
                                   containingFrame=searchParamsLeftFrame,
                                   paramsSpinboxWd=paramsSpinboxWd):
            label1 = ttk.Label(containingFrame,
                               text="{descr}".format(descr=labelText))
            label1.grid(row=rowNumber, column=startCol, sticky="w")
            containingFrame.grid_rowconfigure(rowNumber, weight=100)

            spacer = ttk.Frame(containingFrame)
            spacer.grid(row=rowNumber, column=startCol+1, sticky="nsew")
            containingFrame.grid_columnconfigure(startCol+1, minsize="7p",
                                                 weight=100)

            label2 = ttk.Label(containingFrame,
                               text=pgettext("number of runways/helipads",
                                             "min: "))
            label2.grid(row=rowNumber, column=startCol+2, sticky="e")

            nbRunwaysValidateCmd = self.master.register(
                self._nbRunwaysValidateFunc)
            nbRunwaysInvalidCmd = self.master.register(
                self._nbRunwaysInvalidFunc)

            # Minimum number of land runways / water runways / helipads
            setattr(self, minName, tk.StringVar())
            getattr(self, minName).set('0')
            minWidget = tk.Spinbox(
                containingFrame, from_=0, to=999, increment=1,
                repeatinterval=150, textvariable=getattr(self, minName),
                width=paramsSpinboxWd, validate="focusout",
                validatecommand=(nbRunwaysValidateCmd, "%P"),
                invalidcommand=(nbRunwaysInvalidCmd, "%W", "%P"))
            setattr(self, minName + "Spinbox", minWidget)
            self.validatingWidgets.append(
                ValidatingWidget(minWidget, getattr(self, minName),
                                 self._nbRunwaysValidateFunc,
                                 self._nbRunwaysInvalidFunc))
            minWidget.grid(row=rowNumber, column=startCol+3, sticky="ew")

            label3 = ttk.Label(
                containingFrame,
                text=pgettext("number of runways/helipads", "max: "))
            label3.grid(row=rowNumber, column=startCol+6, sticky="e")

            # Maximum number of land runways / water runways / helipads
            setattr(self, maxName, tk.StringVar())
            getattr(self, maxName).set('999')
            maxWidget = tk.Spinbox(
                containingFrame, from_=0, to=999, increment=1,
                repeatinterval=150, textvariable=getattr(self, maxName),
                width=paramsSpinboxWd, validate="focusout",
                validatecommand=(nbRunwaysValidateCmd, "%P"),
                invalidcommand=(nbRunwaysInvalidCmd, "%W", "%P"))
            setattr(self, maxName + "Spinbox", maxWidget)
            self.validatingWidgets.append(
                ValidatingWidget(maxWidget, getattr(self, maxName),
                                 self._nbRunwaysValidateFunc,
                                 self._nbRunwaysInvalidFunc))
            maxWidget.grid(row=rowNumber, column=startCol+7, sticky="ew")

        addRunwayCountCriteria(1, 0, _("Number of land runways"),
                               "minNbLandRunways", "maxNbLandRunways")
        addRunwayCountCriteria(2, 0, _("Number of water runways"),
                               "minNbWaterRunways", "maxNbWaterRunways")
        addRunwayCountCriteria(3, 0, _("Number of helipads"),
                               "minNbHelipads", "maxNbHelipads")

        # Intercolumn space between the first two “main columns” of the “Search
        # parameters” frame.
        spacer = ttk.Frame(searchParamsLeftFrame)
        spacer.grid(row=0, column=9, sticky="nsew")
        searchParamsLeftFrame.grid_columnconfigure(9, minsize="7p", weight=150)

        # Check button to only include airports that have at least one land or
        # water runway
        self.hasLandOrWaterRwys = tk.IntVar()
        self.hasLandOrWaterRwys.trace("w", self.onHasLandOrWaterRwysWritten)
        hasLandOrWaterRwysCb = ttk.Checkbutton(
            searchParamsLeftFrame, text=_("Has land or water runways"),
            variable=self.hasLandOrWaterRwys)
        hasLandOrWaterRwysCb.grid(row=0, column=10, columnspan=5, sticky="w")

        ToolTip(hasLandOrWaterRwysCb,
                _("Only include airports that have at least one land or "
                  "water runway"), autowrap=True)

        lbl = ttk.Label(searchParamsLeftFrame, text=_("Longest runway"))
        lbl.grid(row=1, column=10, sticky="w")

        spacer = ttk.Frame(searchParamsLeftFrame)
        spacer.grid(row=1, column=11, sticky="nsew")
        searchParamsLeftFrame.grid_columnconfigure(11, minsize="5p", weight=70)

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=pgettext("runway length", "at least") + " ")
        lbl.grid(row=1, column=12, sticky="e")

        distBoundValidateCmd = self.master.register(self._distBoundValidateFunc)
        distBoundInvalidCmd = self.master.register(self._distBoundInvalidFunc)

        # The longest runway in each result airport must be longer than...
        self.maxRwyLengthLowerBound = tk.StringVar()
        self.maxRwyLengthLowerBound.set('0')
        self.maxRwyLengthLowerBoundSpinbox = tk.Spinbox(
            searchParamsLeftFrame, from_=0, to=99999, increment=0.2,
            repeatinterval=20, textvariable=self.maxRwyLengthLowerBound,
            width=paramsSpinboxWd,
            validate="focusout", validatecommand=(distBoundValidateCmd, "%P"),
            invalidcommand=(distBoundInvalidCmd, "%W", "%P"))
        self.validatingWidgets.append(
            ValidatingWidget(self.maxRwyLengthLowerBoundSpinbox,
                             self.maxRwyLengthLowerBound,
                             self._distBoundValidateFunc,
                             self._distBoundInvalidFunc))
        self.maxRwyLengthLowerBoundSpinbox.grid(row=1, column=13, sticky="ew")
        searchParamsLeftFrame.grid_columnconfigure(13, weight=100)

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=" " + pgettext("length unit", "m"))
        lbl.grid(row=1, column=14, sticky="w")

        lbl = ttk.Label(searchParamsLeftFrame, text=_("Shortest runway"))
        lbl.grid(row=2, column=10, sticky="w")

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=pgettext("runway length", "at most") + " ")
        lbl.grid(row=2, column=12, sticky="e")

        # The shortest runway in each result airport must be shorter than...
        self.minRwyLengthUpperBound = tk.StringVar()
        self.minRwyLengthUpperBound.set('99999')
        self.minRwyLengthUpperBoundSpinbox = tk.Spinbox(
            searchParamsLeftFrame, from_=0, to=99999, increment=0.2,
            repeatinterval=20, textvariable=self.minRwyLengthUpperBound,
            width=paramsSpinboxWd,
            validate="focusout", validatecommand=(distBoundValidateCmd, "%P"),
            invalidcommand=(distBoundInvalidCmd, "%W", "%P"))
        self.validatingWidgets.append(
            ValidatingWidget(self.minRwyLengthUpperBoundSpinbox,
                             self.minRwyLengthUpperBound,
                             self._distBoundValidateFunc,
                             self._distBoundInvalidFunc))
        self.minRwyLengthUpperBoundSpinbox.grid(row=2, column=13, sticky="ew")

        lbl = ttk.Label(searchParamsLeftFrame,
                        text=" " + pgettext("length unit", "m"))
        lbl.grid(row=2, column=14, sticky="w")

        # Set the initial enabled/disabled state for the two spinboxes
        # according to this state of the "Has land or water runways" check
        # button.
        self.hasLandOrWaterRwys.set('0')

        spacer = ttk.Frame(searchParamsLeftFrame)
        spacer.grid(row=0, column=15, sticky="nsew")
        searchParamsLeftFrame.grid_columnconfigure(15, minsize="7p", weight=150)

        # Calculation method (Vincenty or Karney)
        calcMethodLabel = ttk.Label(searchParamsLeftFrame,
                                    text=_("Calculation method"))
        calcMethodLabel.grid(row=0, column=16, sticky="w")

        self.calcMethodVar = tk.StringVar()
        # Vincenty's method is much faster than Karney's one, and since the
        # calculation over about 34000 airports takes some time, let's pick the
        # fastest one as default even if it may fail for a few rare pairs of
        # airports (which will be signaled, so the user can select the Karney
        # method for these specific cases and have all results in the end).
        self.calcMethodVar.set("vincentyInverseWithFallback")
        karneyMethodRadioButton = ttk.Radiobutton(
            searchParamsLeftFrame, variable=self.calcMethodVar,
            text=_("Karney"), value="karneyInverse",
            padding=("10p", 0, "10p", 0))
        karneyMethodRadioButton.grid(row=0, column=17, sticky="w")
        vincentyMethodRadioButton = ttk.Radiobutton(
            searchParamsLeftFrame, variable=self.calcMethodVar,
            text=_("Vincenty et al."), value="vincentyInverseWithFallback",
            padding=("10p", 0, "10p", 0))
        vincentyMethodRadioButton.grid(row=1, column=17, sticky="w")

        if not self.geodCalc.karneyMethodAvailable():
            karneyMethodRadioButton.state(["disabled"])

        # Tooltip for the calculation method
        ToolTip(calcMethodLabel,
                common_transl.geodCalcMethodTooltipText(self.geodCalc),
                autowrap=True)

        spacer = ttk.Frame(searchParamsFrame)
        spacer.grid(row=0, column=1, sticky="nsew")
        searchParamsFrame.grid_columnconfigure(1, minsize="5p", weight=150)

        # The 'Search' button
        self.searchButton = ttk.Button(
            searchParamsFrame, text=_('Search'),
            command=self.search, padding="10p")
        self.searchButton.grid(row=0, column=2)

        # Alt-s keyboard shortcut for the 'Search' button
        self.top.bind('<Alt-KeyPress-s>',
                      lambda event, self=self: self.searchButton.invoke())
        ToolTip(self.searchButton,
                _("Find all airports matching the specified criteria.\n"
                  "Can be run with Alt-S."), autowrap=True)

        # *********************************************************************
        # *                       Search results frame                        *
        # *********************************************************************

        # Frame providing padding around the “Search results” LabelFrame
        resultsOuterFrame = ttk.Frame(
            panedWindow, padding=(outerFramesPadding, outerFramesHalfSep,
                                  outerFramesPadding, outerFramesPadding))
        panedWindow.add(resultsOuterFrame, weight=900)

        resultsFrame = ttk.LabelFrame(resultsOuterFrame,
                                      text=_("Search results"),
                                      padding=labelFramesPadding)
        resultsFrame.grid(row=0, column=0, sticky="nsew")
        resultsOuterFrame.grid_rowconfigure(0, weight=100)
        resultsOuterFrame.grid_columnconfigure(0, weight=100)

        resultsLeftFrame = ttk.Frame(resultsFrame)
        resultsLeftFrame.grid(row=0, column=0, sticky="nsew")
        resultsFrame.grid_rowconfigure(0, weight=100)
        resultsFrame.grid_columnconfigure(0, weight=100, pad="30p")

        # Number of results
        self.nbResultsTextVar = tk.StringVar()
        nbResultsLabel = ttk.Label(resultsLeftFrame,
                                   textvariable=self.nbResultsTextVar)
        nbResultsLabel.grid(row=0, column=0, sticky="w")
        resultsLeftFrame.grid_columnconfigure(0, weight=100)

        searchBottomLeftSpacerHeight = "20p"
        spacer = ttk.Frame(resultsLeftFrame)
        spacer.grid(row=1, column=0, sticky="nsew")
        resultsLeftFrame.grid_rowconfigure(
            1, minsize=searchBottomLeftSpacerHeight, weight=100)

        # Direction (from or to the reference airport)
        searchBottomLeftSubframe1 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSubframe1.grid(row=2, column=0, sticky="nsw")

        directionLabel = ttk.Label(searchBottomLeftSubframe1,
                                   text=_("Direction"))
        directionLabel.grid(row=0, column=0, sticky="w")
        searchBottomLeftSubframe1.grid_columnconfigure(0, weight=100)

        self.directionToRef = tk.IntVar()
        self.directionToRef.set(1)
        self.directionToRef.trace("w", self.displayResults)
        directionToRefButton = ttk.Radiobutton(
            searchBottomLeftSubframe1, variable=self.directionToRef,
            text=_("to reference airport"), value=1,
            padding=("10p", 0, "10p", 0))
        directionToRefButton.grid(row=0, column=1, sticky="w")
        searchBottomLeftSubframe1.grid_rowconfigure(0, pad="5p")
        directionFromRefButton = ttk.Radiobutton(
            searchBottomLeftSubframe1, variable=self.directionToRef,
            text=_("from reference airport"), value=0,
            padding=("10p", 0, "10p", 0))
        directionFromRefButton.grid(row=1, column=1, sticky="w")

        searchBottomLeftSpacer1 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSpacer1.grid(row=3, column=0, sticky="nsew")
        resultsLeftFrame.grid_rowconfigure(
            3, minsize=searchBottomLeftSpacerHeight, weight=100)

        # Magnetic or true bearings
        searchBottomLeftSubframe2 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSubframe2.grid(row=4, column=0, sticky="nsw")

        bearingsTypeLabel = ttk.Label(searchBottomLeftSubframe2,
                                      text=_("Bearings"))
        bearingsTypeLabel.grid(row=0, column=0, sticky="w")
        searchBottomLeftSubframe2.grid_columnconfigure(0, weight=100)

        self.bearingsType = tk.StringVar()
        self.bearingsType.trace("w", self.displayResults)
        magBearingsButton = ttk.Radiobutton(
            searchBottomLeftSubframe2, variable=self.bearingsType,
            text=pgettext("Bearings", "magnetic"), value="magnetic",
            padding=("10p", 0, "10p", 0))
        magBearingsButton.grid(row=0, column=1, sticky="w")
        searchBottomLeftSubframe2.grid_rowconfigure(0, pad="5p")
        trueBearingsButton = ttk.Radiobutton(
            searchBottomLeftSubframe2, variable=self.bearingsType,
            text=pgettext("Bearings", "true"), value="true",
            padding=("10p", 0, "10p", 0))
        trueBearingsButton.grid(row=1, column=1, sticky="w")

        if magField is not None:
            self.bearingsType.set("magnetic")
        else:
            self.bearingsType.set("true")
            magBearingsButton.state(["disabled"])
            ToolTip(bearingsTypeLabel, common_transl.magneticFieldTooltipText,
                    autowrap=True)

        searchBottomLeftSpacer2 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSpacer2.grid(row=5, column=0, sticky="nsew")
        resultsLeftFrame.grid_rowconfigure(
            5, minsize=searchBottomLeftSpacerHeight, weight=100)

        # Length unit (nautical miles or kilometers)
        searchBottomLeftSubframe3 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSubframe3.grid(row=6, column=0, sticky="nsw")

        lengthUnitLabel = ttk.Label(searchBottomLeftSubframe3,
                                    text=_("Distances in"))
        lengthUnitLabel.grid(row=0, column=0, sticky="w")
        searchBottomLeftSubframe3.grid_columnconfigure(0, weight=100)

        self.lengthUnit = tk.StringVar()
        self.lengthUnit.set("nautical mile")
        self.lengthUnit.trace("w", self.displayResults)
        nautMilesButton = ttk.Radiobutton(
            searchBottomLeftSubframe3, variable=self.lengthUnit,
            text=_("nautical miles"), value="nautical mile",
            padding=("10p", 0, "10p", 0))
        nautMilesButton.grid(row=0, column=1, sticky="w")
        searchBottomLeftSubframe3.grid_rowconfigure(0, pad="5p")
        kilometersButton = ttk.Radiobutton(
            searchBottomLeftSubframe3, variable=self.lengthUnit,
            text=_("kilometers"), value="kilometer",
            padding=("10p", 0, "10p", 0))
        kilometersButton.grid(row=1, column=1, sticky="w")

        searchBottomLeftSpacer3 = ttk.Frame(resultsLeftFrame)
        searchBottomLeftSpacer3.grid(row=7, column=0, sticky="nsew")
        resultsLeftFrame.grid_rowconfigure(
            7, minsize=searchBottomLeftSpacerHeight, weight=100)

        # “Choose selected airport” button
        self.chooseSelectedAptButton = ttk.Button(
            resultsLeftFrame, text=_('Choose selected airport'),
            command=self.chooseSelectedAirport, padding="4p")
        self.chooseSelectedAptButton.grid(row=8, column=0)
        resultsLeftFrame.grid_rowconfigure(8, pad="15p")

        self.chooseSelectedAptButton.state(["disabled"])
        ToolTip(self.chooseSelectedAptButton,
                _("Choose the selected airport and close this dialog"),
                autowrap=True)

        # “Clear results” button
        self.clearResultsButton = ttk.Button(
            resultsLeftFrame, text=_('Clear results'),
            command=self.clearResults, padding="4p")
        self.clearResultsButton.grid(row=9, column=0)

        ToolTip(self.clearResultsButton,
                _("Clear the table of results. This may free up a small "
                  "amount of memory if a very large number of results "
                  "is displayed."),
                autowrap=True)

        # Treeview widget used to display the search results
        resultsColumnsList = [
            widgets.Column("icao", _("ICAO"), 0, "w", False, "width",
                           widthText="M"*4),
            widgets.Column("name", _("Name"), 1, "w", True, "width",
                           widthText="M"*18),
            # The distance 'formatFunc' will be set later (depends on the
            # chosen unit).
            widgets.Column("distance", _("Distance"), 2, "e", False, "width",
                           widthText="M"*6),
            widgets.Column("initBearing", _("Init. bearing"), 3, "e",
                           False, "width", widthText="M"*4, formatFunc=str),
            widgets.Column("finalBearing", _("Final bearing"), 4, "e",
                           False, "width", widthText="M"*4, formatFunc=str),
            widgets.Column("landRunways", _("Land rwys"), 5, "e", False,
                           formatFunc=str),
            widgets.Column("waterRunways", _("Water rwys"), 6, "e", False,
                           formatFunc=str),
            widgets.Column("helipads", _("Helipads"), 7, "e", False,
                           formatFunc=str),
            widgets.Column("minRwyLength", _("Shortest rwy (m)"), 8, "e",
                           False, formatFunc=rwyLengthFormatFunc,
                           sortFunc=rwyLengthSortFunc),
            widgets.Column("maxRwyLength", _("Longest rwy (m)"), 9, "e",
                           False, formatFunc=rwyLengthFormatFunc,
                           sortFunc=rwyLengthSortFunc) ]
        self.resultsColumns = { col.name: col for col in resultsColumnsList }
        resCols = [ col.name for col in resultsColumnsList ]

        self.resultsTree = widgets.MyTreeview(
            resultsFrame, columns=resCols, show="headings",
            selectmode="browse", height=10)

        self.resultsTree.grid(row=0, column=1, sticky="nsew")
        resultsFrame.grid_columnconfigure(1, weight=300)

        def resultsTreeTooltipFunc(region, itemID, column, self=self):
            if region == "cell":
                icao = self.resultsTree.set(itemID, "icao")
                found, airport = self.app.readAirportData(icao)

                return airport.tooltipText() if found else None
            else:
                return None

        self.resultsTreeTooltip = TreeviewToolTip(self.resultsTree,
                                                  resultsTreeTooltipFunc)

        def onResultsTreeScrolled(*args, self=self):
            self.resultsScrollbar.set(*args)
            # Once the Treeview is scrolled, the tooltip is likely not to match
            # the airport under the mouse pointer anymore.
            self.resultsTreeTooltip.hide()

        self.resultsScrollbar = ttk.Scrollbar(
            resultsFrame, orient='vertical',
            command=self.resultsTree.yview, takefocus=0)
        self.resultsScrollbar.grid(row=0, column=2, sticky="ns")
        self.resultsTree.config(yscrollcommand=onResultsTreeScrolled)

        # This will hold the ICAO for the airport selected in the results tree.
        self.selectedIcao = tk.StringVar()
        # Logic around the Treeview widget used to display the results
        self.resultsManager = TabularDataManager(
            self.master, self.config, self.selectedIcao, [],
            self.resultsColumns, "icao", "distance", self.resultsTree,
            treeUpdatedCallback=self.hideResultsTreeTooltip)

        self.refAirportSearchEntry.focus_set()

    def _distBoundValidateFunc(self, text):
        """Validate a string that should contain a distance measure."""
        try:
            f = locale.atof(text)
        except ValueError:
            return False

        return (f >= 0.0)

    def _distBoundInvalidFunc(self, widgetPath, text):
        """Callback function used when an invalid distance has been input."""
        widget = self.master.nametowidget(widgetPath)
        type_ = "distance"

        if widget is self.minDistSpinbox:
            message = _('Invalid minimum distance value')
        elif widget is self.maxDistSpinbox:
            message = _('Invalid maximum distance value')
        elif widget in (self.minRwyLengthUpperBoundSpinbox,
                        self.maxRwyLengthLowerBoundSpinbox):
            message = _('Invalid length')
            type_ = "length"
        else:
            assert False, "Unexpected widget: " + repr(widget)

        if type_ == "distance":
            detailStart = _("'{input}' is not a valid distance.")
        else:
            assert type_ == "length", type_
            detailStart = _("'{input}' is not a valid length.")

        detail = (detailStart + " " +
                  _("Only non-negative decimal numbers are allowed here.")) \
                  .format(input=text)
        showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail,
                  parent=self.top)

        widget.focus_set()

    def _nbRunwaysValidateFunc(self, text):
        """Validate a string that should contain a number of runways."""
        try:
            i = int(text)
        except ValueError:
            return False

        return (i >= 0)

    def _nbRunwaysInvalidFunc(self, widgetPath, text):
        """Callback function used when an invalid runway count has been input."""
        widget = self.master.nametowidget(widgetPath)

        message = _('Invalid value')
        detail = _("'{input}' is not a valid runway or helipad count. Only "
                   "non-negative integers are allowed here.").format(input=text)
        showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail,
                  parent=self.top)

        widget.focus_set()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onHasLandOrWaterRwysWritten(self, *args):
        widgets = (self.maxRwyLengthLowerBoundSpinbox,
                   self.minRwyLengthUpperBoundSpinbox)

        state = "normal" if self.hasLandOrWaterRwys.get() else "disabled"
        for widget in widgets:
            widget.config(state=state)

    def destroy(self, event=None):
        """Destroy the Airport Finder dialog."""
        self.top.destroy()
        # Normally, this should allow Python's garbage collector to free some
        # memory, however it doesn't work so well. Presumably, the Tk widgets
        # stay in memory even when they are not referenced anymore...
        self.app.setAirportFinderToNone()

    def hide(self, event=None):
        """Hide the Airport Finder dialog."""
        self.top.withdraw()

    def show(self, event=None):
        """Unhide a hidden Airport Finder dialog."""
        self.top.deiconify()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onRefIcaoWritten(self, *args):
        icao = self.refIcao.get()
        self.results = None     # the results were for the previous ref airport

        self.searchDescrLabelVar.set(
            _("Distance from ref. ({refIcao})").format(
            refIcao=icao))

    def hideAirportChooserTooltip(self):
        self.airportChooserTooltip.hide()

    def hideResultsTreeTooltip(self):
        self.resultsTreeTooltip.hide()

    def search(self):
        """Main method of the Airport Finder dialog."""
        # Validate the contents of these spinboxes in case one of them still
        # has the focus (which is possible if this method was invoked by a
        # keyboard shortcut).
        for validating in self.validatingWidgets:
            val = validating.var.get()
            if not validating.validateFunc(val):
                validating.invalidFunc(str(validating.widget), val)
                return

        self.searchButton.state(["disabled"])
        self.chooseSelectedAptButton.state(["disabled"])
        message = _("Calculating distances and bearings...")
        infoWindow = infowindow.InfoWindow(self.master, text=message)

        try:
            res = self._search()
        finally:
            infoWindow.destroy()
            self.searchButton.state(["!disabled"])

        if res is not None:
            if res:             # number of omitted results
                message = _('Some results might be missing')
                detail = _(
                    "Could not compute distance and bearings between "
                    "{refICAO} and the following airport(s): {aptList}.\n\n"
                    "Vincenty's algorithm for the geodetic inverse problem "
                    "is known not to handle all possible cases. Use Karney's "
                    "calculation method if you want to see all results.\n\n"
                    "Normally, this problem can only happen between airports "
                    "that are antipodal or nearly so. Therefore, if you are "
                    "not interested in such cases, you can probably ignore "
                    "this message.").format(refICAO=self.refIcao.get(),
                            aptList=', '.join(sorted(res)))

                showinfo(_('{prg}').format(prg=PROGNAME), message,
                         detail=detail, parent=self.top)

            self.displayResults()
            if self.results:
                self.chooseSelectedAptButton.state(["!disabled"])

    def _search(self):
        refIcao = self.refIcao.get()

        # Convert from nautical miles to meters (the contents of these
        # variables has been validated in search()).
        minDist = 1852*locale.atof(self.minDist.get())
        maxDist = 1852*locale.atof(self.maxDist.get())

        minNbLandRunways = int(self.minNbLandRunways.get())
        maxNbLandRunways = int(self.maxNbLandRunways.get())
        minNbWaterRunways = int(self.minNbWaterRunways.get())
        maxNbWaterRunways = int(self.maxNbWaterRunways.get())
        minNbHelipads = int(self.minNbHelipads.get())
        maxNbHelipads = int(self.maxNbHelipads.get())
        mustHaveLandOrWaterRwys = self.hasLandOrWaterRwys.get()
        minRLUB = locale.atof(self.minRwyLengthUpperBound.get())
        maxRLLB = locale.atof(self.maxRwyLengthLowerBound.get())

        self.results = []
        omittedResults = set()

        if refIcao:
            refApt = self.config.airports[refIcao]
            refAptLat, refAptLon = refApt.lat, refApt.lon # for performance

            distCalcFunc = getattr(self.geodCalc, self.calcMethodVar.get())
            airportsDict = self.config.airports

            for apt in airportsDict.values():
                try:
                    g = distCalcFunc(apt.lat, apt.lon,
                                     refAptLat, refAptLon)
                except geodesy.VincentyInverseError:
                    omittedResults.add(apt.icao)
                    continue

                if \
            (minDist <= g["s12"] <= maxDist and
             minNbLandRunways <= apt.nbLandRunways <= maxNbLandRunways and
             minNbWaterRunways <= apt.nbWaterRunways <= maxNbWaterRunways and
             minNbHelipads <= apt.nbHelipads <= maxNbHelipads and
             (mustHaveLandOrWaterRwys and
              (apt.minRwyLength is not None and apt.minRwyLength <= minRLUB and
               apt.maxRwyLength is not None and apt.maxRwyLength >= maxRLLB) or
              not mustHaveLandOrWaterRwys)):
                    self.results.append(
                        (apt, g["s12"], g["azi1"], g["azi2"]))

            return omittedResults
        else:
            return None

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def displayResults(self, *args, FFGoClearNbResultsTextVar=False):
        """Display the last search results."""
        if self.results is None or not self.refIcao.get():
            return

        l = []

        magBearings = (self.bearingsType.get() == "magnetic")
        if magBearings:
            # This is correct, because self.results is set to None whenever
            # self.refIcao is changed.
            refApt = self.config.airports[self.refIcao.get()]
            refAptLat, refAptLon = refApt.lat, refApt.lon
            magDeclAtRef = magField.decl(refAptLat, refAptLon)

            latLon = [ (airport.lat, airport.lon)
                       for airport, *rest in self.results ]
            magDecl = magField.batchDecl(latLon)

        if self.lengthUnit.get() == "nautical mile":
            self.resultsColumns["distance"].formatFunc = (
                lambda d: str(round(d / 1852))) # exact conversion
        elif self.lengthUnit.get() == "kilometer":
            self.resultsColumns["distance"].formatFunc = (
                lambda d: str(round(d / 1000)))
        else:
            assert False, "Unexpected length unit: {!r}".format(
                self.lengthUnit.get())

        directionToRef = self.directionToRef.get()

        for i, (airport, distance, azi1, azi2) in enumerate(self.results):
            if directionToRef:
                if magBearings:
                    initBearing = normalizeHeading(azi1 - magDecl[i])
                    finalBearing = normalizeHeading(azi2 - magDeclAtRef)
                else:
                    initBearing = normalizeHeading(azi1)
                    finalBearing = normalizeHeading(azi2)
            else:
                if magBearings:
                    initBearing = normalizeHeading(azi2 + 180.0 - magDeclAtRef)
                    finalBearing = normalizeHeading(azi1 + 180.0 - magDecl[i])
                else:
                    initBearing = normalizeHeading(azi2 + 180.0)
                    finalBearing = normalizeHeading(azi1 + 180.0)

            l.append([airport.icao, airport.name, distance, initBearing,
                      finalBearing, airport.nbLandRunways,
                      airport.nbWaterRunways, airport.nbHelipads,
                      airport.minRwyLength, airport.maxRwyLength])

        self.resultsManager.loadData(l)

        if FFGoClearNbResultsTextVar:
            self.nbResultsTextVar.set('')
        else:
            nbRes = len(self.results)
            self.nbResultsTextVar.set(
                ngettext("Found {} airport", "Found {} airports", nbRes)
                .format(nbRes))

    def clearResults(self):
        self.results = []
        self.displayResults(FFGoClearNbResultsTextVar=True)
        self.chooseSelectedAptButton.state(["disabled"])

    def chooseSelectedAirport(self):
        """
        Choose the results-selected airport and close the Airport Finder dialog."""
        icao = self.selectedIcao.get()
        try:
            self.app.selectNewAirport(icao)
        except widgets.NoSuchItem:
            message = _('Airport is filtered out')
            detail = _("It is impossible to select “{name}” ({icao}) in "
                       "{prg}'s main window, because it is not present in the "
                       "airport list from that window. You have probably "
                       "enabled the option to only show airports for which "
                       "you have scenery installed.\n\n"
                       "In order to be able to select this airport, you "
                       "should either deselect this option from the Settings "
                       "menu (“Show installed airports only”) or install "
                       "scenery for this airport.").format(
                       prg=PROGNAME, icao=icao,
                           name=self.config.airports[icao].name)
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail,
                      parent=self.top)
        else:
            self.hide()


class TabularDataManager:
    """Class interfacing Ttk's Treeview widget with a basic data model.

    Similar, but not identical to widgets.AirportChooser.

    """
    def __init__(self, master, config, identVar, treeData, columnsMetadata,
                 identColName, initSortBy, treeWidget,
                 treeUpdatedCallback=None):
        """Constructor for TabularDataManager instances.

        master          -- Tk master object (“root”)
        config          -- Config instance
        identVar        -- StringVar instance that will be automatically
                           updated to reflect the currently selected
                           item (currently selected in the Treeview
                           widget)
        treeData        -- sequence of tuples where each tuple has one
                           element per column displayed in the Treeview.
                           This is the complete data set used to fill
                           the Treeview. The word “tuple” is used to
                           ease understanding here, but any sequence
                           can do.
        columnsMetadata -- mapping from symbolic column names for the
                           Ttk Treeview widget to widgets.Column
                           instances
        identColName    -- symbolic name of the column whose contents is
                           linked to 'identVar'; the data held for this
                           column in treeData must be of type 'str' in
                           order to be compatible with 'identVar'.
        initSortBy      -- symbolic name of the column used to initially
                           sort the Treeview widget
        treeWidget      -- Ttk Treeview widget used as a multicolumn
                           list (in other words, a table)
        treeUpdatedCallback
                        -- function called after the Treeview widget has
                           been updated (after every update of the
                           Treeview widget contents). The function is
                           called without any argument.

        The 'identVar' StringVar instance and the Treeview widget must
        be created by the caller. However, this constructor takes care
        of connecting them with the appropriate methods.

        """
        _attrs = ("master", "config", "identVar", "treeData", "columnsMetadata",
                  "identColName", "treeWidget", "treeUpdatedCallback")
        for attr in _attrs:
            setattr(self, attr, locals()[attr])

        self.sortBy = initSortBy

        # List of item indices (into treeData) that are the result of the last
        # sort operation (i.e., this describes a permutation on treeData).
        self.indices = []

        columnMapping = {}
        for col in self.columnsMetadata.values():
            self.configColumn(col)
            columnMapping[col.dataIndex] = col

        # Column instances in the order of their dataIndex
        self.columns = [ columnMapping[i]
                         for i in sorted(columnMapping.keys()) ]
        for i, col in enumerate(self.columns):
            assert i == col.dataIndex, (i, col.dataIndex)

        self.treeWidget.bind('<<TreeviewSelect>>', self.onTreeviewSelect)
        self.updateContents()

    def loadData(self, treeData):
        """Load a new dataset into the Treeview widget."""
        self.treeData = treeData
        self.updateContents()

    def updateContents(self, dataChanged=True):
        """Fill the Treeview widget based on self.treeData and sorting params.

        If one is sure that neither the items in self.treeData nor the
        column formatting functions have changed since the Treeview was
        last updated, differences in the Treeview display can only come
        from the order in which items are sorted. In such a case, one
        may call this method with 'dataChanged=False' in order to save
        time in the case where nothing has changed (i.e., after sorting,
        the items would be in the same order as saved in self.indices).

        """
        col = self.columnsMetadata[self.sortBy]
        treeData = self.treeData  # for performance
        dataIndex = col.dataIndex # ditto

        l = [ (treeData[i][dataIndex], i) for i in range(len(treeData)) ]
        if col.sortFunc is not None:
            keyFunc = lambda t: col.sortFunc(t[0])
        else:
            keyFunc = lambda t: t[0]

        l.sort(key=keyFunc, reverse=int(col.sortOrder))
        # Describes the permutation on treeData giving the desired sort order
        indices = [ t[1] for t in l ]

        if self.indices != indices or dataChanged:
            self.indices = indices
            self._updateTreeWidget()

    def _updateTreeWidget(self):
        """Update the contents of the Treeview widget."""
        curIdent = self.identVar.get()
        identColName = self.identColName
        tree = self.treeWidget
        # Delete all children of the root element. Even when the elements just
        # need to be put in a different order, it is much faster this way than
        # using tree.move() for each element.
        tree.delete(*tree.get_children())

        hasSpecialFormatter = any(
            ( col.formatFunc is not None for col in self.columns ))

        if hasSpecialFormatter:
            columns = self.columns

            formatter = []
            identity = lambda x: x
            for dataIndex in range(len(self.columns)):
                f = columns[dataIndex].formatFunc
                formatter.append(identity if f is None else f)

            for idx in self.indices:
                rawValues = self.treeData[idx]
                values = [ formatter[dataIndex](rawValue)
                           for dataIndex, rawValue in enumerate(rawValues) ]
                tree.insert("", "end", values=values)
        else:
            # Optimize the case where no column has a formatter function
            for idx in self.indices:
                tree.insert("", "end", values=self.treeData[idx])

        # Select a suitable item in the repopulated tree, if it is non-empty.
        if self.indices:
            try:
                # This will set self.identVar via the TreeviewSelect
                # event handler.
                tree.FFGoGotoItemWithValue(identColName, curIdent)
            except widgets.NoSuchItem:
                # We could not find the previously-selected airport
                # → select the first one in the tree.
                tree.FFGoGotoItemWithIndex(0)
        else:                   # empty tree, we can't select anything
            self.identVar.set('')

        if self.treeUpdatedCallback is not None:
            self.treeUpdatedCallback()

    def configColumn(self, col):
        measure = self.config.treeviewHeadingFont.measure
        if col.widthText is not None:
            width = max(map(measure, (col.widthText + "  ", col.title + "  ")))
        else:
            width = measure(col.title + "  ")

        kwargs = col.columnKwargs.copy()
        kwargs[col.widthKeyword] = width

        self.treeWidget.column(
            col.name, anchor=col.anchor, stretch=col.stretch, **kwargs)

        def sortFunc(col=col):
            self.sortTree(col)
        self.treeWidget.heading(col.name, text=col.title, command=sortFunc)

    def sortTree(self, col):
        """Sort tree contents when a column header is clicked on."""
        if self.sortBy == col.name:
            col.sortOrder = col.sortOrder.reverse()
        else:
            self.sortBy = col.name
            col.sortOrder = widgets.SortOrder.ascending

        self.updateContents(dataChanged=False) # repopulate the Treeview

    def onTreeviewSelect(self, event=None):
        tree = self.treeWidget

        currentSel = tree.selection()
        assert currentSel, "Unexpected empty selection in TreeviewSelect event"

        self.identVar.set(tree.set(currentSel[0], self.identColName))
