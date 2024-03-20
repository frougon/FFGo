"""Application main window."""


import os
import sys
import platform
import locale
import subprocess
import socket
import re
import abc
import itertools
import functools
import collections
import enum
import traceback
from gettext import translation
import threading
import queue as queue_mod       # keep 'queue' available for variable bindings
from tkinter import *
import tkinter as tk
from tkinter import ttk
from tkinter import constants as tkc
import tkinter.filedialog as fd
from tkinter.scrolledtext import ScrolledText
from xml.etree import ElementTree
from tkinter.messagebox import askyesno, showerror
import shlex
import textwrap
import condconfigparser

from ..logging import logger
from .. import misc
from ..misc import resourceExists, textResourceStream, binaryResourceStream
from .. import config as config_mod
from . import tooltip
from .tooltip import ToolTip
from . import widgets
from .configwindow import ConfigWindow
from . import infowindow
from .. import constants
# Wildcard import inherited from FGo!. I suggest to rather use qualified names
# such as 'constants.FOOBAR', except for very frequently used things such as
# PROGNAME, which could be imported explicitely if this wildcard import were to
# be removed.
from ..constants import *
from .. import fgdata
from ..fgdata.parking import ParkingSource
from .pressure_converter import PressureConverterDialog

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import geographiclib
    HAS_GEOGRAPHICLIB = True
except ImportError:
    HAS_GEOGRAPHICLIB = False


def setupTranslationHelper(config):
    global N_, pgettext_noop, pgettext

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext
    pgettext_noop = translationHelper.pgettext_noop
    N_ = translationHelper.N_

def setupTranslationHelperInOtherModules(config):
    from ..fgdata import airport as airport_mod
    from ..fgdata import parking as parking_mod

    for module in (airport_mod, parking_mod):
        module.setupTranslationHelper(config)


class PassShortcutsToApp:
    """Mixin class to override some bindings of standard Tkinter widgets.

    For now, the class ensures that Ctrl-F will trigger
    App.onControlF_KeyPress(), which is the central place where this
    shortcut is handled.

    This class is used to customize Text and Entry widgets of FFGo's
    main window. In other windows (e.g., Preferences), one should use
    standard Tkinter widgets, since Ctrl-F is only supposed to run
    FlightGear when the main window is active.

    """
    def __init__(self, app):
        self.FFGoApp = app
        self.bind('<Control-KeyPress-f>', self.onControlF_KeyPress)

    def onControlF_KeyPress(self, event):
        self.FFGoApp.onControlF_KeyPress(event)
        return "break"

class MyText(Text, PassShortcutsToApp):
    """As the Text widget, but passes Ctrl-F to App.onControlF_KeyPress().

    Note: the first argument to the constructor must be the application
          instance! Other arguments are passed as is to the Text widget.

    """
    def __init__(self, app, *args, **kwargs):
        Text.__init__(self, *args, **kwargs)
        PassShortcutsToApp.__init__(self, app)

class MyEntry(Entry, PassShortcutsToApp):
    """As the Entry widget, but passes Ctrl-F to App.onControlF_KeyPress().

    Note: the first argument to the constructor must be the application
          instance! Other arguments are passed as is to the Entry widget.

    """
    def __init__(self, app, *args, **kwargs):
        Entry.__init__(self, *args, **kwargs)
        PassShortcutsToApp.__init__(self, app)


class App:

    def __init__(self, master, config, params):
        self.params = params
        self.master = master
        self.config = config

        setupTranslationHelper(config)
        setupTranslationHelperInOtherModules(config)
        self.surveyDependencies()

        self.options = StringVar()
        self.translatedPark = StringVar()
        self.translatedRwy = StringVar()
#------ Menu ------------------------------------------------------------------
        self.menubar = Menu(self.master)

        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label=_('Load...'), command=self.configLoad)
        self.filemenu.add_command(label=_('Reload config file'),
                                  accelerator=_('Ctrl-R'), command=self.reset)
        self.filemenu.add_command(label=_('Save as...'),
                                  command=self.configSave)
        self.filemenu.add_separator()
        self.filemenu.add_command(label=_('Run FlightGear'),
                                  accelerator=_('Ctrl-F'), command=self.runFG)
        self.filemenu.add_separator()
        self.filemenu.add_command(label=_('Save & Quit'),
                                  accelerator=_('Ctrl-Q'),
                                  command=self.saveAndQuit)
        self.filemenu.add_command(label=_('Quit'), command=self.quit)
        self.menubar.add_cascade(label=_('File'), menu=self.filemenu)

        self.settmenu = Menu(self.menubar, tearoff=0)
        # BEWARE: when adding new entries to this menu, don't forget to update
        #         the INDEX_OF_INSTALLED_APT_LIST_MENU_ENTRY variable below.
        self.settmenu.add_checkbutton(label=_('Show installed airports only'),
                                      variable=self.config.filteredAptList,
                                      command=self.filterAirports)
        self.settmenu.add_command(label=_('Update list of installed airports'),
                                  command=self.updateInstalledAptList)
        # Index of the menu entry just added, starting from 0
        INDEX_OF_INSTALLED_APT_LIST_MENU_ENTRY = 1

        def _updUpdateInstalledAptListMenuEntryState(*args, **kwargs):
            """
            Update the state of the 'Update list of installed airports' menu entry.

            Enable or disable the menu entry depending on the value of
            self.config.filteredAptList.

            """
            if self.config.filteredAptList.get():
                newState = "normal"
            else:
                newState = "disabled"
            self.settmenu.entryconfigure(
                INDEX_OF_INSTALLED_APT_LIST_MENU_ENTRY, state=newState)

        # This will be needed in reset()
        self._updUpdateInstalledAptListMenuEntryState = \
                                      _updUpdateInstalledAptListMenuEntryState
        self.config.filteredAptList.trace(
            'w', _updUpdateInstalledAptListMenuEntryState)

        self.settmenu.add_separator()
        self.settmenu.add_checkbutton(
            label=_('Show FlightGear arguments'),
            variable=self.config.showFGCommand,
            command=self.changeFGCommandConfig)
        self.settmenu.add_checkbutton(
            label=_('Show FlightGear arguments in separate window'),
            variable=self.config.showFGCommandInSeparateWindow,
            command=self.changeFGCommandConfig)
        self.settmenu.add_checkbutton(
            label=_('Show FlightGear output'),
            variable=self.config.showFGOutput,
            command=self.changeFGOutputConfig)
        self.settmenu.add_checkbutton(
            label=_('Show FlightGear output in separate window'),
            variable=self.config.showFGOutputInSeparateWindow,
            command=self.changeFGOutputConfig)
        self.settmenu.add_separator()
        self.settmenu.add_command(label=_('Preferences'),
                                  command=self.showConfigWindow)
        self.menubar.add_cascade(label=_('Settings'), menu=self.settmenu)

        self.toolsmenu = Menu(self.menubar, tearoff=0)
        self.toolsmenu.add_command(label=_('Airport Finder'),
                                   command=self.showAirportFinder)
        self.toolsmenu.add_command(label=_('GPS Tool'),
                                   command=self.showGPSTool)
        self.toolsmenu.add_command(label='METAR',
                                   command=self.showMETARWindow)
        self.toolsmenu.add_command(label=_('Pressure converter'),
                                   command=self.showPressureConverterDialog)
        self.toolsmenu.add_command(label=_('Copy FG shell-equivalent command'),
                                   command=self.copyFGCommandToClipboard)
        if self.params.test_mode:
            self.toolsmenu.add_command(label=_('Test stuff'),
                                       accelerator=_('Ctrl-T'),
                                       command=self.testStuff)
        self.menubar.add_cascade(label=_('Tools'), menu=self.toolsmenu)

        self.helpmenu = Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label=_('Help'), command=self.showHelpWindow)
        self.helpmenu.add_command(label=_("Show available fgfs options"),
                                  command=self.showFgfsCmdLineHelp)
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label=_('About'), command=self.about)
        self.menubar.add_cascade(label=_('Help'), menu=self.helpmenu)

        self.master.config(menu=self.menubar)

        self.mainPanedWindow = ttk.PanedWindow(self.master, orient='vertical')
        self.mainPanedWindow.pack(side='top', fill='both', expand=True)

        self.topPanedWindow = ttk.PanedWindow(self.mainPanedWindow,
                                              orient="horizontal")
        self.mainPanedWindow.add(self.topPanedWindow, weight=100)

#------ Aircraft list ---------------------------------------------------------
        self.frame1 = ttk.Frame(self.topPanedWindow, padding=8)
        self.topPanedWindow.add(self.frame1, weight=100)

        # Fill self.frame1 from bottom to top, because when vertical space is
        # scarce, the last elements added are the first to suffer from the lack
        # of space. Here, we want the aircraft list to be shrunk before the
        # search field and the 'Clear' button.
        self.frame11 = ttk.Frame(self.frame1, padding=(0, 5, 0, 0))
        self.frame11.pack(side='bottom', fill='x')

        # The link to a StringVar is done in the AircraftChooser class
        self.aircraftSearch = MyEntry(self, self.frame11, bg=TEXT_BG_COL)
        self.aircraftSearch.pack(side='left', fill='x', expand=True)
        ttk.Frame(self.frame11, width=5).pack(side='left') # horizontal spacer
        self.aircraftSearchButton = Button(self.frame11, text=_('Clear'))
        self.aircraftSearchButton.pack(side='left')

        ttk.Frame(self.frame1, height=3).pack(side='bottom') # vertical spacer

        self.frame12 = ttk.Frame(self.frame1)
        self.frame12.pack(side='bottom', fill='both', expand=True)

        aircraftListScrollbar = ttk.Scrollbar(self.frame12, orient='vertical',
                                              takefocus=0)

        def onAircraftListScrolled(
                *args, self=self, aircraftListScrollbar=aircraftListScrollbar):
            aircraftListScrollbar.set(*args)
            # Once the Treeview is scrolled, the tooltip is likely not to match
            # the aircraft under the mouse pointer anymore.
            self.aircraftTooltip.hide()

        # Used below for the tooltip function
        aircraftListDisplayColumns = ["name", "use count"]
        #
        # widgets.MyTreeview is a subclass of the Ttk Treeview widget. The
        # TreeviewSelect event binding is done in the AircraftChooser class.
        # Each item will have an associated “directory” value that can be used
        # in conjunction with the “name” value to precisely identify the
        # aircraft. Only the name will be displayed in the MyTreeview widget,
        # though.
        #
        # Approximate matching of aircraft names
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # The “match key” invisible column in self.aircraftList below is used
        # to efficiently implement approximate matching of aircraft names. For
        # instance, an aircraft named 'EC-137D' will have its match key set to
        # 'ec137d' by App.buildAircraftList() (lowercase, and hyphens + other
        # similar chars removed). The same characters (hyphens, underscores...)
        # are removed from the search query before it is compared to each
        # aircraft match key. For obvious efficiency reasons, the match keys
        # for each aircraft are computed only when the aircraft list is built.
        # The “match key” column is included first in the list of columns,
        # because this allows AircraftChooser.findMatches() to be a bit more
        # efficient (no need to store unused values in local variables for
        # *each* aircraft of the list).
        self.aircraftList = widgets.MyTreeview(
            self.frame12, columns=["match key", "name", "directory",
                                   "use count"],
            displaycolumns=aircraftListDisplayColumns, show="headings",
            selectmode="browse", height=14,
            yscrollcommand=onAircraftListScrolled)
        self.aircraftList.pack(side='left', fill='both', expand=True)

        aircraftListScrollbar.config(command=self.aircraftList.yview)
        aircraftListScrollbar.pack(side='left', fill='y')

        def aircraftListTooltipFunc(region, itemID, column, self=self):
            if region == "cell":
                d = self.aircraftList.set(itemID)
                aircraftName, aircraftDir = d["name"], d["directory"]

                # If the Aircraft instance can't be found, it's a bug.
                aircraft = self.config.aircraftWithNameAndDir(aircraftName,
                                                              aircraftDir)
                return aircraft.tooltipText()
            elif region == "heading" and column == "#{num}".format(
                 num=aircraftListDisplayColumns.index("use count")+1):
                    tooltipText = _(
                        "Number of days the aircraft was used during the "
                        "selected period (cf. “Aircraft statistics show "
                        "period” in the Preferences dialog)")
                    return textwrap.fill(tooltipText, width=62)
            else:
                return None

        self.aircraftTooltip = tooltip.TreeviewToolTip(self.aircraftList,
                                                       aircraftListTooltipFunc)

        aircraftListColumnsList = [
            widgets.Column("match key", "", 0, "w", True),
            widgets.Column("name", _("Aircraft"), 1, "w", True, "width",
                           widthText="M"*12,
                           sortFunc=lambda name: name.lower()),
            widgets.Column("directory", _("Directory"), 2, "w", True),
            widgets.Column("use count", _("Use count"), 3, "e", False, "width",
                           widthText="M"*4,
                           sortOrder=widgets.SortOrder.descending)]
        aircraftListColumns = { col.name: col
                               for col in aircraftListColumnsList }

        self.aircraftChooser = widgets.AircraftChooser(
            self.master, self.config,
            self.config.aircraftId, # output variable of the chooser
            [],                 # empty list for now, will be filled by reset()
            aircraftListColumns,
            "use count",        # initially sort by aircraft use count
            self.aircraftSearch, self.aircraftSearchButton,
            self.aircraftList,   # MyTreeview instance (subclass of Treeview)
            150, # delay before propagating the effect of nav keys (arrows...)
            treeUpdatedCallback=lambda self=self: self.aircraftTooltip.hide(),
            # Since the tree is empty for now, clearing the search field would
            # “update” the MyTreeview widget to display an empty list, and
            # since no item could be selected, self.config.aircraftId would get
            # nullified via AircraftChooser.setNullOutputVar().
            clearSearchOnInit=False)

