# gps_tool.py --- A dialog for performing geodetic calculations between two
#                 chosen points (airports...)
# -*- coding: utf-8 -*-
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
from tkinter.messagebox import showwarning

from ..constants import PROGNAME
from .. import common_transl
from . import widgets
from ..geo import geodesy
from ..misc import normalizeHeading
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


class GPSTool:
    """GPS Tool dialog."""

    geodCalc = geodesy.GeodCalc()

    def __init__(self, master, config, app):
        for attr in ("master", "config", "app"):
            setattr(self, attr, locals()[attr])

        setupTranslationHelper(config)

        # These are used to break observer loops with widget A being modified,
        # causing an update of widget B, itself causing an update of widget
        # A...
        self.dontUpdateFlightDuration = self.dontUpdateGroundSpeed = False

        self.top = tk.Toplevel(self.master)
        self.top.transient(self.master)
        # Uncomment this to disallow interacting with other windows
        # self.top.grab_set()
        self.top.title(_('GPS Tool'))
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

        # *********************************************************************
        # *                   The airports selection frame                    *
        # *********************************************************************

        # Frame providing padding around the “Airport A” and “Airport B”
        # LabelFrame widgets
        airportsOuterFrame = ttk.Frame(
            panedWindow,
            padding=(outerFramesPadding, outerFramesPadding,
                     outerFramesPadding, outerFramesHalfSep))
        panedWindow.add(airportsOuterFrame, weight=100)

        # Airport A
        self.icaoVarA = tk.StringVar()
        airportChooserA, searchEntryA, searchClearButtonA, airportSearchTreeA \
            = self.airportChooserLabelFrame(
                container=airportsOuterFrame, row=0, column=0,
                columnWeight=100, labelFramesPadding=labelFramesPadding,
                frameTitle=_("Airport A"), icaoVar=self.icaoVarA)

        spacer = ttk.Frame(airportsOuterFrame)
        spacer.grid(row=0, column=1, sticky="nsew")
        airportsOuterFrame.grid_columnconfigure(1, minsize="12p", weight=10)

        # Airport B
        self.icaoVarB = tk.StringVar()
        airportChooserB, searchEntryB, searchClearButtonB, airportSearchTreeB \
            = self.airportChooserLabelFrame(
                container=airportsOuterFrame, row=0, column=2,
                columnWeight=100, labelFramesPadding=labelFramesPadding,
                frameTitle=_("Airport B"), icaoVar=self.icaoVarB)

        # Frame providing padding around the “Calculations” LabelFrame
        calcOuterFrame = ttk.Frame(
            panedWindow, padding=(outerFramesPadding, outerFramesHalfSep,
                                  outerFramesPadding, outerFramesPadding))
        panedWindow.add(calcOuterFrame, weight=100)

        calcFrame = ttk.LabelFrame(calcOuterFrame,
                                   text=_("Calculations"),
                                   padding=labelFramesPadding)
        calcFrame.grid(row=0, column=0, sticky="nsew")
        calcOuterFrame.grid_rowconfigure(0, weight=100)
        calcOuterFrame.grid_columnconfigure(0, weight=100)

        # *********************************************************************
        # *   Left frame of Calculations, containing parameters (units...)    *
        # *********************************************************************
        calcLeftFrame = ttk.Frame(calcFrame)
        calcLeftFrame.grid(row=0, column=0, sticky="nsw")
        calcFrame.grid_rowconfigure(0, weight=100)
        calcFrame.grid_columnconfigure(0, weight=100, pad="30p")

        # Length unit (nautical miles or kilometers)
        leftSubframe1 = ttk.Frame(calcLeftFrame)
        leftSubframe1.grid(row=0, column=0, sticky="nsw")

        lengthUnitLabel = ttk.Label(leftSubframe1, text=_("Distance in"))
        lengthUnitLabel.grid(row=0, column=0, sticky="w")
        leftSubframe1.grid_columnconfigure(0, weight=100)

        self.lengthUnit = tk.StringVar()
        self.lengthUnit.set("nautical mile")
        nautMilesButton = ttk.Radiobutton(
            leftSubframe1, variable=self.lengthUnit,
            text=_("nautical miles"), value="nautical mile",
            padding=("10p", 0, "10p", 0))
        nautMilesButton.grid(row=0, column=1, sticky="w")
        leftSubframe1.grid_rowconfigure(0, pad="5p")
        kilometersButton = ttk.Radiobutton(
            leftSubframe1, variable=self.lengthUnit,
            text=_("kilometers"), value="kilometer",
            padding=("10p", 0, "10p", 0))
        kilometersButton.grid(row=1, column=1, sticky="w")

        leftSpacerHeight = "20p"
        leftSpacer = ttk.Frame(calcLeftFrame)
        leftSpacer.grid(row=1, column=0, sticky="nsew")
        calcLeftFrame.grid_rowconfigure(
            1, minsize=leftSpacerHeight, weight=100)

        # Magnetic or true bearings
        leftSubframe2 = ttk.Frame(calcLeftFrame)
        leftSubframe2.grid(row=2, column=0, sticky="nsw")

        bearingsTypeLabel = ttk.Label(leftSubframe2, text=_("Bearings"))
        bearingsTypeLabel.grid(row=0, column=0, sticky="w")
        leftSubframe2.grid_columnconfigure(0, weight=100)

        self.bearingsType = tk.StringVar()
        magBearingsButton = ttk.Radiobutton(
            leftSubframe2, variable=self.bearingsType,
            text=pgettext("Bearings", "magnetic"), value="magnetic",
            padding=("10p", 0, "10p", 0))
        magBearingsButton.grid(row=0, column=1, sticky="w")
        leftSubframe2.grid_rowconfigure(0, pad="5p")
        trueBearingsButton = ttk.Radiobutton(
            leftSubframe2, variable=self.bearingsType,
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

        leftSpacer = ttk.Frame(calcLeftFrame)
        leftSpacer.grid(row=3, column=0, sticky="nsew")
        calcLeftFrame.grid_rowconfigure(
            3, minsize=leftSpacerHeight, weight=100)

        # Speed unit (knots or kilometers per hour)
        leftSubframe3 = ttk.Frame(calcLeftFrame)
        leftSubframe3.grid(row=4, column=0, sticky="nsw")

        speedUnitLabel = ttk.Label(leftSubframe3, text=_("Speed in"))
        speedUnitLabel.grid(row=0, column=0, sticky="w")
        leftSubframe3.grid_columnconfigure(0, weight=100)

        self.speedUnit = tk.StringVar()
        self.speedUnit.set("knot")
        knotsButton = ttk.Radiobutton(
            leftSubframe3, variable=self.speedUnit,
            text=_("knots"), value="knot",
            padding=("10p", 0, "10p", 0))
        knotsButton.grid(row=0, column=1, sticky="w")
        leftSubframe3.grid_rowconfigure(0, pad="5p")
        kmhButton = ttk.Radiobutton(
            leftSubframe3, variable=self.speedUnit,
            text=_("km/h"), value="km/h",
            padding=("10p", 0, "10p", 0))
        kmhButton.grid(row=1, column=1, sticky="w")

        spacer = ttk.Frame(calcLeftFrame)
        spacer.grid(row=5, column=0, sticky="nsew")
        calcLeftFrame.grid_rowconfigure(
            5, minsize=leftSpacerHeight, weight=100)

        # Calculation method (Vincenty or Karney)
        leftSubframe4 = ttk.Frame(calcLeftFrame)
        leftSubframe4.grid(row=6, column=0, sticky="nsw")

        calcMethodLabel = ttk.Label(leftSubframe4,
                                    text=_("Calculation method"))
        calcMethodLabel.grid(row=0, column=0, sticky="w")

        self.calcMethodVar = tk.StringVar()
        karneyMethodRadioButton = ttk.Radiobutton(
            leftSubframe4, variable=self.calcMethodVar,
            text=_("Karney"), value="karneyInverse",
            padding=("10p", 0, "10p", 0))
        karneyMethodRadioButton.grid(row=0, column=1, sticky="w")
        vincentyMethodRadioButton = ttk.Radiobutton(
            leftSubframe4, variable=self.calcMethodVar,
            text=_("Vincenty et al."), value="vincentyInverseWithFallback",
            padding=("10p", 0, "10p", 0))
        vincentyMethodRadioButton.grid(row=1, column=1, sticky="w")

        if self.geodCalc.karneyMethodAvailable():
            self.calcMethodVar.set("karneyInverse")
        else:
            self.calcMethodVar.set("vincentyInverseWithFallback")
            karneyMethodRadioButton.state(["disabled"])

        # Tooltip for the calculation method
        ToolTip(calcMethodLabel,
                common_transl.geodCalcMethodTooltipText(self.geodCalc),
                autowrap=True)

        # *********************************************************************
        # *        Right frame of Calculations, containing the results        *
        # *********************************************************************
        calcRightFrame = ttk.Frame(calcFrame)
        calcRightFrame.grid(row=0, column=1, sticky="nw")
        calcFrame.grid_rowconfigure(0, weight=100)
        calcFrame.grid_columnconfigure(1, weight=200)

        # Distance between the two airports
        distanceFrame = ttk.Frame(calcRightFrame)
        distanceFrame.grid(row=0, column=0, sticky="new")
        calcRightFrame.grid_rowconfigure(0, weight=0)
        calcRightFrame.grid_columnconfigure(0, weight=100)

        distanceLabel = ttk.Label(distanceFrame,
                                  text=_("Distance between A and B: "))
        distanceLabel.grid(row=0, column=0, sticky="w")
        distanceFrame.grid_rowconfigure(0, weight=100)

        self.distanceVar = tk.StringVar()
        distanceValueLabel = ttk.Label(distanceFrame,
                                       textvariable=self.distanceVar)
        distanceValueLabel.grid(row=0, column=1, sticky="w")

        self.distanceUnitLabelVar = tk.StringVar()
        distanceUnitLabel = ttk.Label(distanceFrame,
                                      textvariable=self.distanceUnitLabelVar)
        distanceUnitLabel.grid(row=0, column=2, sticky="w")

        rightSpacerHeight = "20p"
        spacer = ttk.Frame(calcRightFrame)
        spacer.grid(row=1, column=0, sticky="nsew")
        calcRightFrame.grid_rowconfigure(
            1, minsize=rightSpacerHeight, weight=100)

        # Bearings
        bearingsFrame = ttk.Frame(calcRightFrame)
        bearingsFrame.grid(row=2, column=0, sticky="ew")
        calcRightFrame.grid_rowconfigure(2, weight=0)

        bearingsABLabel = ttk.Label(bearingsFrame,
                                    text=_("Bearings from A to B:"))
        bearingsABLabel.grid(row=0, column=0, sticky="w")
        bearingsFrame.grid_rowconfigure(0, weight=100)
        bearingsFrame.grid_columnconfigure(0, pad="8p")

        bearingsABinitLabel = ttk.Label(
            bearingsFrame, text=pgettext(
                "bearings for a path between two points", "init: "))
        bearingsABinitLabel.grid(row=0, column=1, sticky="w")

        self.bearingABinitVar = tk.StringVar()
        bearingsABinitValueLabel = ttk.Label(
            bearingsFrame, textvariable=self.bearingABinitVar)
        bearingsABinitValueLabel.grid(row=0, column=2, sticky="w")
        bearingsFrame.grid_columnconfigure(2, pad="10p")

        spacer = ttk.Frame(bearingsFrame)
        spacer.grid(row=0, column=3, sticky="nsew")
        calcRightFrame.grid_columnconfigure(3, minsize="10p", weight=100)

        bearingsABfinalLabel = ttk.Label(
            bearingsFrame, text=pgettext(
                "bearings for a path between two points", "final: "))
        bearingsABfinalLabel.grid(row=0, column=4, sticky="w")

        self.bearingABfinalVar = tk.StringVar()
        bearingsABfinalValueLabel = ttk.Label(
            bearingsFrame, textvariable=self.bearingABfinalVar)
        bearingsABfinalValueLabel.grid(row=0, column=5, sticky="w")

        bearingsBALabel = ttk.Label(bearingsFrame,
                                    text=_("Bearings from B to A: "))
        bearingsBALabel.grid(row=1, column=0, sticky="w")
        bearingsFrame.grid_rowconfigure(1, weight=100)

        bearingsBAinitLabel = ttk.Label(
            bearingsFrame, text=pgettext(
                "bearings for a path between two points", "init: "))
        bearingsBAinitLabel.grid(row=1, column=1, sticky="w")

        self.bearingBAinitVar = tk.StringVar()
        bearingsBAinitValueLabel = ttk.Label(
            bearingsFrame, textvariable=self.bearingBAinitVar)
        bearingsBAinitValueLabel.grid(row=1, column=2, sticky="w")

        # Spacer present in row 0 column 3, no need to insert another one here

        bearingsBAfinalLabel = ttk.Label(
            bearingsFrame, text=pgettext(
                "bearings for a path between two points", "final: "))
        bearingsBAfinalLabel.grid(row=1, column=4, sticky="w")

        self.bearingBAfinalVar = tk.StringVar()
        bearingsBAfinalValueLabel = ttk.Label(
            bearingsFrame, textvariable=self.bearingBAfinalVar)
        bearingsBAfinalValueLabel.grid(row=1, column=5, sticky="w")

        spacer = ttk.Frame(calcRightFrame)
        spacer.grid(row=3, column=0, sticky="nsew")
        calcRightFrame.grid_rowconfigure(
            3, minsize=rightSpacerHeight, weight=100)

        # Flight duration in relation to ground speed
        groundSpeedVsFlightTimeFrame = ttk.Frame(calcRightFrame)
        groundSpeedVsFlightTimeFrame.grid(row=4, column=0, sticky="ew")
        calcRightFrame.grid_rowconfigure(4, weight=0)

        groundSpeedLabel = ttk.Label(groundSpeedVsFlightTimeFrame,
                                     text=_("Ground speed: "))
        groundSpeedLabel.grid(row=0, column=0, sticky="w")
        groundSpeedVsFlightTimeFrame.grid_rowconfigure(0, weight=100)

        self.groundSpeed = tk.StringVar()
        self.groundSpeed.set("475") # typical airliner speed (in knots)
        self.groundSpeedEntry = ttk.Entry(
            groundSpeedVsFlightTimeFrame, width=5,
            textvariable=self.groundSpeed)
        self.groundSpeedEntry.grid(row=0, column=1)
        groundSpeedVsFlightTimeFrame.grid_columnconfigure(1, minsize="20p",
                                                          pad="5p")
        self.speedUnitLabelVar = tk.StringVar()
        speedUnitLabel = ttk.Label(groundSpeedVsFlightTimeFrame,
                                   textvariable=self.speedUnitLabelVar)
        speedUnitLabel.grid(row=0, column=2, sticky="w")
        groundSpeedVsFlightTimeFrame.grid_columnconfigure(2, pad="20p")

        # Double arrow between ground speed and flight duration
        linkLabel = ttk.Label(groundSpeedVsFlightTimeFrame, text="↔")
        linkLabel.grid(row=0, column=3, sticky="ew")
        groundSpeedVsFlightTimeFrame.grid_columnconfigure(3, pad="20p")

        self.flightDuration = tk.StringVar() # minutes
        self.flightDurationEntry = ttk.Entry(
            groundSpeedVsFlightTimeFrame, width=6,
            textvariable=self.flightDuration)
        self.flightDurationEntry.grid(row=0, column=4)
        groundSpeedVsFlightTimeFrame.grid_columnconfigure(4, pad="5p")

        # Time unit + human-readable form for the flight duration (such as
        # “1 day, 12 hours and 5 minutes”)
        self.flightDurationPostfixVar = tk.StringVar()
        flightDurationPostfixLabel = ttk.Label(
            groundSpeedVsFlightTimeFrame,
            textvariable=self.flightDurationPostfixVar)
        flightDurationPostfixLabel.grid(row=0, column=5, sticky="w")
        # Use a minimum column size in order to avoid frequent layout changes
        # when the flight duration is modified.
        groundSpeedVsFlightTimeFrame.grid_columnconfigure(
            5, minsize=tk.font.Font().measure("0"*60))

        ToolTip(flightDurationPostfixLabel,
                _("Decomposition using Julian years\n"
                  "(1 Julian year = {days} days)").format(
                      days=locale.format("%.02f", 365.25, grouping=True)))

        # This causes the initialization of the various fields of the dialog
        # because of the TreeviewSelect event generated by the initial airport
        # selection from airportChooserLabelFrame().
        self.icaoVarA.trace("w", self.updateResults)
        self.icaoVarB.trace("w", self.updateResults)
        self.calcMethodVar.trace("w", self.updateResults)

        self.bearingsType.trace("w", self.updateDisplayedResults)
        self.lengthUnit.trace("w", self.updateDisplayedResults)
        self.speedUnit.trace("w", self.onSpeedUnitChanged)
        self.groundSpeed.trace("w", self.updateDisplayedFlightTime)
        self.flightDuration.trace("w", self.updateDisplayedGroundSpeed)
        self.flightDuration.trace("w", self.updateFlightDurationPostfix)
        self.updateDisplayedSpeedUnit()

        # Initially focus the search field for airport A
        searchEntryA.focus_set()

    def airportChooserLabelFrame(self, *, container, row, column, columnWeight,
                                 labelFramesPadding, frameTitle, icaoVar):
        labelFrame = ttk.LabelFrame(container, text=frameTitle,
                                    padding=labelFramesPadding)
        labelFrame.grid(row=row, column=column, sticky="nsew")
        container.grid_rowconfigure(row, weight=100)
        container.grid_columnconfigure(column, weight=100)

        leftSubframe = ttk.Frame(labelFrame, padding=(0, 0, "30p", 0))
        leftSubframe.grid(row=0, column=0, sticky="ew")
        labelFrame.grid_rowconfigure(0, weight=100)
        labelFrame.grid_columnconfigure(0, weight=100)

        searchLabel = ttk.Label(leftSubframe, text=_("Search: "))
        searchLabel.grid(row=0, column=0, sticky="w")

        # The link to a StringVar is done in the AirportChooser class
        searchEntry = ttk.Entry(leftSubframe)
        searchEntry.grid(row=0, column=1, sticky="ew")
        leftSubframe.grid_columnconfigure(1, weight=100)

        spacer = ttk.Frame(leftSubframe)
        spacer.grid(row=1, column=0, sticky="nsew")
        leftSubframe.grid_rowconfigure(1, minsize="18p", weight=100)

        # The button binding is done in the AirportChooser class
        searchClearButton = ttk.Button(leftSubframe, text=_('Clear'))
        searchClearButton.grid(row=2, column=1, sticky="w")

        # The TreeviewSelect event binding is done in the AirportChooser class
        airportSearchTree = widgets.MyTreeview(
            labelFrame, columns=["icao", "name"],
            show="headings", selectmode="browse", height=10)

        airportSearchTree.grid(row=0, column=1, sticky="nsew")
        labelFrame.grid_columnconfigure(1, weight=500)

        def airportSearchTreeTooltipFunc(region, itemID, column, self=self):
            if region == "cell":
                icao = airportSearchTree.set(itemID, "icao")
                found, airport = self.app.readAirportData(icao)

                return airport.tooltipText() if found else None
            else:
                return None

        airportChooserTooltip = TreeviewToolTip(airportSearchTree,
                                                airportSearchTreeTooltipFunc)
        airportScrollbar = ttk.Scrollbar(
            labelFrame, orient='vertical',
            command=airportSearchTree.yview, takefocus=0)
        airportScrollbar.grid(row=0, column=2, sticky="ns")

        def onAirportListScrolled(*args, airportScrollbar=airportScrollbar,
                                  airportChooserTooltip=airportChooserTooltip):
            airportScrollbar.set(*args)
            # Once the Treeview is scrolled, the tooltip is likely not to match
            # the airport under the mouse pointer anymore.
            airportChooserTooltip.hide()

        airportSearchTree.config(yscrollcommand=onAirportListScrolled)

        airportSearchColumnsList = [
            widgets.Column("icao", _("ICAO"), 0, "w", False, "width",
                           widthText="M"*4),
            widgets.Column("name", _("Name"), 1, "w", True, "width",
                           widthText="M"*20)]
        airportSearchColumns = { col.name: col
                                 for col in airportSearchColumnsList }

        airportSearchData = []
        for icao in self.config.sortedIcao():
            airport = self.config.airports[icao]
            airportSearchData.append((icao, airport.name))

        airportChooser = widgets.AirportChooser(
            self.master, self.config,
            icaoVar,                      # output variable of the chooser
            airportSearchData,
            airportSearchColumns, "icao", # Initially, sort by ICAO
            searchEntry, searchClearButton,
            airportSearchTree,
               # Delay before propagating the effect of nav keys (arrows...).
            0, # The calculation is fast enough here that now delay is needed.
            treeUpdatedCallback=lambda t=airportChooserTooltip: t.hide())

        # Initial airport selection
        curIcao = self.config.airport.get()
        try:
            # This will set icaoVar via the TreeviewSelect event handler.
            airportSearchTree.FFGoGotoItemWithValue("icao", curIcao)
        except widgets.NoSuchItem:
            icaoVar.set('')

        return (airportChooser, searchEntry, searchClearButton,
                airportSearchTree)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateResults(self, *args):
        # By default, assume the calculations couldn't be carried out to make
        # sure not to display wrong results in case we return without setting
        # these instance attributes.
        self.distance = self.bearingABinit = self.bearingABfinal = None

        icaoA = self.icaoVarA.get()
        icaoB = self.icaoVarB.get()

        if icaoA and icaoB:     # we have two defined airports, go ahead
            distCalcFunc = getattr(self.geodCalc, self.calcMethodVar.get())
            aptA = self.config.airports[icaoA]
            aptB = self.config.airports[icaoB]

            if magField is not None:
                self.magDeclA, self.magDeclB = magField.batchDecl(
                    ((aptA.lat, aptA.lon), (aptB.lat, aptB.lon)))

            try:
                g = distCalcFunc(aptA.lat, aptA.lon, aptB.lat, aptB.lon)
            except geodesy.VincentyInverseError:
                message = _('Unable to perform this calculation')
                detail = _(
                    "Could not compute the distance and bearings between "
                    "{icaoA} ({nameA}) and {icaoB} ({nameB}).\n\n"
                    "Vincenty's algorithm for the geodetic inverse problem "
                    "is known not to handle all possible cases (most notably, "
                    "it can't handle the case of two antipodal or nearly "
                    "antipodal points). Use Karney's calculation method if "
                    "you want to see the results for these two airports.") \
                    .format(icaoA=icaoA, icaoB=icaoB,
                            nameA=aptA.name, nameB=aptB.name)

                showwarning(_('{prg}').format(prg=PROGNAME), message,
                            detail=detail, parent=self.top)
            else:
                # The calculation went fine; set the relevant attributes.
                self.distance = g["s12"]        # in meters
                self.bearingABinit = g["azi1"]  # true bearing
                self.bearingABfinal = g["azi2"] # ditto

        self.updateDisplayedResults()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateDisplayedResults(self, *args):
        self.updateDisplayedDistance()
        self.updateDisplayedBearings()
        self.updateDisplayedFlightTime()

    def updateDisplayedDistance(self):
        unit = self.lengthUnit.get()

        if unit == "nautical mile":
            if self.distance is not None:
                dist = self.distance / 1852
            unitPostfix = pgettext("length unit", " nm")
        else:
            assert unit == "kilometer", unit
            if self.distance is not None:
                dist = self.distance / 1000
            unitPostfix = pgettext("length unit", " km")

        if self.distance is None:
            self.distanceVar.set("---")
        else:
            self.distanceVar.set(str(round(dist)))

        self.distanceUnitLabelVar.set(unitPostfix)

    def updateDisplayedBearings(self):
        bearingsType = self.bearingsType.get()
        assert bearingsType in ("magnetic", "true"), bearingsType
        magBearings = (bearingsType == "magnetic")
        azi1 = self.bearingABinit
        azi2 = self.bearingABfinal

        if azi1 is None or self.distance == 0:
            initBearingAB = finalBearingBA = "---"
        else:
            if magBearings:
                initBearingAB = normalizeHeading(azi1 - self.magDeclA)
                finalBearingBA = normalizeHeading(azi1 + 180.0 - self.magDeclA)
            else:
                initBearingAB = normalizeHeading(azi1)
                finalBearingBA = normalizeHeading(azi1 + 180.0)

        if azi2 is None or self.distance == 0:
            finalBearingAB = initBearingBA = "---"
        else:
            if magBearings:
                finalBearingAB = normalizeHeading(azi2 - self.magDeclB)
                initBearingBA = normalizeHeading(azi2 + 180.0 - self.magDeclB)
            else:
                finalBearingAB = normalizeHeading(azi2)
                initBearingBA = normalizeHeading(azi2 + 180.0)

        self.bearingABinitVar.set(str(initBearingAB))
        self.bearingABfinalVar.set(str(finalBearingAB))
        self.bearingBAinitVar.set(str(initBearingBA))
        self.bearingBAfinalVar.set(str(finalBearingBA))

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateDisplayedGroundSpeed(self, *args):
        if self.dontUpdateGroundSpeed:
            self.dontUpdateGroundSpeed = False
            return

        # Every code path below sets self.groundSpeed. This must not in turn
        # cause an update to the flight duration...
        self.dontUpdateFlightDuration = True

        if self.distance is None:
            self.groundSpeed.set("")
            return

        durationStr = self.flightDuration.get()
        try:
            durationMin = float(durationStr)
            if durationMin < 0:
                raise ValueError
        except ValueError:
            self.groundSpeed.set("")
            return

        unit = self.speedUnit.get()
        assert unit in ("knot", "km/h")

        try:
            if unit == "knot":
                gs = 60*self.distance / (durationMin*1852)
            else:
                gs = 60*self.distance / (durationMin*1000)
        except ZeroDivisionError:
            self.groundSpeed.set("")
        else:
            self.groundSpeed.set(str(round(gs)))

    def _setInvalidFlightDuration(self):
        self.flightDuration.set("")

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateDisplayedFlightTime(self, *args):
        if self.dontUpdateFlightDuration:
            self.dontUpdateFlightDuration = False
            return

        # Every code path below sets self.flightDuration. This must not in turn
        # cause an update to the ground speed...
        self.dontUpdateGroundSpeed = True

        if self.distance is None:
            self._setInvalidFlightDuration()
            return

        groundSpeedStr = self.groundSpeed.get()
        try:
            groundSpeed = float(groundSpeedStr)
            if groundSpeed < 0:
                raise ValueError
        except ValueError:
            self._setInvalidFlightDuration()
            return

        unit = self.speedUnit.get()
        assert unit in ("knot", "km/h")

        try:
            if unit == "knot":
                durationMin = 60*self.distance / (groundSpeed*1852)
            else:
                durationMin = 60*self.distance / (groundSpeed*1000)
        except ZeroDivisionError:
            self._setInvalidFlightDuration()
            return

        roundedMin = round(durationMin)
        self.flightDuration.set(str(roundedMin))

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateFlightDurationPostfix(self, *args):
        """
        Update the converted value of flight time in days, hours and minutes."""
        baseUnitStr = pgettext("unit of time", "min")
        durationStr = self.flightDuration.get()

        try:
            durationMin = float(durationStr)
            if durationMin < 0:
                raise ValueError
        except ValueError:
            self.flightDurationPostfixVar.set(baseUnitStr)
            return

        roundedMin = round(durationMin)
        l = [baseUnitStr]

        if roundedMin >= 60:
            # Print a user-friendly representation of the flight duration if it
            # is at least one minute.
            l.append(" (" + self.decomposeMinutes(roundedMin) + ")")

        self.flightDurationPostfixVar.set(''.join(l))

    def decomposeMinutes(self, nMin):
        """Decompose an integral number of minutes."""
        # 1 Julian year = 365.25 days. This one is easier to handle separately
        # because of the non-integral number. 525960 = 365.25*24*60.
        years, remainingMin = divmod(nMin, 525960)

        hours, minutes = divmod(remainingMin, 60)
        days, hours = divmod(hours, 24)
        l = []

        if years:
            l.append(_("{nYears} {years}").format(
                nYears=locale.format("%d", years, grouping=True),
                years=ngettext("year", "years", years)))

        if days:
            l.append(_("{nDays} {days}").format(
                nDays=locale.format("%d", days, grouping=True),
                days=ngettext("day", "days", days)))

        if hours:
            l.append(_("{nHours} {hours}").format(
                nHours=locale.format("%d", hours, grouping=True),
                hours=ngettext("hour", "hours", hours)))

        if minutes:
            l.append(_("{nMinutes} {minutes}").format(
                nMinutes=locale.format("%d", minutes, grouping=True),
                minutes=ngettext("minute", "minutes", minutes)))

        if len(l) >= 2:
            res = ", ".join(l[:-1]) + pgettext("duration expression",
                                               " and ") + l[-1]
        elif l:                 # len(l) == 1, actually
            res = l[0]
        else:                   # 0 minutes in total
            # Use the same expression as above for uniformity and to avoid
            # creating useless work for translations
            res = _("{nMinutes} {minutes}").format(
                nMinutes=locale.format("%d", 0, grouping=True),
                minutes=ngettext("minute", "minutes", minutes))

        return res

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onSpeedUnitChanged(self, *args):
        self.updateDisplayedSpeedUnit()

        groundSpeedStr = self.groundSpeed.get()
        try:
            groundSpeed = float(groundSpeedStr)
        except ValueError:
            return

        unit = self.speedUnit.get()
        assert unit in ("knot", "km/h")

        if unit == "knot":
            gs = groundSpeed / 1.852
        else:
            gs = 1.852*groundSpeed

        self.dontUpdateFlightDuration = True
        self.groundSpeed.set(str(round(gs)))

    def updateDisplayedSpeedUnit(self):
        unit = self.speedUnit.get()
        assert unit in ("knot", "km/h")

        if unit == "knot":
            unitPostfix = pgettext("speed unit", " kn")
        else:
            unitPostfix = pgettext("speed unit", " km/h")

        self.speedUnitLabelVar.set(unitPostfix)

    def hide(self, event=None):
        """Hide the GPS Tool dialog."""
        self.top.withdraw()

    def show(self, event=None):
        """Unhide a hidden GPS Tool dialog."""
        self.top.deiconify()

    def destroy(self, event=None):
        """Destroy the GPS Tool dialog."""
        self.top.destroy()
        # Normally, this should allow Python's garbage collector to free some
        # memory, however it doesn't work so well. Presumably, the Tk widgets
        # stay in memory even when they are not referenced anymore...
        self.app.setGPSToolToNone()