#------ Left middle pane (aircraft thumbnail, airport, runway, ...) -----------
        self.frame2 = ttk.Frame(self.topPanedWindow, padding=8)
        self.topPanedWindow.add(self.frame2, weight=50)
        # Fill self.frame2 from bottom to top, because when vertical space is
        # scarce, the last elements added are the first to suffer from the lack
        # of space. Here, we want the aircraft thumbnail to be shrunk before
        # the buttons.

        # AI Scenarios
        self.frame21 = Frame(self.frame2)
        self.frame21.pack(side='bottom', fill='both')

        self.scenarios = Label(self.frame21, text=_('Select Scenario'),
                               relief='groove', padx=6, pady=6)
        self.scenarios.pack(side='left', fill='both', expand=True)
        self.scenarios.bind('<Button-1>', self.popupScenarios)

        ttk.Frame(self.frame2, height=20).pack(side='bottom') # vertical spacer

        # Airport, rwy and parking
        self.frame22 = ttk.Frame(self.frame2)
        self.frame22.pack(side='bottom', fill='x')
        # First column
        self.frame221 = ttk.Frame(self.frame22, padding=(0, 0, 4, 0))
        self.frame221.pack(side='left', fill='x')

        self.park_label = Label(self.frame221, text=_('Parking:'))
        self.park_label.pack(side='bottom', anchor='w')

        self.rwy_label = Label(self.frame221, text=_('Rwy:'))
        self.rwy_label.pack(side='bottom', anchor='w')

        self.airport_label = Label(self.frame221, text=_('Airport:'))
        self.airport_label.pack(side='bottom', anchor='w')

        # Second column
        self.frame222 = ttk.Frame(self.frame22)
        self.frame222.pack(side='left', fill='x', expand=True)

        self.parkLabel = Label(self.frame222, width=12,
                               textvariable=self.translatedPark,
                               relief='groove', borderwidth=2)
        self.parkLabel.pack(side='bottom', fill='x', expand=True)

        self.rwyLabel = Label(self.frame222, width=12,
                              textvariable=self.translatedRwy,
                              relief='groove', borderwidth=2)
        self.rwyLabel.pack(side='bottom', fill='x', expand=True)

        self.airportLabel = Label(self.frame222, width=12,
                                  textvariable=self.config.airport,
                                  relief='groove', borderwidth=2)
        self.airportLabel.pack(side='bottom', fill='x', expand=True)
        self.airportLabel.bind('<Button-1>', self.popupCarrier)

        # Aircraft
        self.frame23 = ttk.Frame(self.frame2)
        self.frame23.pack(side='bottom', expand=True)

        self.aircraftLabel = Label(self.frame23,
                                   textvariable=self.config.aircraft)
        self.aircraftLabel.pack(side='top')

        self.thumbnail = Label(self.frame23,
                               width=STD_AIRCRAFT_THUMBNAIL_SIZE[0],
                               height=STD_AIRCRAFT_THUMBNAIL_SIZE[1])
        self.thumbnail.pack(side='top', fill='y')
        # At application initialization, when reset() is called, the observers
        # on Config.aircraftId have not been attached yet. Therefore, one has
        # to explicitely call updateImage() in order to have an image in
        # self.thumbnail and avoid severe layout problems.
        self.updateImage()

#------ Right middle pane (Miscellaneous settings) ----------------------------
        self.translatedTimeOfDay = tk.StringVar()
        self.translatedSeason = tk.StringVar()

        timeOfDayChoices = [N_("current time"), N_("dawn"), N_("morning"),
                            N_("noon"), N_("afternoon"), N_("dusk"),
                            N_("evening"), N_("midnight")]
        timeOfDayReverseMapping = collections.OrderedDict(
            ( (_(s), s) for s in timeOfDayChoices ))

        def _updateTimeOfDay(*args,
                             timeOfDayReverseMapping=timeOfDayReverseMapping):
            if self.translatedTimeOfDay.get() == _("current time"):
                self.config.timeOfDay.set("")
            else:
                 self.config.timeOfDay.set(
                    timeOfDayReverseMapping[self.translatedTimeOfDay.get()])

        seasonChoices = [pgettext_noop("season", "default"),
                         pgettext_noop("season", "summer"),
                         pgettext_noop("season", "winter")]
        seasonReverseMapping = collections.OrderedDict(
           ( (pgettext("season", s), s) for s in seasonChoices ))

        def _updateSeason(*args, seasonReverseMapping=seasonReverseMapping):
            if self.translatedSeason.get() == pgettext("season", "default"):
                self.config.season.set("")
            else:
                self.config.season.set(
                    seasonReverseMapping[self.translatedSeason.get()])

        self.translatedTimeOfDay.trace('w', _updateTimeOfDay)
        self.translatedSeason.trace('w', _updateSeason)

        # Enclosing frame to obtain vertical centering
        frame3ext = ttk.Frame(self.topPanedWindow, padding=8)
        self.topPanedWindow.add(frame3ext, weight=30)
        # Inside frame
        self.frame3 = ttk.Frame(frame3ext)
        # This 'expand=True' is the key for vertical centering inside frame3ext
        self.frame3.pack(expand=True)

        # One frame that will contain two columns (frames)
        self.frame31 = ttk.Frame(self.frame3)
        self.frame31.pack(side='top', anchor='w')

        # First column
        self.frame311 = ttk.Frame(self.frame31, padding=(0, 0, 12, 0))
        self.frame311.pack(side='left')
        timeOfDayLabel = ttk.Label(self.frame311, text=_("Time of day:"))
        timeOfDayLabel.pack(side='top')

        # Vertical spacer
        ttk.Frame(self.frame311, height=6).pack(side='top')

        seasonLabel = ttk.Label(self.frame311, text=_("Season:"))
        seasonLabel.pack(side='top', anchor='w')

        # Second column
        self.frame312 = ttk.Frame(self.frame31)
        self.frame312.pack(side='left')

        if self.config.timeOfDay.get():
            initTimeOfDay = _(self.config.timeOfDay.get())
        else:
            initTimeOfDay = _("current time")

        timeOfDayMenu = ttk.OptionMenu(self.frame312, self.translatedTimeOfDay,
                                       initTimeOfDay,
                                       *timeOfDayReverseMapping.keys())
        timeOfDayMenu.pack(side='top', anchor='w')

        # Vertical spacer
        ttk.Frame(self.frame312, height=6).pack(side='top')

        if self.config.season.get():
            initSeason = pgettext("season", self.config.season.get())
        else:
            initSeason = pgettext("season", "default")

        seasonMenu = ttk.OptionMenu(self.frame312, self.translatedSeason,
                                    initSeason,
                                    *seasonReverseMapping.keys())
        seasonMenu.pack(side='top', anchor='w')

        # font = tk.font.Font() # same as tk.font.nametofont("TkDefaultFont")
        # maxWidth = max(( font.measure(text) for text in
        #                  timeOfDayChoices + seasonChoices ))
        maxLen = max(( len(text) for text in itertools.chain(
            timeOfDayReverseMapping.keys(), seasonReverseMapping.keys()) ))
        for widget in (timeOfDayMenu, seasonMenu):
            # Stupid interface that seems to work with a number of characters!
            widget.config(width=maxLen)

        # Back to one-column layout
        self.frame32 = ttk.Frame(self.frame3)
        self.frame32.pack(side='top', anchor='w')

        # Vertical spacer
        ttk.Frame(self.frame32, height=22).pack(side='top')

        self.enableTerraSyncCb = ttk.Checkbutton(
            self.frame32,
            text=_('Automatic scenery download'),
            variable=self.config.enableTerraSync)
        self.enableTerraSyncCb.pack(side='top', anchor='w')

        ToolTip(self.enableTerraSyncCb,
                _("Enabling this causes FlightGear to automatically download "
                  "scenery as you fly (this FlightGear feature is called "
                  "TerraSync). The location where these downloads take "
                  "place can be chosen in the Preferences dialog.\n\nSee "
                  "<http://wiki.flightgear.org/TerraSync> for more details."),
                autowrap=True)

        # Vertical spacer
        ttk.Frame(self.frame32, height=8).pack(side='top')

        self.enableRealWeatherFetchCb = ttk.Checkbutton(
            self.frame32,
            text=_('Automatic download of weather data'),
            variable=self.config.enableRealWeatherFetch)
        self.enableRealWeatherFetchCb.pack(side='top', anchor='w')

        ToolTip(self.enableRealWeatherFetchCb,
                _("Enabling this causes FlightGear to automatically download "
                  "weather data as you fly (in the form of METAR reports). "
                  "This causes the weather in FlightGear to match the current "
                  "real world weather at the location of your flight."),
                autowrap=True)

        # Vertical spacer
        ttk.Frame(self.frame32, height=22).pack(side='top')

        startFGFullScreenCb = ttk.Checkbutton(
            self.frame32,
            text=_('Start FlightGear in full screen'),
            variable=self.config.startFGFullScreen)
        startFGFullScreenCb.pack(side='top', anchor='w')

        # Vertical spacer
        ttk.Frame(self.frame32, height=8).pack(side='top')

        startFGPausedCb = ttk.Checkbutton(
            self.frame32,
            text=_('Start FlightGear paused'),
            variable=self.config.startFGPaused)
        startFGPausedCb.pack(side='top', anchor='w')

        # Vertical spacer
        ttk.Frame(self.frame32, height=22).pack(side='top')

        self.enableMSAACb = ttk.Checkbutton(
            self.frame32,
            text=_('Enable multi-sample anti-aliasing'),
            variable=self.config.enableMSAA)
        self.enableMSAACb.pack(side='top', anchor='w')

        ToolTip(self.enableMSAACb,
                _("Enabling this makes any still image in FlightGear smoother "
                  "(less pronounced pixelation effect). It is also likely "
                  "to reduce the frame rate, though maybe in a negligible "
                  "way—just try it."),
                autowrap=True)

        # Vertical spacer
        ttk.Frame(self.frame32, height=8).pack(side='top')

        self.enableRembrandtCb = ttk.Checkbutton(
            self.frame32,
            text=_('Use the Rembrandt renderer'),
            variable=self.config.enableRembrandt)
        self.enableRembrandtCb.pack(side='top', anchor='w')

        ToolTip(self.enableRembrandtCb,
                _("Enable the Rembrandt renderer, which uses a technique "
                  "known as deferred rendering. The most remarkable feature "
                  "of this renderer is light management (reflections, "
                  "shadows, night scenes...). Please note that it is "
                  "significantly slower than both the default renderer "
                  "and the ALS renderer (“Atmospheric Light Scattering”)."),
                autowrap=True)

#------ Airport list ----------------------------------------------------------
        self.frame4 = Frame(self.topPanedWindow, borderwidth=8)
        self.topPanedWindow.add(self.frame4, weight=100)

        # Fill self.frame4 from bottom to top, because when vertical space is
        # scarce, the last elements added are the first to suffer from the lack
        # of space. Here, we want the airport list to be shrunk before the
        # search field and the 'Clear' button.
        self.frame41 = ttk.Frame(self.frame4, padding=(0, 5, 0, 0))
        self.frame41.pack(side='bottom', fill='x')

        # The link to a StringVar is done in the AirportChooser class
        self.airportSearch = MyEntry(self, self.frame41, bg=TEXT_BG_COL)
        self.airportSearch.pack(side='left', fill='x', expand=True)
        ttk.Frame(self.frame41, width=5).pack(side='left') # horizontal spacer
        self.airportSearchButton = Button(self.frame41, text=_('Clear'))
        self.airportSearchButton.pack(side='left')

        ttk.Frame(self.frame4, height=3).pack(side='bottom') # vertical spacer

        self.frame42 = Frame(self.frame4, borderwidth=1)
        self.frame42.pack(side='bottom', fill='both', expand=True)

        self.airportListScrollbar = Scrollbar(self.frame42, orient='vertical',
                                              takefocus=0)

        def onAirportListScrolled(*args, self=self):
            self.airportListScrollbar.set(*args)
            # Once the Treeview is scrolled, the tooltip is likely not to match
            # the airport under the mouse pointer anymore.
            self.airportTooltip.hide()

        # Used below for the tooltip function
        airportListDisplayColumns = ["icao", "name", "use count"]
        # Subclass of Ttk's Treeview. The TreeviewSelect event binding is done
        # in the AirportChooser class.
        self.airportList = widgets.MyTreeview(
            self.frame42, columns=airportListDisplayColumns, # show all columns
            show="headings", selectmode="browse", height=14,
            yscrollcommand=onAirportListScrolled)
        self.airportList.pack(side='left', fill='both', expand=True)

        self.airportListScrollbar.config(command=self.airportList.yview)
        self.airportListScrollbar.pack(side='left', fill='y')

        def airportListTooltipFunc(region, itemID, column, self=self):
            if region == "cell":
                icao = self.airportList.set(itemID, "icao")
                found, airport = self.readAirportData(icao)

                return airport.tooltipText() if found else None
            elif region == "heading" and column == "#{num}".format(
                 num=airportListDisplayColumns.index("use count")+1):
                    tooltipText = _(
                        "Number of days the airport was visited during the "
                        "selected period (cf. “Airports statistics show "
                        "period” in the Preferences dialog)")
                    return textwrap.fill(tooltipText, width=62)
            else:
                return None

        self.airportTooltip = tooltip.TreeviewToolTip(self.airportList,
                                                      airportListTooltipFunc)

        airportListColumnsList = [
            widgets.Column("icao", _("ICAO"), 0, "w", False, "width",
                           widthText="M"*4),
            widgets.Column("name", _("Airport name"), 1, "w", True, "width",
                           widthText="M"*17),
            widgets.Column("use count", _("Visit count"), 2, "e", False,
                           "width", widthText="M"*4,
                           sortOrder=widgets.SortOrder.descending)]
        airportListColumns = { col.name: col
                               for col in airportListColumnsList }

        self.airportChooser = widgets.AirportChooser(
            self.master, self.config,
            self.config.airport, # output variable of the chooser
            [],                 # empty list for now, will be filled by reset()
            airportListColumns,
            "use count",        # initially sort by airport visit count
            self.airportSearch, self.airportSearchButton,
            self.airportList,   # MyTreeview instance (subclass of Treeview)
            150, # delay before propagating the effect of nav keys (arrows...)
            treeUpdatedCallback=lambda self=self: self.airportTooltip.hide(),
            # Since the tree is empty for now, clearing the search field would
            # “update” the MyTreeview widget to display an empty list, and
            # since no item could be selected, self.config.airport would get
            # nullified via AirportChooser.setNullOutputVar().
            clearSearchOnInit=False)

#------ FlightGear process status and buttons ---------------------------------
        self.frame4 = Frame(self.mainPanedWindow, borderwidth=4)
        # Zero weight ensures the frame is visible even when starting with a
        # main window that is not very tall.
        self.mainPanedWindow.add(self.frame4, weight=0)

        self.frame41 = Frame(self.frame4, borderwidth=4)
        self.frame41.pack(side='right', fill='x')

        # FlightGear process status
        self.fgStatusText = StringVar()
        self.fgStatusText.set(_('Ready'))
        self.fgStatusLabel = Label(self.frame4, textvariable=self.fgStatusText,
                                   background="#88ff88")
        self.fgStatusLabel.pack(side='left', fill='both', expand=True)

        self.frame42 = ttk.Frame(self.frame4, width=6)
        self.frame42.pack(side='right')

        # Buttons
        self.sq_button = Button(self.frame41, text=_('Save & Quit'),
                                command=self.saveAndQuit)
        self.sq_button.pack(side='left')

        self.reset_button = Button(self.frame41, text=_('Reload config'),
                                   command=self.reset)
        ToolTip(self.reset_button,
                _("Reload the configuration file ({cfg_file})").format(
                    cfg_file=CONFIG))
        self.reset_button.pack(side='left')

        self.run_button = Button(self.frame41, text=_('Run FG'),
                                 command=self.runFG)
        self.run_button.pack(side='left')
#------ Text windows ----------------------------------------------------------
        self.innerPanedWindow = ttk.PanedWindow(self.mainPanedWindow,
                                                orient='horizontal')
        self.mainPanedWindow.add(self.innerPanedWindow, weight=100)

        self.frame51 = ttk.Frame(self.innerPanedWindow)
        self.innerPanedWindow.add(self.frame51, weight=100)

        option_window_sv = Scrollbar(self.frame51, orient='vertical')
        option_window_sh = Scrollbar(self.frame51, orient='horizontal')
        self.option_window = MyText(self,
                                    self.frame51, bg=TEXT_BG_COL, wrap='none',
                                    yscrollcommand=option_window_sv.set,
                                    xscrollcommand=option_window_sh.set)
        option_window_sv.config(command=self.option_window.yview, takefocus=0)
        option_window_sh.config(command=self.option_window.xview, takefocus=0)
        self.option_window.bind('<<Modified>>', self.onOptionWindowModified)
        option_window_sh.pack(side='bottom', fill='x')
        self.option_window.pack(side='left', fill='both', expand=True)
        option_window_sv.pack(side='left', fill='y')

        self.FGOutput = FGOutput(
            self, self.config.showFGOutput, parent=self.innerPanedWindow,
            show=self.config.showFGOutput.get(),
            windowDetached=self.config.showFGOutputInSeparateWindow.get(),
            geomVariable=self.config.FGOutputGeometry, paneWeight=150)
        self.FGCommand = FGCommand(
            self, self.config.showFGCommand, parent=self.mainPanedWindow,
            show=self.config.showFGCommand.get(),
            windowDetached=self.config.showFGCommandInSeparateWindow.get(),
            geomVariable=self.config.FGCommandGeometry, paneWeight=100)

#------------------------------------------------------------------------------

        self.default_fg = self.rwyLabel.cget('fg')
        self.default_bg = self.master.cget('bg')
        self.scenarioListOpen = False
        self.currentCarrier = []
        self.setMetarToNone()         # Initialize self.metar to None
        self.setPressureConverterToNone() # Initialize
                                          # self.pressureConverterDialog to None
        self.setAirportFinderToNone() # Initialize self.airportFinder to None
        self.setGPSToolToNone()       # Initialize self.gpsTool to None

        rereadCfgFile = self.proposeConfigChanges()
        # Will set self.FGCommand.{argList,lastConfigParsingExc}
        # appropriately (actually, self.FGCommand.builder.*).
        self.reset(readCfgFile=rereadCfgFile)

        self.registerTracedVariables()
        # Config.rwy and Config.park have not been updated since their
        # creation, unless the config file has been reread (except maybe in
        # Config.sanityChecks(), before the creation of the App object anyway).
        # Therefore, calling registerTracedVariables() before reset() wouldn't
        # be enough to render this call unnecessary.
        self.updateRunwayAndParkingButtons()

        # Lock used to prevent concurent calls of self._runFG()
        # (disabling the "Run FG" button is not enough, as self.runFG()
        # can be invoked through a keyboard shortcut).
        self.runFGLock = threading.Lock()
        self.setupKeyboardShortcuts()

        self.airportSearch.focus_set()

        if self.params.test_only:
            self.testStuff()
            self.master.after_idle(self.quit)

    def surveyDependencies(self):
        textWidth = 78

        l = [_('Python {}').format(misc.pythonVersionString()),
             _('CondConfigParser {}').format(condconfigparser.__version__)]

        if HAS_GEOGRAPHICLIB:
            l.append(_("GeographicLib's Python 3 implementation: version {}")
                     .format(geographiclib.__version__))

        if self.config.earthMagneticField is not None:
            l.append(self.config.earthMagneticField.getBackendDescription())

        # This attribute is also used in the About box.
        self.using = _("Using:\n") + \
                     '\n'.join([ textwrap.indent(s, '  - ') for s in l ])
        logger.notice(_("{prgWithVer} started\n{using}\n").format(
            prgWithVer=NAME_WITH_VERSION, using=self.using))

        # We can't print a translated version of the warning when the import
        # test is done at module initialization; thus, do it now.
        if not HAS_PIL:
            s = _("[{prg} warning] {libName} library not found. Aircraft "
                  "thumbnails won't be displayed.").format(prg=PROGNAME,
                                                           libName="Pillow")
            logger.warningNP(textwrap.fill(s, width=textWidth))

        if not HAS_GEOGRAPHICLIB:
            s = _("[{prg} notice] {libName}'s implementation for Python 3 not "
                  "found. {prg} has fallback strategies, therefore you "
                  "shouldn't see much of a difference. However, some "
                  "particular geodetic calculations can only be done with "
                  "{libName}. You will be notified when such a case is "
                  "encountered.").format(prg=PROGNAME, libName="GeographicLib")
            logger.noticeNP(textwrap.fill(s, width=textWidth))

        if self.config.earthMagneticField is None:
            s = _("[{prg} warning] {libName}'s MagneticField executable not "
                  "found or not working properly ({reason}). Some features "
                  "requiring knowledge about the Earth's magnetic field will "
                  "be disabled (e.g., computing a magnetic heading from a true "
                  "heading).").format(
                      prg=PROGNAME, libName="GeographicLib",
                      reason=self.config.earthMagneticFieldLastProblem)
            logger.warningNP(textwrap.fill(s, width=textWidth))

        self.config.logDetectedFlightGearVersion()

    # Regexp to ignore empty or whitespace-only elements
    _alreadyProposedChangesIgnore_cre = re.compile(r"^\s*$")

    def proposeConfigChanges(self):
        # res: whether the config will need to be reread after the changes
        # writeConfig: whether we make config changes that should be written
        #              before the function returns
        res = writeConfig = False
        l = [ s.strip() for s in
              self.config.alreadyProposedChanges.get().split(',') ]
        alreadyProposedChanges = set()
        # Don't include whitespace-only (or empty) elements into
        # alreadyProposedChanges
        for s in l:
            if not self._alreadyProposedChangesIgnore_cre.match(s):
                alreadyProposedChanges.add(s)

        if not (self.config.apt_data_source.get() or
                "APT_DATA_SOURCE_to_Scenery" in alreadyProposedChanges):
            message = _('Change “Airport data source” to “Scenery”?')
            detail = (_("""\
In old FlightGear versions (up to 2.4.0 according to
<http://wiki.flightgear.org/About_Scenery/Airports>), parking data was read
from $FG_ROOT/AI/Airports/. Up to version 1.2.1, the default {prg} setting
for “Airport data source” used to match this behavior.""")
            .replace('\n', ' ') + "\n\n" + _("""\
In contemporary versions of FlightGear, this parking data is read from
$FG_SCENERY/Airports/ instead (which is automatically updated if you use
TerraSync and have included its download directory into $FG_SCENERY). In
order to match this behavior, the default value for “Airport data
source” in {prg} has been changed to “Scenery”.""")
            .replace('\n', ' ') + "\n\n" + _("""\
Your “Airport data source” setting is currently set to the old default.
Do you want to change it to “Scenery”? Unless you are using FlightGear
2.4 or earlier, it is recommended to say “Yes”.""")
            .replace('\n', ' ') + "\n\n" + _("""\
Note: you may need to go to an airport first, let TerraSync download
scenery for a few minutes, then quit FlightGear before parking data is
available for this airport in $FG_SCENERY, allowing {prg} to use it.""")
            .replace('\n', ' ')
                      ).format(prg=PROGNAME)

            if askyesno(_('{prg}').format(prg=PROGNAME), message,
                        detail=detail, parent=self.master):
                self.config.apt_data_source.set('1')
                # The config file will have to be reread (to be on the safe
                # side; not sure it is really necessary in this case).
                res = True

            # Make sure the question is not asked again
            alreadyProposedChanges.add("APT_DATA_SOURCE_to_Scenery")
            # This must be written to the config file
            writeConfig = True

        if not (self.config.auto_update_apt.get() or
                "AUTO_UPDATE_APT_to_Automatic" in alreadyProposedChanges):
            message = _('Change “Airport database update” to “Automatic”?')
            detail = (_("""\
Whenever FlightGear's apt.dat files are updated, {prg}
must rebuild its own airport database for proper operation. This can be
done manually with the “Rebuild Airport Database” button from the
Preferences dialog, or automatically whenever {prg} detects a change in
FlightGear's apt.dat files.""")
            .replace('\n', ' ') + "\n\n" + _("""\
The default setting in {prg} for this option is now “Automatic”, because
it is convenient, with no significant drawback in my opinion. Do you
want to follow this new default and set “Airport database update” to
“Automatic”?""")
            .replace('\n', ' ')
                     ).format(prg=PROGNAME)

            if askyesno(_('{prg}').format(prg=PROGNAME), message,
                        detail=detail, parent=self.master):
                self.config.auto_update_apt.set('1')
                # The config file will have to be reread (to be on the safe
                # side; not sure it is really necessary in this case).
                res = True

            # Make sure the question is not asked again
            alreadyProposedChanges.add("AUTO_UPDATE_APT_to_Automatic")
            # This must be written to the config file
            writeConfig = True

        if writeConfig:
            self.config.alreadyProposedChanges.set(', '.join(
                sorted(alreadyProposedChanges)))
            self.config.write()

        return res

    def testStuff(self, event=None):
        pass

    def onControlF_KeyPress(self, event):
        self.runFG(event)
        return "break"

    def onControlR_KeyPress(self, event):
        self.reset(event)
        return "break"

    def setupKeyboardShortcuts(self):
        if self.params.test_mode:
            self.master.bind('<Control-KeyPress-t>', self.testStuff)

        self.master.bind('<Control-KeyPress-f>', self.onControlF_KeyPress)
        self.master.bind('<Control-KeyPress-r>', self.onControlR_KeyPress)
        self.master.bind_all('<Control-KeyPress-q>', self.saveAndQuit)

    def about(self):
        """Create 'About' window"""
        try:
            self.aboutWindow.destroy()
        except AttributeError:
            pass

        if _('Translation:') == 'Translation:':
            translator = ''
        else:
            translator = '\n\n' + _('Translation:')
        authors = _('Authors: {}').format(AUTHORS)

        missing = ""
        if self.config.earthMagneticField is None:
            # Make sure we have up-to-date information before reporting a
            # missing component.
            from ..geo.magfield import EarthMagneticField, MagVarUnavailable
            try:
                EarthMagneticField(self.config)
            except MagVarUnavailable as e:
                s = _("Magnetic variation unavailable: {reason}.").format(
                    reason=e.message)
                missing = "\n\n" + textwrap.fill(s, width=60)

        # Refresh the version info in case the user fixed his fgfs executable
        # since the last time we tried to run 'fgfs --version'.
        self.config.getFlightGearVersion(ignoreFGVersionError=True)
        if self.config.FG_version is not None:
            FG_version = self.config.FG_version
            comment = ""
        else:
            FG_version =  pgettext('FlightGear version', 'none')
            comment =  '\n' +_(
                "(you may want to check the '{fgfs}' executable and FG_ROOT "
                "paths, as well as the FlightGear working directory defined "
                "in Settings → Preferences)").format(fgfs=FG_EXECUTABLE)
        # Uses the same string as in Config.logDetectedFlightGearVersion()
        detected = _('Detected FlightGear version: {ver}').format(
            ver=FG_version) + comment

        about_text = ('{copyright}\n\n{authors}{transl}\n\n'
                      '{using}{missing}\n\n{detected}.').format(
                          copyright=COPYRIGHT, authorsLabel=authors,
                          authors=authors, transl=translator, using=self.using,
                          missing=missing, detected=detected)

        self.aboutWindow = Toplevel(borderwidth=4)
        self.aboutWindow.title(_('About'))
        self.aboutWindow.resizable(width=False, height=False)
        self.aboutWindow.transient(self.master)
        self.aboutWindow.bind('<Escape>', self._destroyAboutWindow)

        self.aboutTitle = Label(self.aboutWindow,
                                font=self.config.aboutTitleFont,
                                text=NAME_WITH_VERSION)
        self.aboutTitle.pack()
        self.aboutFrame1 = Frame(self.aboutWindow, borderwidth=1,
                                 relief='sunken', padx=8, pady=12)
        self.aboutFrame1.pack(fill='x', expand=True)
        self.aboutText = Label(
            self.aboutFrame1, text=about_text, justify='left',
            wraplength=constants.STANDARD_TEXT_WRAP_WIDTH)
        self.aboutText.pack()
        self.aboutFrame2 = Frame(self.aboutWindow, borderwidth=12)
        self.aboutFrame2.pack()
        self.aboutLicense = Button(self.aboutFrame2, text=_('License'),
                                   command=self.aboutShowLicense)
        self.aboutLicense.pack(side='left')
        self.aboutClose = Button(self.aboutFrame2, text=_('Close'),
                                 command=self._destroyAboutWindow)
        self.aboutClose.pack(side='left')

    def _destroyAboutWindow(self, event=None):
        self.aboutWindow.destroy()

    def aboutShowLicense(self):
        self.aboutText.configure(text=LICENSE)
        self.aboutTitle.destroy()
        self.aboutLicense.destroy()

    def buildAircraftList(self, clearSearch=False):
        matchKeyFunc = self.aircraftChooser.aircraftNameMatchKey
        aircraftTreeData = [ (matchKeyFunc(ac.name), ac.name, ac.dir,
                              ac.useCountForShow)
                             for ac in self.config.aircraftList ]
        # Update the aircraft list widget
        self.aircraftChooser.setTreeData(aircraftTreeData,
                                         clearSearch=clearSearch)

    def buildAirportList(self, clearSearch=False):
        if (self.config.auto_update_apt.get() or
            not os.path.isfile(constants.APT)):
            self.config.autoUpdateApt()

        if self.config.airportStatsManager is None: # application init
            # Requires the translation system to be in place
            from .. import stats_manager
            self.config.airportStatsManager = \
                                stats_manager.AirportStatsManager(self.config)
        else:
            # Save the in-memory statistics (from AirportStub instances) to
            # persistent storage. This expires old stats, according to
            # 'Config.airportStatsExpiryPeriod'.
            self.config.airportStatsManager.save()

        # This is limited to the list of installed airports if
        # 'Config.filteredAptList' is set to 1.
        self.browsableAirports = self.config.readAptDigestFile()

        # Load the saved statistics into the new in-memory AirportStub
        # instances (the set of airports may have just changed, hence the need
        # to save the stats before the in-memory airport list is updated, and
        # reload them afterwards).
        self.config.airportStatsManager.load()

        airportListData = [ (airport.icao, airport.name,
                             airport.useCountForShow)
                            for airport in self.browsableAirports ]
        # Update the airport list widget (as opposed to
        # 'self.browsableAirports', which is also an airport list in some way)
        self.airportChooser.setTreeData(airportListData,
                                        clearSearch=clearSearch)

    def commentText(self):
        """Highlight comments in text window."""
        t = self.option_window
        index = '1.0'
        used_index = [None]
        t.tag_delete('#')

        while index not in used_index:
            comment = t.search('#', index)
            comment = str(comment)

            if comment:
                endline = comment.split('.')[0] + '.end'
                t.tag_add('#', comment, endline)
                t.tag_config('#', foreground=COMMENT_COL)
                used_index.append(index)
                line = comment.split('.')[0]
                index = str(int(line) + 1) + '.0'
            else:
                index = None

    def configLoad(self):
        p = fd.askopenfilename(
            initialdir=USER_DATA_DIR,
            filetypes=[(_('{prg} Config Files').format(prg=PROGNAME), '*.ffgo'),
                       (_('FGo! Config Files'), '*.fgo')])
        if p:
            self.reset(path=p)

    def configSave(self):
        asf = fd.asksaveasfilename
        p = asf(initialdir=USER_DATA_DIR,
                filetypes=[(_('{prg} Config Files').format(prg=PROGNAME),
                            '*.ffgo')])
        if p:
            if not p.endswith('.ffgo'):
                p += '.ffgo'
            t = self.options.get()
            self.config.write(text=t, path=p)

    def filterAirports(self):
        """Update the airport list.

        Apply filter to the airport list if self.config.filteredAptList is
        True.

        """
        message = _("Building the airport list (this may take a while)...")
        infoWindow = infowindow.InfoWindow(self.master, text=message)
        self.buildAirportList()
        infoWindow.destroy()

    def getAircraft(self):      # Currently unused
        """Return the Aircraft instance selected via self.aircraftList."""
        try:
            aircraftName = self.aircraftChooser.getValue("name")
            aircraftDir = self.aircraftChooser.getValue("directory")
        except widgets.NoSelectedItem:
            # No aircraft selected. Should only happen when no aircraft is
            # available, or no aircraft matches the search query.
            return None

        # If this doesn't find anything, there must be a bug.
        return self.config.aircraftWithNameAndDir(aircraftName, aircraftDir)

    def getImage(self, aircraft):
        """Prepare a suitable thumbnail for 'aircraft'.

        Find the thumbnail in the aircraft directory and convert it to
        the appropriate size if necessary. Use a placeholder image for
        aircraft that have no thumbnail. Return an object that Tkinter
        can use as an image.

        """
        if HAS_PIL and aircraft is not None:
            path = os.path.join(aircraft.dir, 'thumbnail.jpg')
            try:
                srcImage = Image.open(path)
            except OSError:
                with binaryResourceStream(NO_THUMBNAIL_PIC) as f:
                    # Massage the image into something suitable for Tkinter
                    image = ImageTk.PhotoImage(Image.open(f))
            else:
                if srcImage.size == STD_AIRCRAFT_THUMBNAIL_SIZE:
                    pilImage = srcImage
                else:
                    pilImage = self.fitImageIntoStdSize(srcImage)

                image = ImageTk.PhotoImage(pilImage)
        else:
            # This 'PhotoImage' class is from Tkinter, not from Pillow!
            image = PhotoImage(file=NO_PIL_PIC)

        return image

    def fitImageIntoStdSize(self, srcImg):
        """Scale 'srcImg' to make it fit into STD_AIRCRAFT_THUMBNAIL_SIZE.

        Return an image with size exactly as given by
        STD_AIRCRAFT_THUMBNAIL_SIZE---that is, a (width, height) tuple,
        the unit being pixels. If 'srcImg' doesn't have the appropriate
        aspect ratio to do this naturally, the necessary borders in the
        resulting image are filled with transparent pixels.

        """
        # Create a new, fully transparent image with the standard size
        outImg = Image.new("RGBA", STD_AIRCRAFT_THUMBNAIL_SIZE,
                           (0, 0, 0, 0))
        # Create a thumbnail of the source image that fits in the previous one
        tmpImg = srcImg.copy()
        tmpImg.thumbnail(STD_AIRCRAFT_THUMBNAIL_SIZE)
        # Coordinates of the top-left corner to use when pasting tmpImg into
        # outImg so that it is horizontally and vertically centered.
        #
        # Note: use the 'size' attribute instead of 'width' and 'height', as
        #       these two attributes were only added to Pillow in version
        #       2.9.0, released on 2015-07-01 according to Pillow's ChangeLog.
        x = round(0.5*(STD_AIRCRAFT_THUMBNAIL_SIZE[0] - tmpImg.size[0]))
        y = round(0.5*(STD_AIRCRAFT_THUMBNAIL_SIZE[1] - tmpImg.size[1]))
        outImg.paste(tmpImg, box=(x, y))

        return outImg

    def popupCarrier(self, event):
        """Make pop up menu."""
        popup = Menu(tearoff=0)

        # This makes the popup menu more visible, visually similar to the
        # runway and parking popup menus, and avoids it disappearing in a flash
        # with the first entry being accidentally selected if the user just
        # clicked without holding the mouse button down.
        popup.add_command(label='', state=DISABLED,
                          background=POPUP_HEADER_BG_COL)

        popup.add_command(label=pgettext('carrier', 'None'),
                          command=self.resetCarrier)
        for i in self.config.carrier_list:
            popup.add_command(label=i[0],
                              command=lambda i=i: self.setCarrier(i))
        popup.tk_popup(event.x_root, event.y_root, 0)

    def _flightTypeDisplayName(self, flightType):
        d = {"cargo":       pgettext("flight type", "Cargo"),
             "ga":          pgettext("flight type", "General aviation"),
             "gate":        pgettext("flight type", "Gate"),
             "mil-cargo":   pgettext("flight type", "Mil. cargo"),
             "mil-fighter": pgettext("flight type", "Mil. fighter"),
             # Vertical Take-Off and Landing
             "vtol":        pgettext("flight type", "VTOL"),
             # X-Plane categories
             "hangar":      pgettext("flight type", "Hangar"),
             "misc":        pgettext("flight type", "Misc"),
             "tie-down":    pgettext("flight type", "Tie-down"),
             # There are inconsistencies between X-Plane's apt.dat file and its
             # specification...
             "tie_down":    pgettext("flight type", "Tie-down"),
             # Fallback
             "":            pgettext("flight type", "Unspecified")}

        return d.get(flightType, flightType)

    def populateAirportParkingPopup(self, origEvent, popup, headerBgColor):
        """Populate the popup menu for an airport parking."""
        d = self.readParkingData(self.config.airport.get())
        if d is not None:
            self._populateAirportParkingPopupEnd(origEvent, popup,
                                                 headerBgColor, d)
        return d

    def _populateAirportParkingPopupEnd(self, origEvent, popup, headerBgColor,
                                        parkingData):
        # First column: empty header, and one 'None' button
        popup.add_command(label='', state=DISABLED,
                          background=headerBgColor)
        popup.add_command(label=pgettext('parking position', 'None'),
                          command=lambda: self.config.park.set(''))

        # Mapping from menu item index to fgdata.parking.Parking instance
        parkingForItem = {}
        for flightType in sorted(parkingData.keys()):
            for i, parking in enumerate(parkingData[flightType]):
                parkName = str(parking)
                if not (i % 20):
                    # New column: add the column header
                    popup.add_command(
                        label=self._flightTypeDisplayName(flightType),
                        state=DISABLED,
                        background=headerBgColor,
                        columnbreak=True)

                fakeParkposOpt = self.config.fakeParkposOption.get()
                if (parking.source == ParkingSource.groundnet and
                    not fakeParkposOpt):
                    setParkFunc = lambda x=parkName: self.config.park.set(x)
                else:
                    assert (parking.source == ParkingSource.apt_dat or
                            fakeParkposOpt), (parking.source, fakeParkposOpt)

                    def setParkFunc(parking=parking, parkName=parkName):
                        s = "::apt.dat::1::{},{};lat={},lon={},heading={}" \
                            .format(len(parkName), parkName,
                                    parking.lat.precisionRepr(),
                                    parking.lon.precisionRepr(),
                                    parking.heading)
                        self.config.park.set(s)

                popup.add_command(
                    label=parkName,
                    command=setParkFunc)
                idx = popup.index(tkc.END) # index of the last item added
                parkingForItem[idx] = parking

        def parkingTooltipFunc(idx):
            try:
                parking = parkingForItem[idx]
            except KeyError:
                return None # no tooltip for this item
            else:
                return parking.tooltipText()

        self.parkingTooltip = tooltip.MenuToolTip(popup, parkingTooltipFunc)
        popup.tk_popup(origEvent.x_root, origEvent.y_root, 0)

    def popupPark(self, event):
        """Make popup menu for airport parking or carrier start position."""
        popup = Menu(tearoff=0)

        if not self.config.carrier.get(): # not in “carrier mode”
            data = self.populateAirportParkingPopup(event, popup,
                                                    POPUP_HEADER_BG_COL)
            if data is None:    # error doing the parking data lookup
                popup.destroy() # (the error dialog box has already been shown)
        else:
            L = self.currentCarrier[1:-1]
            for i in L:
                popup.add_command(label=i,
                                  command=lambda i=i: self.config.park.set(i))

            popup.tk_popup(event.x_root, event.y_root, 0)

    def _readAirportDataWrongIndexErrMsg(self, pbType, icao, aptDatPath,
                                         aptDatUncompSize, byteOffset):
        message = _('Unable to load airport data')

        if pbType == "index too large":
            startOfMsg = _("""\
Attempt to load data for airport {icao} from apt digest file '{aptDigest}' \
using index {index}, which is greater than, or equal to the supposed size of \
uncompressed '{aptDat}' ({uncompSize} bytes) as recorded in '{aptDigest}'."""
            ).format(icao=icao, aptDigest=APT, index=byteOffset,
                     aptDat=aptDatPath, uncompSize=aptDatUncompSize)
        elif pbType == "airport not found at index":
            startOfMsg = _("""\
Unable to find data for airport {icao} in apt digest file '{aptDigest}' \
at index {index}.""").format(icao=icao, aptDigest=APT, index=byteOffset)
        else:
            assert False, "Bug in {prg}, please report.".format(prg=PROGNAME)

        detail = _("""{startOfMsg} \
This may be explained by '{aptDigest}' being out of date relatively to \
'{aptDat}'. In such a case, you should just rebuild the airport database from \
the Miscellaneous tab of the Preferences dialog.

If you are *sure* this is not the explanation, please report a bug using the \
instructions on {prg}'s home page including:
  - a screenshot containing this message;
  - a copy of the '{aptDat}' and '{aptDigest}' files (DON'T REBUILD THE \
AIRPORT DATABASE before making a copy of '{aptDigest}', otherwise it will be \
useless!). Thank you.""").format(prg=PROGNAME, startOfMsg=startOfMsg,
                                 aptDigest=APT, aptDat=aptDatPath)
        showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)

    def readAirportData(self, icao):
        """Read airport data from self.config.aptDatCache or apt.dat files.

        Return a tuple of the form (found, airport) where 'found' is a
        boolean and airport an Airport instance, or None when 'found' is
        False.

        """
        for cachedIcao, cachedAirport in self.config.aptDatCache:
            if cachedIcao == icao:
                found = True
                airport = cachedAirport
                break
        else:
            # index[0] is the file index in Config.aptDatFilesInfoFromDigest,
            # index[1] is the byte offset in that file and
            # index[2] is the corresponding line number.
            index = self.config.airports[icao].airportIndex
            aptDatFileInfo = self.config.aptDatFilesInfoFromDigest[index[0]]
            aptDatPath = aptDatFileInfo.path
            if index[1] >= aptDatFileInfo.uncompSize:
                self._readAirportDataWrongIndexErrMsg(
                    "index too large", icao, aptDatPath,
                    aptDatFileInfo.uncompSize, index[1])
                return (False, None)

            found, airport = \
            self.config.aptDatSetManager.readAirportDataUsingIndex(icao, index)

            if found:
                self.config.aptDatCache.append((icao, airport))
            else:
                self._readAirportDataWrongIndexErrMsg(
                    "airport not found at index", icao, aptDatPath,
                    aptDatFileInfo.uncompSize, index[1])

        return (found, airport)

    def _readGroundnetFile(self, groundnetPath):
        parkings, exceptions = fgdata.parking.readGroundnetFile(groundnetPath)

        # Disable the error popup dialog for now: it is quite ugly and
        # annoying, and didn't have the effect I hoped (i.e., people fixing the
        # groundnet files---at least, not in many airports distributed via
        # TerraSync).
        #
        # if exceptions:
        #     message = _('Error parsing a groundnet file')
        #     detail = _("In '{file}':\n\n{errors}").format(
        #         file=groundnetPath, errors='\n'.join(map(str, exceptions)))
        #     showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)

        return parkings

    def readParkingData(self, icao):
        """Read parking/startup location data from a groundnet file or apt.dat.

        Return a dictionary if successful, or None if the apt.dat lookup
        (done as a last resort) failed. The keys of the dictionary are
        flight types (if the data was found in a groundnet) or type of
        location (if it comes from an apt.dat file). Its values are
        sequences of Parking instances.

        """
        res = {}

        # If airport data source is set to "Scenery"
        if self.config.apt_data_source.get():
            paths = [
                os.path.join(path, DEFAULT_AIRPORTS_DIR)
                for path in self.config.FG_scenery.get().split(os.pathsep) ]

            for path in paths:
                for i in range(3):
                    path = os.path.join(path, icao[i])
                groundnet = '{}.groundnet.xml'.format(icao)
                groundnetPath = os.path.join(path, groundnet)
                if os.path.isfile(groundnetPath):
                    res = self._readGroundnetFile(groundnetPath)
                    break
        # If airport data source is set to "Old default"
        else:
            path = os.path.join(self.config.ai_path, DEFAULT_AIRPORTS_DIR)
            if os.path.isdir(path):
                dirs = os.listdir(path)
                if icao in dirs:
                    path = os.path.join(path, icao)
                    groundnetPath = os.path.join(path, 'parking.xml')
                    if os.path.isfile(groundnetPath):
                        res = self._readGroundnetFile(groundnetPath)

        if not res:
            found, airport = self.readAirportData(icao)
            res = airport.parkings if found else None

        return res

    def popupRwy(self, event):
        """Popup menu offering to select between runways and/or helipads."""
        assert self.config.airport.get(), \
            "self.config.airport.get() should not be empty here"

        runways = self.readRunwayData(self.config.airport.get())
        if runways is None: # error doing the runway data lookup
            return          # (the error dialog box has already been shown)

        # Mapping from menu item index to fgdata.airport.RunwayBase instance
        runwayForItem = {}
        popup = Menu(tearoff=0)

        # This makes the popup menu more visible, visually similar
        # to the parking popup, and avoids it disappearing in a
        # flash with the first entry being accidentally selected if
        # the user just clicked without holding the button down.
        popup.add_command(label='', state=DISABLED,
                          background=POPUP_HEADER_BG_COL)

        popup.add_command(label=pgettext('runway', 'Default'),
                          command=lambda: self.config.rwy.set(''))
        for r in runways:
            popup.add_command(label=r.name, command=lambda x=r.name:
                              self.config.rwy.set(x))
            idx = popup.index(tkc.END) # index of the last item added
            runwayForItem[idx] = r

        def runwayTooltipFunc(idx):
            try:
                runway = runwayForItem[idx]
            except KeyError:
                return None # no tooltip for this item
            else:
                return runway.tooltipText()

        self.runwayTooltip = tooltip.MenuToolTip(popup, runwayTooltipFunc)
        popup.tk_popup(event.x_root, event.y_root, 0)

    def popupScenarios(self, event):
        """Make pop up list."""
        if not self.scenarioListOpen:
            self.scenarioListOpen = True
            self.scenarioList = Toplevel(borderwidth=1, relief='raised')
            self.scenarioList.overrideredirect(True)
            self.scenarioList.geometry('+%d+%d' % (event.x_root, event.y_root))
            self.master.bind('<Configure>', self.popupScenariosClose)
            self.master.bind('<Unmap>', self.popupScenariosClose)
            frame = Frame(self.scenarioList)
            frame.pack(side='top')

            popupScrollbar = Scrollbar(frame, orient='vertical')
            self.popup = Listbox(frame, bg=TEXT_BG_COL, exportselection=0,
                                 selectmode=MULTIPLE, height=15,
                                 yscrollcommand=popupScrollbar.set)
            popupScrollbar.config(command=self.popup.yview, takefocus=0)
            self.popup.pack(side='left')
            popupScrollbar.pack(side='left', fill='y')
            self.popup.bind('<Button-3>', self.scenarioDescription)

            frame1 = Frame(self.scenarioList)
            frame1.pack(side='top', fill='x')

            button = Button(frame1, text=_('OK'),
                            command=self.popupScenariosClose)
            button.pack(fill='x')

            for i in self.config.scenario_list:
                self.popup.insert('end', i)

            self.popupScenariosSelect()

    def popupScenariosClose(self, event=None):
        try:
            self.descriptionWindow.destroy()
        except AttributeError:
            pass

        L = []
        for i in self.popup.curselection():
            L.append(self.config.scenario_list[int(i)])
        self.config.scenario.set(' '.join(L))
        self.scenarioList.destroy()
        self.master.unbind('<Configure>')
        self.master.unbind('<Unmap>')
        self.scenarioListOpen = False

    def popupScenariosSelect(self):
        L = list(self.config.scenario.get().split())
        for i in L:
            if i in self.config.scenario_list:
                self.popup.selection_set(self.config.scenario_list.index(i))

    def readRunwayData(self, icao):
        found, airport = self.readAirportData(icao)

        if found:
            return airport.runways() # iterator
        else:
            return None

    def read_scenario(self, scenario):
        """Read description from a scenario."""
        text = ''
        file_name = scenario + '.xml'
        path = os.path.join(self.config.ai_path, file_name)
        root = self._get_root(path)
        # There is no consistency along scenario files where
        # the <description> tag can be found in the root tree,
        # therefore we are making a list of all occurrences
        # of the tag and return the first element (if any).
        descriptions = root.findall('.//description')
        if descriptions:
            text = self._rstrip_text_block(descriptions[0].text)

        return text

    def _get_root(self, xmlFilePath):
        tree = ElementTree.parse(xmlFilePath)
        return tree.getroot()

    def _rstrip_text_block(self, text):
        rstripped_text = '\n'.join(line.lstrip() for line in text.splitlines())
        return rstripped_text

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onMSAAToggled(self, *args):
        # MSAA and Rembrandt are mutually exclusive
        if self.config.enableMSAA.get():
            self.config.enableRembrandt.set('0')
            self.enableRembrandtCb.state(["disabled"])
        else:
            self.enableRembrandtCb.state(["!disabled"])

        self.FGCommand.update()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onRembrandtToggled(self, *args):
        # MSAA and Rembrandt are mutually exclusive
        if self.config.enableRembrandt.get():
            self.config.enableMSAA.set('0')
            self.enableMSAACb.state(["disabled"])
        else:
            self.enableMSAACb.state(["!disabled"])

        self.FGCommand.update()

    def registerTracedVariables(self):
        self.options.trace('w', self.FGCommand.update)
        # There is also an observer of 'self.config.aircraftId' registered in
        # Config's constructor to update 'self.config.aircraft' and
        # 'self.config.aircraftDir'.
        self.config.aircraftId.trace('w', self.updateImage)
        self.config.aircraftId.trace('w', self.FGCommand.update)
        self.config.airport.trace('w', self.resetRwyParkAndCarrier)
        self.config.airport.trace('w', self.FGCommand.update)
        self.config.scenario.trace('w', self.FGCommand.update)
        self.config.carrier.trace('w', self.FGCommand.update)
        self.config.FG_root.trace('w', self.FGCommand.update)
        self.config.FG_scenery.trace('w', self.FGCommand.update)
        self.config.park.trace('w', self.FGCommand.update)
        self.config.park.trace('w', self.onParkingUpdate)
        self.config.rwy.trace('w', self.FGCommand.update)
        self.config.rwy.trace('w', self.onRunwayUpdate)
        self.config.timeOfDay.trace('w', self.FGCommand.update)
        self.config.season.trace('w', self.FGCommand.update)
        self.config.enableTerraSync.trace('w', self.FGCommand.update)
        self.config.enableRealWeatherFetch.trace('w', self.FGCommand.update)
        self.config.startFGFullScreen.trace('w', self.FGCommand.update)
        self.config.startFGPaused.trace('w', self.FGCommand.update)
        self.config.enableMSAA.trace('w', self.onMSAAToggled)
        self.config.enableRembrandt.trace('w', self.onRembrandtToggled)

    def reset(self, event=None, path=None, readCfgFile=True):
        """Reset data"""
        # Don't call config.update() at application initialization
        # as config object is updated at its creation anyway.
        if readCfgFile:
            self.config.update(path)

        setupTranslationHelper(self.config) # the language may have changed

        self._updUpdateInstalledAptListMenuEntryState()
        self.resetLists()
        self.resetText()

        # Update selected carrier
        if self.config.carrier.get():
            for carrierData in self.config.carrier_list:
                # Check the carrier name
                if self.config.carrier.get() == carrierData[0]:
                    self.currentCarrier = carrierData

            self.setCarrier(self.currentCarrier)
        else:
            self.resetCarrier()

        # Restore the main window geometry
        mainWindowGeometry = self.config.mainWindowGeometry.get()
        if mainWindowGeometry:
            self.master.geometry(mainWindowGeometry)

        # Restore the state and geometry of other windows
        for manager, meth in ((self.FGOutput, self.changeFGOutputConfig),
                              (self.FGCommand, self.changeFGCommandConfig)):
            # Show/hidden and detached/integrated state of FGOutput and
            # FGCommand
            meth(event)
            # Geometry if applicable
            if manager.visible and manager.windowDetached:
                manager.restoreGeometry()

        # Update the fgfs argument list preview (“Command window”)
        self.FGCommand.update()

    def resetCarrier(self):
        if self.config.carrier.get():
            self.config.park.set('')
        self.config.carrier.set('')
        self.airport_label.config(text=_('Airport:'))
        self.airportLabel.config(textvariable=self.config.airport,
                                 bg=self.default_bg)
        self.updateRunwayAndParkingButtons()

        try:
            scenario = self.currentCarrier[-1]
        except IndexError:
            pass
        else:
            c = self.config.scenario.get().split()
            if scenario in c:
                c.pop(c.index(scenario))
                self.config.scenario.set(' '.join(c))

    def resetLists(self):
        # Clear the aircraft search entry and rebuild the aircraft list at the
        # same time. The aircraft thumbnail is updated via an observer when
        # Config.aircraftId is set by Config.update().
        self.buildAircraftList(clearSearch=True)
        # Clear the airport search entry and rebuild the airport list at the
        # same time.
        self.buildAirportList(clearSearch=True)

    def resetText(self):
        t = self.option_window
        t.delete('1.0', 'end')
        t.insert('end', self.config.text)

    def runFG(self, *args, **kwargs):
        """Wrapper around self._runFG() to prevent concurrent calls.

        If self._runFG() is already running, display an error message,
        otherwise call it, passing all arguments as is. The "already
        running" check is performed with a threading.Lock instance in
        order to avoid any kind of race condition.

        """
        if self.runFGLock.acquire(blocking=False):
            self.run_button.config(state=DISABLED)

            if not self._runFG(*args, **kwargs):
                # The fgfs process could not be started, release the lock.
                self.run_button.config(state=NORMAL)
                self.runFGLock.release()
        else:
            message = _("FlightGear is already running")
            detail = _("Sorry, FlightGear is already running and we'd rather "
                       "not run two instances simultaneously under the same "
                       "account.")
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)

    def _runFG(self, event=None):
        """Run FlightGear.

        Run FlightGear in a child process and start a new thread to
        monitor it (read its stdout and stderr, wait for the process to
        exit). This way, this won't freeze the GUI during the blocking
        calls.

        Return a boolean indicating whether FlightGear could actually be
        started.

        """
        # Can only be imported once the translation system is set up
        from .. import fgcmdbuilder
        t = self.options.get()
        self.config.write(text=t)

        program = self.config.FG_bin.get()
        FG_working_dir = self.config.FG_working_dir.get()
        if not FG_working_dir:
            FG_working_dir = HOME_DIR

        if not program.strip():
            message = _('FlightGear executable not properly set')
            detail = _(
                "The name or path to the FlightGear executable is either "
                "empty or only contains whitespace. Set it in the "
                "Preferences dialog accessible from the Settings menu. The "
                "FlightGear executable is normally called '{execProgName}' on "
                "your platform.").format(
                    execProgName=misc.executableFileName("fgfs"))
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)
            return False
        elif not self.config.aircraft.get():
            message = _("No aircraft selected")
            detail = _("No valid aircraft was selected in the aircraft list.")
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)
            return False
        elif not self.config.airport.get():
            message = _("No airport selected")
            detail = _("No valid airport was selected in the airport list.")
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)
            return False
        elif self.FGCommand.argList is None:
            if isinstance(self.FGCommand.lastConfigParsingExc,
                          fgcmdbuilder.InvalidEscapeSequenceInOptionLine):
                message = _('Cannot start FlightGear now.')
                # str(self.lastConfigParsingExc) is not translated...
                detail = _("The configuration in the main text field has an "
                           "invalid syntax:\n\n{errmsg}.\n\n"
                           "See docs/README.conditional-config or the "
                           "CondConfigParser Manual for a description of the "
                           "syntax rules.").format(
                               errmsg=self.FGCommand.lastConfigParsingExc)
            elif isinstance(self.FGCommand.lastConfigParsingExc,
                            fgcmdbuilder.UnsupportedOption):
                message = _('Unsupported option in the Options Window.')
                detail = _("The configuration in the main text field uses the "
                           "fgfs option {option}, which is unsupported because "
                           "every change to its value could potentially "
                           "require a time-consuming rebuild of the airport "
                           "database. Use the “download directory” setting "
                           "of the Preferences dialog for equivalent "
                           "functionality.").format(
                              option=self.FGCommand.lastConfigParsingExc.option)
            else:
                assert False, "Unexpected exception: {!r}".format(
                    self.FGCommand.lastConfigParsingExc)

            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)
            return False

        l = ['\n' + '=' * 80 + '\n',
             _('Starting %s with following options:') % program] + \
            [ '\t{}'.format(arg) for arg in self.FGCommand.argList ] + \
            ['\n' + '-' * 80 + '\n']
        logger.notice(*l, sep='\n')

        try:
            process = subprocess.Popen([program] + self.FGCommand.argList,
                                       cwd=FG_working_dir,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True,
                                       bufsize=1) # Use line buffering
        except OSError as e:
            self.runFGErrorMessage(e)
            return False

        self.FGOutput.clear()

        # One queue for fgfs' stdout and stderr, the other for its exit
        # status (or killing signal)
        outputQueue, statusQueue = queue_mod.Queue(), queue_mod.Queue()

        self.master.bind("<<FFGoNewFgfsOutputQueued>>",
                         functools.partial(self._updateFgfsProcessOutput,
                                           queue=outputQueue))
        self.master.bind("<<FFGoFgfsProcessTerminated>>",
                         functools.partial(self._onFgfsProcessTerminated,
                                           queue=statusQueue))
        t = threading.Thread(name="FG_monitor",
                             target=self._monitorFgfsProcessThreadFunc,
                             args=(process, outputQueue, statusQueue),
                             daemon=True)
        t.start()           # start reading fgfs' stdout and stderr

        # Done here to avoid delaying the preceding 't.start()'...
        self.fgStatusText.set(_("FlightGear is running..."))
        self.fgStatusLabel.config(background="#ff8888")

        # Update the airport and aircraft usage statistics
        if not self.config.carrier.get(): # not in “carrier mode”
            self.config.airportStatsManager.recordAsUsedToday(
                self.config.airport.get())
            self.airportChooser.updateItemData(self.config.airport.get())

        self.config.aircraftStatsManager.recordAsUsedToday(
            self.config.aircraftId.get())
        self.aircraftChooser.updateItemData(self.config.aircraftId.get())

        return True

    def runFGErrorMessage(self, exc, title=None):
        title = title if title is not None else _('Unable to run FlightGear!')
        msg = _(
            'Please make sure that the “FlightGear executable”, “FG_ROOT” '
            'and “Working directory” parameters are correctly set in the '
            'Preferences dialog.')
        detail = '{}\n\n{}'.format(exc, msg)
        showerror(_('{prg}').format(prg=PROGNAME), title, detail=detail)

    def _monitorFgfsProcessThreadFunc(self, process, outputQueue, statusQueue):
        # We are using Tk.event_generate() to notify the main thread. This
        # particular method, when passed 'when="tail"', is supposed to be safe
        # to call from other threads than the Tk GUI thread
        # (cf. <https://stackoverflow.com/questions/7141509/tkinter-wait-for-item-in-queue#comment34432041_14809246>
        # and
        # <https://mail.python.org/pipermail/tkinter-discuss/2013-November/003519.html>).
        # Other Tk functions are usually considered unsafe to call from these
        # other threads.
        for line in iter(process.stdout.readline, ''):
            logger.notice(line, end='')
            outputQueue.put(line)
            try:
                self.master.event_generate("<<FFGoNewFgfsOutputQueued>>",
                                           when="tail")
                # In case Tk is not here anymore
            except TclError:
                return

        exitStatus = process.wait()
        # FlightGear is terminated and all its output has been read
        statusQueue.put(exitStatus)
        try:
            self.master.event_generate("<<FFGoFgfsProcessTerminated>>",
                                       when="tail")
        except TclError:
            return

    def _updateFgfsProcessOutput(self, event, queue=None):
        """Forward fgfs output from 'queue' to 'self.FGOutput'.

        This function, as well as all code from the FGOutput class used
        in this file, runs in the main thread (which is the GUI thread
        here). As a result, there is no risk that a detached FGOutput
        window is attached or closed while this method is being
        executed. If the user tries to do that, Tk will just queue an
        event which won't be processed until this method returns. This
        is important, because no particular precautions have been taken
        to make FGOutput thread-safe.

        """
        self.FGOutput.unlock()
        while True:             # Pop all elements present in the queue
            try:
                line = queue.get_nowait()
            except queue_mod.Empty:
                break

            self.FGOutput.appendNoUnlock(line)

        self.FGOutput.lock()

        if self.config.autoscrollFGOutput.get():
            self.FGOutput.showEnd()

    def _onFgfsProcessTerminated(self, event, queue=None):
        # There should be exactly one item in the queue now. Get it.
        exitStatus = queue.get()
        if exitStatus >= 0:
            complement = _("FG's last exit status: {0}").format(exitStatus)
            shortComplement = _("exit status: {0}").format(exitStatus)
        else:
            complement = _("FG last killed by signal {0}").format(-exitStatus)
            shortComplement = _("killed by signal {0}").format(-exitStatus)

        logger.notice(_("fgfs process terminated ({0})").format(
            shortComplement))

        self.fgStatusText.set(_('Ready ({0})').format(complement))
        self.fgStatusLabel.config(background="#88ff88")
        self.run_button.configure(state='normal')
        self.runFGLock.release()

    def saveWindowsGeometry(self):
        if self.config.saveWindowPosition.get():
            # Save the size and position of the main window.
            geometry = self.master.geometry()
        else:
            # Save the size of the main window but not its position (behavior
            # of FGo! 1.5.5).
            geometry = self.master.geometry().split('+')[0]
        self.config.mainWindowGeometry.set(geometry)

        if self.FGCommand.visible and self.FGCommand.windowDetached:
            self.FGCommand.saveGeometry()

        if self.FGOutput.visible and self.FGOutput.windowDetached:
            self.FGOutput.saveGeometry()

    def quit(self):
        """Quit the application.

        This method contains common code that should be run whenever
        FFGo is to be quit, be it via a simple “Quit” or a “Save & Quit”
        operation.

        """
        # Save the in-memory statistics to persistent storage
        self.config.airportStatsManager.save()
        self.config.aircraftStatsManager.save()

        self.master.quit()

    def saveAndQuit(self, event=None):
        """Save options to file (incl. geometry of windows) and quit."""
        self.saveWindowsGeometry()
        t = self.options.get()
        self.config.write(text=t)
        self.quit()             # run the “shared” quit() code

    def scenarioDescription(self, event):
        """Make pop up window showing AI scenario description."""
        index = self.popup.nearest(event.y)
        try:
            name = self.config.scenario_list[index]
        except IndexError:
            return
        text = self.read_scenario(name)

        try:
            self.descriptionWindow.destroy()
        except AttributeError:
            pass

        if text:
            text = name.center(80) + '\n' + ('-' * 80) + '\n' + text
            x = self.master.winfo_rootx()
            y = self.master.winfo_rooty()
            self.descriptionWindow = Toplevel(borderwidth=1, relief='raised')
            self.descriptionWindow.overrideredirect(True)
            self.descriptionWindow.geometry('+%d+%d' % (x + 10, y))
            self.descriptionText = Label(self.descriptionWindow, justify=LEFT,
                                         text=text, bg=MESSAGE_BG_COL)
            self.descriptionText.pack()
            self.descriptionText.bind('<Button-3>',
                                      self.scenarioDescriptionClose)

    def scenarioDescriptionClose(self, event=None):
        self.descriptionWindow.destroy()

    def setCarrier(self, L):
        old_scenario = ''
        if self.currentCarrier:
            old_scenario = self.currentCarrier[-1]
        if self.config.carrier.get() != L[0]:
            # The carrier described by L is different from the current carrier
            # (if any) → reset parking pos.
            self.config.park.set('')

        self.config.carrier.set(L[0])
        self.currentCarrier = L
        self.airport_label.config(text=_('Carrier:'))
        self.airportLabel.config(textvariable=self.config.carrier,
                                 bg=CARRIER_COL)
        self.config.rwy.set('')
        scenario = self.currentCarrier[-1]

        if scenario not in self.config.scenario.get().split():
            if old_scenario:
                L = self.config.scenario.get().split()
                if old_scenario in L:
                    L.pop(L.index(old_scenario))
                    self.config.scenario.set(' '.join(L))

            c = (self.config.scenario.get(), scenario)
            self.config.scenario.set(' '.join(c))

    def showConfigWindow(self):
        text = self.options.get()
        self.configWindow = ConfigWindow(self.master, self.config, text)
        # Wait for window to close and reset data if Save&Quit button was used.
        self.master.wait_window(self.configWindow.top)
        if self.configWindow.reset_flag:
            self.reset()

    def showHelpWindow(self):
        """Display help window."""
        # Find currently used language.
        lang_code = self.config.language.get()
        if not lang_code:
            try:
                lang_code = translation(
                    MESSAGES, LOCALE_DIR).info()['language']
            except OSError:
                # There is no translation for the current locale, use English
                lang_code = "en"

        if not resourceExists(HELP_STEM + lang_code):
            lang_code = 'en'

        with textResourceStream(HELP_STEM + lang_code) as readme:
            text = readme.read()

        self.showScrolledTextWindow("helpWindow",
                                    _("{prg} Help").format(prg=PROGNAME),
                                    text)

    def showFgfsCmdLineHelp(self):
        program = self.config.FG_bin.get()
        FG_root_arg = "--fg-root=" + self.config.FG_root.get()
        FG_working_dir = self.config.FG_working_dir.get()
        if not FG_working_dir:
            FG_working_dir = HOME_DIR

        # Passing 'FG_root_arg' to avoid any undesirable popup dialog from FG
        args = [program, FG_root_arg, "--help", "--verbose"]
        try:
            helpText = subprocess.check_output(args,
                                               stderr=subprocess.DEVNULL,
                                               universal_newlines=True,
                                               cwd=FG_working_dir)
        except OSError as exc:
            self.runFGErrorMessage(exc, title=_(
                "Unable to run 'fgfs --fg-root=... --help --verbose'"))
        except subprocess.CalledProcessError as exc:
            self.runFGErrorMessage(exc, title=_(
                "Error when running 'fgfs --fg-root=... --help --verbose'"))
        else:
            title = _("Output of 'fgfs --help --verbose'")
            self.showScrolledTextWindow("fgfsCmdLineHelpWindow", title,
                                        helpText)

    def showScrolledTextWindow(self, attrName, title, text, width=80):
        """Display 'text' in a scrollable Text widget inside a new Toplevel.

        Store the Toplevel instance in the attribute 'attrName' of
        'self'. If such an instance already exists before this method is
        called, it is first destroyed, then a new one is created.

        """
        try:
            oldTopLevel = getattr(self, attrName)
        except AttributeError:
            pass
        else:
            oldTopLevel.destroy()
            delattr(self, attrName)

        topLevel = Toplevel(self.master)
        setattr(self, attrName, topLevel)
        topLevel.transient(self.master)
        topLevel.title(title)

        def destroyFunc(event=None, attrName=attrName, topLevel=topLevel):
            topLevel.destroy()
            delattr(self, attrName)

        topLevel.protocol("WM_DELETE_WINDOW", destroyFunc)
        topLevel.bind('<Escape>', destroyFunc)

        scrolledText = ScrolledText(topLevel, bg=MESSAGE_BG_COL, width=width)
        scrolledText.pack(side='left', fill='both', expand=True)
        scrolledText.insert('end', text)
        scrolledText.configure(state='disabled')

    def showAirportFinder(self, event=None):
        """Show the Airport Finder dialog."""
        # This import indirectly requires the translation system to be in
        # place.
        from . import airport_finder

        if self.airportFinder is None:
            # Create a new dialog from scratch
            self.airportFinder = airport_finder.AirportFinder(
                self.master, self.config, self)
        else:
            # Unhide an already-created dialog
            self.airportFinder.show()

    # Method called from AirportFinder.destroy() (otherwise, that would be
    # ridiculous)
    def setAirportFinderToNone(self):
        # Allow the garbage collector to free up the memory. In theory, at
        # least...
        self.airportFinder = None

    def showGPSTool(self, event=None):
        """Show the GPS Tool dialog."""
        # This import indirectly requires the translation system to be in
        # place.
        from . import gps_tool

        if self.gpsTool is None:
            # Create a new dialog from scratch
            self.gpsTool = gps_tool.GPSTool(self.master, self.config, self)
        else:
            # Unhide an already-created dialog
            self.gpsTool.show()

    # Method called from GPSTool.destroy() (otherwise, that would be
    # ridiculous)
    def setGPSToolToNone(self):
        # Allow the garbage collector to free up the memory. In theory, at
        # least...
        self.gpsTool = None

    def showMETARWindow(self, event=None):
        # This import indirectly requires the translation system to be in
        # place.
        from .metar import Metar

        if self.metar is not None:
            self.metar.quit()

        self.metar = Metar(self, self.master, self.config, MESSAGE_BG_COL)

    # Method called from Metar.quit() (otherwise, that would be ridiculous)
    def setMetarToNone(self):
        self.metar = None

    def showPressureConverterDialog(self, event=None):
        if self.pressureConverterDialog is not None:
            self.pressureConverterDialog.show()
        else:
            self.pressureConverterDialog = PressureConverterDialog(
                self.master, self.config, self)

    # Method called from PressureConverterDialog.quit()
    def setPressureConverterToNone(self):
        self.pressureConverterDialog = None

    def copyFGCommandToClipboard(self, event=None):
        # FGCommand.argList is None in case errors prevented its preparation
        args = self.FGCommand.argList or []
        command = ' '.join(map(shlex.quote,
                               [self.config.FG_bin.get()] + args))
        self.master.clipboard_clear()

        # Tkinter/Tk doesn't seem fantastic for clipboard management...
        try:
            bCommand = command.encode('latin-1')
        except UnicodeEncodeError as e:
            message = _('Impossible to copy the current FlightGear command')
            detail = _("The current FlightGear command cannot be copied "
                       "to the clipboard, because the encoding to ISO 8859-1 "
                       "(also known as “Latin 1”) failed:\n\n{exc}") \
                       .format(exc=e)
            showerror(_('{prg}').format(prg=PROGNAME), message,
                      detail=detail)
        else:
            self.master.clipboard_append(bCommand)

    def resetRwyParkAndCarrier(self, *args):
        """Reset runway, parking position and carrier after changing airport.

        Automatically called after changing the selection in the airport list.

        """
        if self.config.airport.get() != self.config.previousAirport:
            self.config.previousAirport = self.config.airport.get()

            self.config.park.set('')
            self.config.rwy.set('')

            self.resetCarrier()

    def selectNewAirport(self, icao):
        """Select a new airport. Leave carrier mode if necessary.

        Also clear the airport search field to make sure the chosen
        airport can be shown in the airport list.

        """
        # Clear the search field, otherwise the new airport may be filtered out
        # and thus invisible.
        self.airportChooser.clearSearch(setFocusOnEntryWidget=False)
        # Let Tk update the airport list
        self.master.update_idletasks()
        # Now, we can select the desired airport.
        self.airportList.FFGoGotoItemWithValue("icao", icao)

    def onRunwayUpdate(self, *args):
        """Method run when self.config.rwy is changed."""
        # Let the user select only one option: rwy or park position.
        if self.config.rwy.get():
            self.config.park.set('')

        self.updateRunwayAndParkingButtons()

    def onParkingUpdate(self, *args):
        """Method run when self.config.park is changed."""
        # Let the user select only one option: rwy or park position.
        if self.config.park.get():
            self.config.rwy.set('')

        self.updateRunwayAndParkingButtons()

    def updateRunwayAndParkingButtons(self):
        """Update runway and parking buttons (label, state and binding).

        Concerning the labels: update self.translatedPark and
        self.translatedRwy based on self.config.park and self.config.rwy. In
        each case, only the default value is translated.

        """
        for cfgVarName, labelVarName, default in (
              ('park', 'translatedPark', pgettext('parking position', 'None')),
              ('rwy', 'translatedRwy', pgettext('runway', 'Default'))):
            cfgValue = getattr(self.config, cfgVarName).get()

            # Special case for the parking name because of the special format
            # used in Config.park to represent startup locations obtained from
            # an apt.dat file.
            if cfgVarName == 'park':
                status, parkName, *rest = self.config.decodeParkingSetting(
                    cfgValue)
                if status == "apt.dat":
                    cfgValue = parkName
                    # Safety measure in case parkName were the empty string,
                    # which should not be the case unless there is a bug.
                    if not cfgValue:
                        logger.notice("Empty parking name obtained from an "
                                      "apt.dat file. Bug?")
                        cfgValue = '?'
                elif status == "invalid":
                    cfgValue = pgettext('parking position', 'Invalid')

            # Update the button label
            labelVar = getattr(self, labelVarName)
            labelVar.set(cfgValue if cfgValue else default)

        # Enable the parking button if an airport is selected or we are in
        # carrier mode
        self.setParkingButtonState(
            self.config.airport.get() or self.config.carrier.get())
        # Enable the runway button if an airport is selected and we are not
        # in carrier mode
        self.setRunwayButtonState(
            self.config.airport.get() and not self.config.carrier.get())

    def setParkingButtonState(self, state):
        """Enable or disable the button that triggers the parking popup."""
        if state:
            self.parkLabel.bind('<Button-1>', self.popupPark)
            self.parkLabel.config(state="normal")
        else:
            self.parkLabel.config(state="disabled")
            # Tkinter's <widget>.unbind() doesn't work with a function id
            self.parkLabel.unbind('<Button-1>')

    def setRunwayButtonState(self, state):
        """Enable or disable the button that triggers the runway popup."""
        if state:
            self.rwyLabel.bind('<Button-1>', self.popupRwy)
            self.rwyLabel.config(state="normal")
        else:
            self.rwyLabel.config(state="disabled")
            # Tkinter's <widget>.unbind() doesn't work with a function id
            self.rwyLabel.unbind('<Button-1>')

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateImage(self, *args):
        try:
            aircraft = self.config.getCurrentAircraft()
        except config_mod.NoSuchAircraft:
            aircraft = None

        self.image = self.getImage(aircraft)
        self.thumbnail.config(image=self.image)

    def updateInstalledAptList(self):
        """Rebuild installed airports list."""
        if self.config.filteredAptList.get():
            self.config.makeInstalledAptList()
            self.filterAirports()

    def onOptionWindowModified(self, event=None):
        self.commentText()
        self.options.set(self.option_window.get('1.0', 'end'))
        self.option_window.edit_modified(False)

    def changeFGCommandConfig(self, event=None):
        """Switch between the various configurations for FGCommand.

        The “window” may be shown or hidden, attached to or detached
        from the FFGo main window (4 possible states in total).

        """
        self.FGCommand.config(self.config.showFGCommand.get(),
                              self.config.showFGCommandInSeparateWindow.get())

    def changeFGOutputConfig(self, event=None):
        """Switch between the various configurations for FGOutput.

        The “window” may be shown or hidden, attached to or detached
        from the FFGo main window (4 possible states in total).

        """
        self.FGOutput.config(self.config.showFGOutput.get(),
                             self.config.showFGOutputInSeparateWindow.get())


class AttachableToplevel(Toplevel):
    """Class representing a Toplevel window that can be attached/detached.

    This class is used to implement Toplevel windows that can be
    integrated into the main FFGo window. Such a window has four states
    made from the combination of two “axes” containing two values each:
    visible/hidden and detached/integrated-into-the-main-window.

    Of course, the two hidden states (hidden, detached) and
    (hidden, integrated) can't be visually distinguished on a given
    screenshot, but it is important to remember if a window should
    appear detached or integrated when going from hidden to visible.

    When integrated into the FFGo window, the widgets from this class
    are not used at all: the Toplevel is destroyed. I often use the term
    “window” within double quotes to describe this set of widgets that
    appears to move from a Toplevel to the main window and vice versa.

    The geometry of the “window” in its detached state (i.e., as a
    Toplevel) is always stored before it is hidden or integrated into
    the main window, or when FFGo is exited with “Save & Quit”. This
    way, it can be restored the next time the “window” is shown in
    detached state.

    """
    def __init__(self, app, manager, showVariable, *args, **kwargs):
        Toplevel.__init__(self, *args, **kwargs)
        # Application instance
        self.app = app
        # Instance of a class such as FGCommand or FGOutput
        self.manager = manager
        # Tkinter variable linked to the menu checkbutton that is used
        # to toggle visibility of the “window”. It should always
        # correspond to the "visible" state of the underlying widgets.
        self.showVariable = showVariable
        self.bind('<Control-KeyPress-f>', self.app.onControlF_KeyPress)
        self.bind('<Control-KeyPress-r>', self.app.onControlR_KeyPress)

        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.bind('<Escape>', self.hide)

    def hide(self, event=None):
        self.manager.config(False, self.manager.windowDetached)
        self.showVariable.set(False)


# This class has abstract methods: it is impossible to create an
# instance of a subclass unless all of the abstract methods have been
# overridden by concrete ones.
class DetachableWindowManagerBase(metaclass=abc.ABCMeta):
    """Base class for managers of detachable “windows”.

    Used to implement classes such as FGCommand and FGOutput.

    """
    def __init__(self, app, showVariable, parent, title, show, windowDetached,
                 geomVariable, paneWeight):
        """Initialize a DetachableWindowManagerBase instance.

            app       -- application instance
            showVariable
                      -- Tkinter variable linked to the menu checkbutton
                         used to toggle the shown/hidden status of the
                         widgets making up the detachable “window”
            parent    -- parent of the outer Frame among the widgets to be
                         created; should be a Ttk PanedWindow
            title     -- displayed when the window is detached
            show      -- whether to show the widgets on instance creation
                         (regardless of the detached state)
            windowDetached
                      -- whether the “window” should start in detached state
            geomVariable
                      -- Tkinter variable used to remember the geometry of
                         the window in its detached state
            paneWeight
                      -- weight used when add()ing the outer Frame to
                         the parent PanedWindow (i.e., when attaching
                         it)

        """
        for name in ("app", "parent", "title", "showVariable", "geomVariable",
                     "paneWeight"):
            setattr(self, name, locals()[name])
        if show:
            self.createWidgets(windowDetached, firstTime=True)
        # Stores the current visibility state, as known by this class
        self.visible = show

    @abc.abstractmethod
    def createWidgets(self, windowDetached, firstTime=False):
        raise NotImplementedError

    @abc.abstractmethod
    def fillTextWidget(self):
        raise NotImplementedError

    def config(self, show, windowDetached):
        """Change the “window” configuration.

        show           -- whether the “window” should be visible after
                          the call
        windowDetached -- whether the “window” should be in detached
                          state after the call

        In other words, these parameters describe the desired state
        whereas self.visible and self.windowDetached correspond to the
        current state.

        """
        # Anything to destroy?
        if self.visible and (not show or self.windowDetached != windowDetached):
            if self.windowDetached:
                self.saveGeometry()
                self.topLevel.destroy()
            else:
                # Remove the pane from the parent PanedWindow
                self.parent.forget(self.outerFrame)
                self.outerFrame.destroy()

        # Anything to create?
        if show and (not self.visible or self.windowDetached != windowDetached):
            self.createWidgets(windowDetached)
            self.fillTextWidget()

        self.visible = show
        self.windowDetached = windowDetached

    def saveGeometry(self, window=None):
        if self.geomVariable is not None:
            window = window if window is not None else self.topLevel
            self.geomVariable.set(window.geometry())

    # Regexp for parsing X11-style geometry specifications (e.g.,
    # '830x916+151-10')
    geomCre = re.compile(r"""(?P<size>
                               (?P<width>\d+)x
                               (?P<height>\d+))
                             (?P<pos>
                               (?P<x_offset>[+-]\d+)?
                               (?P<y_offset>[+-]\d+)?)$""", re.VERBOSE)

    def restoreGeometry(self, window=None, firstTime=False):
        if self.geomVariable is None:
            return
        geom = self.geomVariable.get()
        if not geom:
            return

        mo = self.geomCre.match(geom)
        if not mo:
            title = _('Invalid geometry specification')
            msg = _("The following geometry specification read from "
                    "the configuration file has an invalid syntax:\n\n"
                    "  {spec}\n\n").format(spec=geom)
            message = '{0}\n\n{1}'.format(title, msg)
            detail = _("You can consult <{url}> for a description of the "
                       "allowed syntax.").format(
                           url="http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/geometry.html")
            showerror(_('{prg}').format(prg=PROGNAME), message,
                      detail=detail)
            return

        window = window if window is not None else self.topLevel
        if firstTime:
            # If one wanted to restore the size but not the position,
            # when a “window” is shown in detached state for the first
            # time in the current FFGo session:
            #   window.geometry(mo.group("size"))
            window.geometry(geom)
        else:
            window.geometry(geom)


class FGCommand(DetachableWindowManagerBase):
    """Class displaying the fgfs command in a detachable “window”."""

    # cf. DetachableWindowManagerBase for a description of the parameters
    def __init__(self, app, showVariable, parent=None, show=True,
                 windowDetached=False, geomVariable=None, paneWeight=100):
        title = _("FlightGear Command")
        DetachableWindowManagerBase.__init__(
            self, app, showVariable, parent, title,
            show, windowDetached, geomVariable, paneWeight)

        # Can only be imported once the translation system is set up
        from ..fgcmdbuilder import FGCommandBuilder
        # Manages the logic of command building (independently of the GUI)
        self.builder = FGCommandBuilder(app)

    @property
    def argList(self):
        """Convenience property returning the current fgfs argument list."""
        return self.builder.argList

    @property
    def lastConfigParsingExc(self):
        """Convenience property returning the last config parsing exception.

        Note that the exception is not necessarily a condconfigparser.error
        instance (nor an instance of a subclass).

        """
        return self.builder.lastConfigParsingExc

    def createWidgets(self, windowDetached, firstTime=False):
        if windowDetached:
            topLevel = parent = AttachableToplevel(
                self.app, self, self.showVariable, master=self.parent)
            topLevel.title(self.title)
            self.restoreGeometry(window=topLevel, firstTime=firstTime)
            outerFrameOpts = {}
        else:
            topLevel = None
            parent = self.parent
            outerFrameOpts = {"relief": "groove", "borderwidth": 2}

        outerFrame = Frame(parent, **outerFrameOpts)
        if windowDetached:
            outerFrame.pack(side='top', fill='both', expand=True)
        else:                   # add the pane to the parent PanedWindow
            self.parent.add(outerFrame, weight=self.paneWeight)

        label = Label(
            outerFrame,
            text=_('FlightGear will be started with following arguments:'))
        label.pack(side='top', fill='y', anchor='nw')

        innerFrame = Frame(outerFrame)
        innerFrame.pack(side='bottom', fill='both', expand=True)

        commandWindow_sv = Scrollbar(innerFrame, orient='vertical')
        commandWindow_sh = Scrollbar(innerFrame, orient='horizontal')
        commandWindow = MyText(self.app,
                               innerFrame, wrap='none', height=10,
                               relief='flat', bg=FG_COMMAND_BG_COL,
                               yscrollcommand=commandWindow_sv.set,
                               xscrollcommand=commandWindow_sh.set,
                               state='disabled')
        commandWindow_sv.config(command=commandWindow.yview, takefocus=0)
        commandWindow_sh.config(command=commandWindow.xview, takefocus=0)
        commandWindow_sh.pack(side='bottom', fill='x')
        commandWindow.pack(side='left', fill='both', expand=True)
        commandWindow_sv.pack(side='left', fill='y')

        self.topLevel, self.outerFrame, self.textWidget = \
                                           topLevel, outerFrame, commandWindow
        self.windowDetached = windowDetached

    def update(self, *args):
        self.builder.update()
        if self.visible:
            self.fillTextWidget()

    def fillTextWidget(self):
        """Fill the command window with the last computed fgfs command."""
        self.textWidget.config(state='normal')
        self.textWidget.delete('1.0', 'end')
        if self.builder.argList is not None:
            self.textWidget.insert('end', '\n'.join(self.builder.argList))
        self.textWidget.config(state='disabled')


class LogManager:
    """Class managing storing/retrieving of FG output, log saving...

    Contrary to FGOutput, this class doesn't deal with GUI details.

    """
    def __init__(self, app):
        # Application instance
        self.app = app
        # Used to store fgfs output. Elements are not necessarily lines.
        self.strings = collections.deque()

    def clearLog(self):
        self.strings.clear()

    def addText(self, text):
        self.strings.append(text)

    def getLog(self):
        return ''.join(self.strings)

    def saveLog(self):
        p = fd.asksaveasfilename(initialdir=LOG_DIR,
                                 initialfile=DEFAULT_LOG_NAME)
        if p:
            logger.info("Opening '{}' for writing".format(p))
            with open(p, mode='w', encoding='utf-8') as logfile:
                logfile.write(self.getLog())

    def openLogDir(self):
        if platform.system() == "Windows":
            # The directory was created at application startup.
            os.startfile(LOG_DIR) # this is supposed to return immediately
        elif platform.system() == "Darwin":
            self._openLogDirWithSubprocess("open")
        else:
            self._openLogDirWithSubprocess("xdg-open")

    def _openLogDirWithSubprocess(self, program):
        try:
            process = subprocess.Popen([program, LOG_DIR])
        except OSError as exc:
            msg = _("Unable to start the file manager with '{0}'.").format(
                program)
            detail = _('Problem: {0}').format(exc)
            showerror(_('{prg}').format(prg=PROGNAME), msg, detail=detail)
        else:
            # xdg-open normally doesn't return immediately (cf.
            # <https://unix.stackexchange.com/a/74631>). The thread will wait()
            # for it in order to avoid leaving a zombie.
            threading.Thread(name="FileManager_monitor",
                             target=self._monitorFileManagerProcessThreadFunc,
                             args=(process,),
                             daemon=True).start()

    def _monitorFileManagerProcessThreadFunc(self, process):
        exitStatus = process.wait()
        if exitStatus >= 0:
            complement = _("exit status: {0}").format(exitStatus)
        else:
            complement = _("killed by signal {0}").format(-exitStatus)

        logger.notice(_("File manager process terminated ({0})").format(
            complement))


class FGOutput(DetachableWindowManagerBase):
    """Class for displaying fgfs output, saving it to a file, etc.

    This class is not thread-safe: for a given instance, all of its
    methods must be called from the same thread that created the
    instance (which has to be the GUI thread, since essential methods
    manipulate Tkinter widgets).

    """
    # cf. DetachableWindowManagerBase for a description of the parameters
    def __init__(self, app, showVariable, parent=None, show=True,
                 windowDetached=False, geomVariable=None, paneWeight=150):
        # Manages the logic independently of the GUI. It stores all of
        # the FG output, which is essential when the window is hidden or
        # detached/attached (since the widgets are destroy()ed in these
        # cases).
        self.logManager = LogManager(app)
        title = _("FlightGear Output")
        DetachableWindowManagerBase.__init__(
            self, app, showVariable, parent, title,
            show, windowDetached, geomVariable, paneWeight)

    def createWidgets(self, windowDetached, firstTime=False):
        if windowDetached:
            topLevel = parent = AttachableToplevel(
                self.app, self, self.showVariable, master=self.parent)
            topLevel.title(self.title)
            self.restoreGeometry(window=topLevel, firstTime=firstTime)
        else:
            topLevel = None
            parent = self.parent

        # Elements of outerFrame are defined in reverse order to make sure
        # that bottom buttons are always visible when resizing.
        outerFrame = Frame(parent)
        if windowDetached:
            outerFrame.pack(side='left', fill='both', expand=True)
        else:                   # add the pane to the parent PanedWindow
            self.parent.add(outerFrame, weight=self.paneWeight)

        self.frame1 = Frame(outerFrame)
        self.frame1.pack(side='bottom', fill='y')

        self.saveOutputButton = Button(self.frame1, text=_('Save Log'),
                                       command=self.logManager.saveLog)
        self.saveOutputButton.pack(side='left')

        self.openLogDirButton = Button(self.frame1,
                                       text=_('Open Log Directory'),
                                       command=self.logManager.openLogDir)
        self.openLogDirButton.pack(side='left')

        self.frame2 = Frame(outerFrame)
        self.frame2.pack(side='bottom', fill='both', expand=True)

        outputWindow_sv = Scrollbar(self.frame2, orient='vertical')
        outputWindow_sh = Scrollbar(self.frame2, orient='horizontal')
        outputWindow = MyText(self.app,
                              self.frame2, foreground=FG_OUTPUT_FG_COL,
                              bg=FG_OUTPUT_BG_COL, wrap='none',
                              yscrollcommand=outputWindow_sv.set,
                              xscrollcommand=outputWindow_sh.set,
                              state='disabled')
        outputWindow_sv.config(command=outputWindow.yview, takefocus=0)
        outputWindow_sh.config(command=outputWindow.xview, takefocus=0)
        outputWindow_sh.pack(side='bottom', fill='x')
        outputWindow.pack(side='left', fill='both', expand=True)
        outputWindow_sv.pack(side='left', fill='y')

        self.topLevel, self.outerFrame, self.textWidget = \
                                            topLevel, outerFrame, outputWindow
        self.windowDetached = windowDetached

    def _appendText(self, text="", clear=False):
        self.textWidget.config(state='normal')
        try:
            if clear:
                self.textWidget.delete('1.0', 'end')
            if text:
                self.textWidget.insert('end', text)
        finally:
            self.textWidget.config(state='disabled')

    def clear(self):
        self.logManager.clearLog()
        if self.visible:
            self._appendText(text="", clear=True)

    # The following three methods will be used basically for every line
    # of output from FlightGear. So, we try to keep them optimized (no
    # more locking/unlocking than necessary, etc.), even if they may
    # seem redundant at first with other methods such as append().
    def lock(self):
        if self.visible:
            self.textWidget.config(state='disabled')

    def unlock(self):
        if self.visible:
            self.textWidget.config(state='normal')

    def appendNoUnlock(self, text):
        """Append text to the FlightGear log.

        Contrary to append(), this method doesn't care to put
        self.textWidget into 'normal' state before appending the text
        and into 'disabled' state afterwards. It is up to the caller to
        ensure the widget is in a state that allows writing.

        """
        self.logManager.addText(text)
        if self.visible:
            self.textWidget.insert('end', text)

    def append(self, text):
        self.logManager.addText(text)
        if self.visible:
            self._appendText(text)

    def showEnd(self):
        if self.visible:
            self.textWidget.see('end')

    def fillTextWidget(self):
        """Fill the output window with the log recorded by self.logManager."""
        self._appendText(self.logManager.getLog(), clear=True)
        # It would be nice to be able to restore the previous view position...
        self.showEnd()
