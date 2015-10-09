"""Application main window."""


import os
import sys
import subprocess
import threading
import socket
import re
import abc
import functools
import collections
from gettext import translation
import threading
import queue as queue_mod       # keep 'queue' available for variable bindings
from tkinter import *
import tkinter.filedialog as fd
from tkinter.scrolledtext import ScrolledText
from xml.etree import ElementTree
from tkinter.messagebox import askyesno, showerror
import condconfigparser

from ..logging import logger
from .. import misc
from ..misc import resourceExists, textResourceStream, binaryResourceStream
from . import tooltip
from .tooltip import ToolTip
from .metar import Metar
from .configwindow import ConfigWindow
from . import infowindow
from ..constants import *
from .. import fgdata

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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

        self.LogStartupMessages()

        self.translatedPark = StringVar()
        self.translatedRwy = StringVar()
        self.options = StringVar()
        self.translatedPark.set(_('None'))
        self.translatedRwy.set(_('Default'))
        self.options.set('')
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
        self.toolsmenu.add_command(label='METAR',
                                   command=self.showMETARWindow)
        if self.params.test_mode:
            self.toolsmenu.add_command(label=_('Test stuff'),
                                       accelerator=_('Ctrl-T'),
                                       command=self.testStuff)
        self.menubar.add_cascade(label=_('Tools'), menu=self.toolsmenu)

        self.helpmenu = Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label=_('Help'), command=self.showHelpWindow)
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label=_('About'), command=self.about)
        self.menubar.add_cascade(label=_('Help'), menu=self.helpmenu)

        self.master.config(menu=self.menubar)

        self.frame = Frame(self.master)
        self.frame.pack(side='top', fill='both', expand=True)

        self.frame0 = Frame(self.frame, borderwidth=4)
        self.frame0.pack(side='top', fill='x')
#------ Aircraft list ---------------------------------------------------------
        self.frame1 = Frame(self.frame0, borderwidth=8)
        self.frame1.pack(side='left', fill='both', expand=True)

        self.frame11 = Frame(self.frame1, borderwidth=1)
        self.frame11.pack(side='top', fill='both', expand=True)

        self.scrollbar = Scrollbar(self.frame11, orient='vertical')
        self.aircraftList = Listbox(self.frame11, bg=TEXT_BG_COL,
                                    exportselection=0,
                                    yscrollcommand=self.scrollbar.set,
                                    height=14)
        self.scrollbar.config(command=self.aircraftList.yview, takefocus=0)
        self.aircraftList.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='left', fill='y')
        self.aircraftList.bind('<Button-1>', self.focusAircraftList)

        def aircraftListTooltipFunc(index):
            return self.shownAircrafts[index].dir

        self.aircraftTooltip = tooltip.ListBoxToolTip(self.aircraftList,
                                                      aircraftListTooltipFunc)

        self.frame12 = Frame(self.frame1, borderwidth=1)
        self.frame12.pack(side='top', fill='x')

        self.aircraftSearch = MyEntry(self, self.frame12, bg=TEXT_BG_COL)
        self.aircraftSearch.pack(side='left', fill='x', expand=True)
        self.aircraftSearch.bind('<FocusIn>', self.aircraftSearchStart)
        self.aircraftSearch.bind('<FocusOut>', self.aircraftSearchStop)
        self.aircraftSearchButton = Button(self.frame12, text=_('Clear'),
                                           command=self.aircraftSearchClear)
        self.aircraftSearchButton.pack(side='left')
#------ Middle panel ----------------------------------------------------------
        self.frame2 = Frame(self.frame0, borderwidth=1, relief='sunken')
        self.frame2.pack(side='left', fill='both')
        # Aircraft
        self.frame21 = Frame(self.frame2, borderwidth=4)
        self.frame21.pack(side='top', expand=True)

        self.aircraftLabel = Label(self.frame21,
                                   textvariable=self.config.aircraft)
        self.aircraftLabel.pack(side='top')

        self.thumbnail = Label(self.frame21, width=171, height=128)
        self.thumbnail.pack(side='top', fill='y')
        self.updateImage()
        # Airport, rwy and parking
        self.frame22 = Frame(self.frame2, borderwidth=4)
        self.frame22.pack(side='top', fill='x')
        # First column
        self.frame221 = Frame(self.frame22, borderwidth=4)
        self.frame221.pack(side='left', fill='x')

        self.airport_label = Label(self.frame221, text=_('Airport:'))
        self.airport_label.pack(side='top')

        self.rwy_label = Label(self.frame221, text=_('Rwy:'))
        self.rwy_label.pack(side='top')

        self.park_label = Label(self.frame221, text=_('Parking:'))
        self.park_label.pack(side='top')
        # Second column
        self.frame222 = Frame(self.frame22, borderwidth=4)
        self.frame222.pack(side='left', fill='x')

        self.airportLabel = Label(self.frame222, width=12,
                                  textvariable=self.config.airport,
                                  relief='groove', borderwidth=2)
        self.airportLabel.pack(side='top')
        self.airportLabel.bind('<Button-1>', self.popupCarrier)

        self.rwyLabel = Label(self.frame222, width=12,
                              textvariable=self.translatedRwy,
                              relief='groove', borderwidth=2)
        self.rwyLabel.pack(side='top')
        self.rwyLabel.bind('<Button-1>', self.popupRwy)

        self.parkLabel = Label(self.frame222, width=12,
                               textvariable=self.translatedPark,
                               relief='groove', borderwidth=2)
        self.parkLabel.pack(side='top')
        self.parkLabel.bind('<Button-1>', self.popupPark)
        # AI Scenarios
        self.frame23 = Frame(self.frame2)
        self.frame23.pack(side='top', fill='both')

        self.scenarios = Label(self.frame23, text=_('Select Scenario'),
                               relief='groove', padx=6, pady=6)
        self.scenarios.pack(side='left', fill='both', expand=True)
        self.scenarios.bind('<Button-1>', self.popupScenarios)

#------ Airport list ----------------------------------------------------------
        self.frame3 = Frame(self.frame0, borderwidth=8)
        self.frame3.pack(side='left', fill='both', expand=True)

        self.frame31 = Frame(self.frame3, borderwidth=1)
        self.frame31.pack(side='top', fill='both', expand=True)

        self.sAirports = Scrollbar(self.frame31, orient='vertical')
        self.airportList = Listbox(self.frame31, bg=TEXT_BG_COL,
                                   exportselection=0,
                                   yscrollcommand=self.sAirports.set,
                                   height=14)
        self.sAirports.config(command=self.airportList.yview, takefocus=0)
        self.airportList.pack(side='left', fill='both', expand=True)
        self.sAirports.pack(side='left', fill='y')
        self.airportList.see(self.getIndex('p'))
        self.airportList.bind('<Button-1>', self.focusAirportList)

        self.frame32 = Frame(self.frame3, borderwidth=1)
        self.frame32.pack(side='top', fill='x')

        self.airportSearch = MyEntry(self, self.frame32, bg=TEXT_BG_COL)
        self.airportSearch.pack(side='left', fill='x', expand=True)
        self.airportSearch.bind('<FocusIn>', self.airportSearchStart)
        self.airportSearch.bind('<FocusOut>', self.airportSearchStop)
        self.airportSearchButton = Button(self.frame32, text=_('Clear'),
                                          command=self.airportSearchClear)
        self.airportSearchButton.pack(side='left')
#------ FlightGear process status and buttons ---------------------------------
        self.frame4 = Frame(self.frame, borderwidth=4)
        self.frame4.pack(side='top', fill='x')

        self.frame41 = Frame(self.frame4, borderwidth=4)
        self.frame41.pack(side='right', fill='x')

        # FlightGear process status
        self.fgStatusText = StringVar()
        self.fgStatusText.set(_('Ready'))
        self.fgStatusLabel = Label(self.frame4, textvariable=self.fgStatusText,
                                   background="#88ff88")
        self.fgStatusLabel.pack(side='left', fill='both', expand=True)

        self.frame42 = Frame(self.frame4, borderwidth=4)
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
        self.frame5 = Frame(self.frame)
        self.frame5.pack(side='top', fill='both', expand=True)

        self.frame5top = Frame(self.frame5)
        self.frame5top.pack(side='top', fill='both', expand=True)

        self.frame51 = Frame(self.frame5top)
        self.frame51.pack(side='left', fill='both', expand=True)

        option_window_sv = Scrollbar(self.frame51, orient='vertical')
        option_window_sh = Scrollbar(self.frame51, orient='horizontal')
        self.option_window = MyText(self,
                                    self.frame51, bg=TEXT_BG_COL, wrap='none',
                                    yscrollcommand=option_window_sv.set,
                                    xscrollcommand=option_window_sh.set)
        option_window_sv.config(command=self.option_window.yview, takefocus=0)
        option_window_sh.config(command=self.option_window.xview, takefocus=0)
        self.option_window.bind('<<Modified>>', self.updateOptions)
        option_window_sh.pack(side='bottom', fill='x')
        self.option_window.pack(side='left', fill='both', expand=True)
        option_window_sv.pack(side='left', fill='y')

        self.FGOutput = FGOutput(
            self, self.config.showFGOutput, parent=self.frame5top,
            show=self.config.showFGOutput.get(),
            windowDetached=self.config.showFGOutputInSeparateWindow.get(),
            geomVariable=self.config.FGOutputGeometry)
        self.FGCommand = FGCommand(
            self, self.config.showFGCommand, parent=self.frame,
            show=self.config.showFGCommand.get(),
            windowDetached=self.config.showFGCommandInSeparateWindow.get(),
            geomVariable=self.config.FGCommandGeometry)

#------------------------------------------------------------------------------

        self.default_fg = self.rwyLabel.cget('fg')
        self.default_bg = self.master.cget('bg')
        self.scenarioListOpen = False
        self.mainLoopIsRuning = False
        self.aircraftSearchIsRunning = False
        self.airportSearchIsRunning = False
        self.currentCarrier = []
        self.old_rwy = self.config.rwy.get()
        self.old_park = self.config.park.get()
        self.old_aircraft_search = ''
        self.old_airport_search = ''
        rereadCfgFile = self.proposeConfigChanges()
        # Will set self.FGCommand.{argList,lastConfigParsingExc}
        # appropriately (actually, self.FGCommand.builder.*).
        self.reset(readCfgFile=rereadCfgFile)
        self.registerTracedVariables()
        # Lock used to prevent concurent calls of self._runFG()
        # (disabling the "Run FG" button is not enough, as self.runFG()
        # can be invoked through a keyboard shortcut).
        self.runFGLock = threading.Lock()
        self.setupKeyboardShortcuts()
        self.startLoops()

    def LogStartupMessages(self):
        # Same string as in the About box
        using = _('Using Python {pyVer} and CondConfigParser {ccpVer}').format(
            pyVer=misc.pythonVersionString(),
            ccpVer=condconfigparser.__version__)
        logger.notice(_("{prgWithVer} started\n{using}").format(
            prgWithVer=NAME_WITH_VERSION, using=using))

        # We can't print a translated version of the warning when the import
        # test is done at module initialization; thus, do it now.
        if not HAS_PIL:
            logger.warningNP(
                _("[{prg} warning] {libName} library not found. Aircraft "
                  "thumbnails won't be displayed.").format(prg=PROGNAME,
                                                           libName="Pillow"))
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
Whenever FlightGear's FG_ROOT/Airports/apt.dat.gz file is updated, {prg}
must rebuild its own airport database for proper operation. This can be
done manually with the “Rebuild Airport Database” button from the
Preferences dialog, or automatically whenever {prg} detects a timestamp
change for FlightGear's apt.dat.gz.""")
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
        authors = _('Authors:')
        # Same string as in App.LogStartupMessages()
        using = _('Using Python {pyVer} and CondConfigParser {ccpVer}').format(
            pyVer=misc.pythonVersionString(),
            ccpVer=condconfigparser.__version__)

        # Refresh the version info in case the user fixed his fgfs executable
        # since the last time we tried to run 'fgfs --version'.
        self.config.getFlightGearVersion(ignoreFGVersionError=True)
        if self.config.FG_version is not None:
            FG_version = self.config.FG_version
            comment = ""
        else:
            FG_version =  _('none')
            comment =  '\n' +_(
                "(you may want to check the 'fgfs' executable as defined "
                "in Settings → Preferences)")
        # Uses the same string as in Config.logDetectedFlightGearVersion()
        detected = _('Detected FlightGear version: {ver}').format(
            ver=FG_version) + comment

        about_text = ('{copyright}\n\n{authorsLabel}\n{authors}{transl}\n\n'
                      '{using}.\n\n{detected}.').format(
                          copyright=COPYRIGHT, authorsLabel=authors,
                          authors=AUTHORS, transl=translator, using=using,
                          detected=detected)

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
        self.aboutText = Label(self.aboutFrame1, text=about_text)
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

    def aircraftSearchClear(self):
        self.aircraftSearch.delete('0', 'end')
        self.old_aircraft_search = ''
        self.searchAircrafts()

    def aircraftSearchStart(self, event=None):
        self.aircraftSearchIsRunning = True
        self.aircraftSearchUpdate()

    def aircraftSearchStop(self, event=None):
        self.aircraftSearchIsRunning = False

    def aircraftSearchUpdate(self):
        if self.aircraftSearchIsRunning:
            if self.old_aircraft_search != self.aircraftSearch.get():
                self.searchAircrafts()
            self.old_aircraft_search = self.aircraftSearch.get()
            self.master.after(100, self.aircraftSearchUpdate)
        else:
            self.old_aircraft_search = ''
            return

    def airportSearchClear(self):
        self.airportSearch.delete('0', 'end')
        self.old_airport_search = ''
        self.searchAirports()

    def airportSearchStart(self, event=None):
        self.airportSearchIsRunning = True
        self.airportSearchUpdate()

    def airportSearchStop(self, event=None):
        self.airportSearchIsRunning = False

    def airportSearchUpdate(self):
        if self.airportSearchIsRunning:
            if self.old_airport_search != self.airportSearch.get():
                self.searchAirports()
            self.old_airport_search = self.airportSearch.get()
            self.master.after(100, self.airportSearchUpdate)
        else:
            self.old_airport_search = ''
            return

    def buildAircraftList(self):
        # The current tooltip won't match the aircraft under the mouse pointer
        # after the list is rebuilt.
        self.aircraftTooltip.hide_tooltip()

        if self.aircraftList:
            self.aircraftList.delete(0, 'end')

        self.aircraftList.insert(
                'end', *[ ac.name for ac in self.config.aircraftList ])
        # Cheap, but self.shownAircrafts must not be modified in-place!
        self.shownAircrafts = self.config.aircraftList

    def searchAircrafts(self):
        searchText = self.aircraftSearch.get().lower()
        if searchText:
            self.aircraftList.delete(0, 'end')
            self.shownAircrafts = []

            for aircraft in self.config.aircraftList:
                if searchText in aircraft.name.lower():
                    self.aircraftList.insert('end', aircraft.name)
                    self.shownAircrafts.append(aircraft)
        else:
            self.buildAircraftList()

        # Select the first result, if any
        if self.aircraftList.size():
            self.aircraftList.selection_set(0)

    def buildAirportList(self):
        L = list(zip(self.config.airport_icao, self.config.airport_name))
        if self.airportList:
            self.airportList.delete(0, 'end')

        for i in L:
            if len(i[0]) == 3:
                i = list(i)
                i[1] = ' ' + i[1]
            try:
                i = '   '.join(i)
            except TypeError:
                i = i[0]
            self.airportList.insert('end', i)

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
        if self.mainLoopIsRuning:
            self.master.after(500, self.commentText)
        else:
            return

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
        """Update airportList.

        Apply filter to airportList if self.config.filteredAptList is True.

        """
        message = _("Building airport lists (this may take some time)...")
        infoWindow = infowindow.InfoWindow(self.master, message)
        infoWindow.update()
        self.config.updateAptLists()
        self.buildAirportList()
        infoWindow.destroy()

        self.airportList.see(self.getIndex('p'))
        self.airportList.select_set(self.getIndex('p'))

    def focusAircraftList(self, event=None):
        self.aircraftList.focus_set()

    def focusAirportList(self, event=None):
        self.airportList.focus_set()

    def getAircraft(self):
        """Return the Aircraft instance selected via self.aircraftList."""
        indices = self.aircraftList.curselection()
        if indices:
            return self.shownAircrafts[int(indices[0])]
        else:
            # No aircraft selected. Should only happen when no aircraft is
            # available.
            return None

    def getAirport(self):
        """Get airportList current selection and return airport ICAO."""
        index = self.airportList.curselection()
        if index:
            return self.airportList.get(index).split()[0]
        try:
            return self.airportList.get(ACTIVE).split()[0]
        except IndexError:
            return self.config.airport.get()

    def getImage(self, aircraft):
        """Find thumbnail in aircraft directory."""
        if HAS_PIL and aircraft is not None:
            try:
                path = os.path.join(aircraft.dir, 'thumbnail.jpg')
                image = ImageTk.PhotoImage(Image.open(path))
            except:
                with binaryResourceStream(NO_THUMBNAIL_PIC) as f:
                    image = ImageTk.PhotoImage(Image.open(f))
        else:
            image = PhotoImage(file=NO_PIL_PIC)

        return image

    def getIndex(self, type_):
        """Get aircraft name ('a') or airport ICAO ('p')
        and return its index."""
        if type_ == 'a':
            aircraft = self.config.getCurrentAircraft()

            try:
                return self.shownAircrafts.index(aircraft)
            except ValueError:
                try:
                    dfltAircrafts = self.config.aircraftDict[DEFAULT_AIRCRAFT]
                except KeyError:
                    return 0

                try:
                    dfltAircraft = dfltAircrafts[0]
                except IndexError: # should never happen
                    logger.warning(_(
                        "Empty list for the default aircraft. Please report "
                        "a bug."))
                    return 0

                try:
                    return self.shownAircrafts.index(dfltAircraft)
                except ValueError:
                    return 0

        if type_ == 'p':
            name = self.config.airport.get()
            try:
                return self.config.airport_icao.index(name)
            except ValueError:
                try:
                    return self.config.airport_icao.index(DEFAULT_AIRPORT)
                except ValueError:
                    return 0

    def popupCarrier(self, event):
        """Make pop up menu."""
        # Take focus out of search entry to stop search loop.
        self.master.focus()
        popup = Menu(tearoff=0)
        popup.add_command(label=_('None'), command=self.resetCarrier)
        for i in self.config.carrier_list:
            popup.add_command(label=i[0],
                              command=lambda i=i: self.setCarrier(i))
        popup.tk_popup(event.x_root, event.y_root, 0)

    def _flightTypeDisplayName(self, flightType):
        d = {"cargo":       _("Cargo"),
             "ga":          _("General aviation"),
             "gate":        _("Gate"),
             "mil-cargo":   _("Mil. cargo"),
             "mil-fighter": _("Mil. fighter"),
             "vtol":        _("VTOL"), # Vertical Take-Off and Landing
             "":            _("Unspecified")}

        return d.get(flightType, flightType)

    def popupPark(self, event):
        """Make pop up menu."""
        # Take focus out of search entry to stop search loop.
        self.master.focus()
        popup = Menu(tearoff=0)
        # Background color for column headers
        headerBgColor = "#000066"

        if self.config.airport.get() != 'None':
            popup.add_command(label='', state=DISABLED,
                              background=headerBgColor)
            popup.add_command(label=_('None'),
                              command=lambda: self.config.park.set('None'))

            d = self.readParkingData(self.config.airport.get())

            for flightType in sorted(d.keys()):
                for i, parking in enumerate(d[flightType]):
                    parkName = str(parking)
                    if not (i % 20):
                        # Column header
                        popup.add_command(
                            label=self._flightTypeDisplayName(flightType),
                            state=DISABLED,
                            background=headerBgColor,
                            columnbreak=True)

                    popup.add_command(
                        label=parkName,
                        command=lambda x=parkName: self.config.park.set(x))
        else:
            L = self.currentCarrier[1:-1]
            for i in L:
                popup.add_command(label=i,
                                  command=lambda i=i: self.config.park.set(i))

        popup.tk_popup(event.x_root, event.y_root, 0)

    def popupRwy(self, event):
        """Make pop up menu."""
        # Take focus out of search entry to stop search loop.
        self.master.focus()
        if self.config.airport.get() != 'None':
            popup = Menu(tearoff=0)
            popup.add_command(label=_('Default'),
                              command=lambda: self.config.rwy.set('Default'))
            for i in self.readRunwayData(self.config.airport.get()):
                popup.add_command(label=i, command=lambda i=i:
                                  self.config.rwy.set(i))
            popup.tk_popup(event.x_root, event.y_root, 0)

    def popupScenarios(self, event):
        """Make pop up list."""
        if not self.scenarioListOpen:
            # Take focus out of search entry to stop search loop.
            self.master.focus()
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

    def quit(self):
        """Quit application."""
        self.master.quit()

    def readRunwayData(self, icao):
        res = []
        path = os.path.join(self.config.ai_path, DEFAULT_AIRPORTS_DIR)
        if os.path.isdir(path):
            index = self.getIndex('p')
            rwy = self.config.airport_rwy[index]
            for i in rwy:
                res.append(i)

        return res

    def readParkingData(self, icao):
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
                    res = fgdata.parking.readGroundnetFile(groundnetPath)
                    break
        # If airport data source is set to "Old default"
        else:
            path = os.path.join(self.config.ai_path, DEFAULT_AIRPORTS_DIR)
            if os.path.isdir(path):
                dirs = os.listdir(path)
                if icao in dirs:
                    path = os.path.join(path, icao)
                    file_path = os.path.join(path, 'parking.xml')
                    if os.path.exists(file_path):
                        res = fgdata.parking.readGroundnetFile(file_path)

        return res

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

    def registerTracedVariables(self):
        self.options.trace('w', self.FGCommand.update)
        self.config.aircraft.trace('w', self.FGCommand.update)
        self.config.aircraftDir.trace('w', self.FGCommand.update)
        self.config.airport.trace('w', self.FGCommand.update)
        self.config.scenario.trace('w', self.FGCommand.update)
        self.config.carrier.trace('w', self.FGCommand.update)
        self.config.FG_root.trace('w', self.FGCommand.update)
        self.config.FG_scenery.trace('w', self.FGCommand.update)
        self.config.park.trace('w', self.FGCommand.update)
        self.config.rwy.trace('w', self.FGCommand.update)

    def reset(self, event=None, path=None, readCfgFile=True):
        """Reset data"""
        # Don't call config.update() at application initialization
        # as config object is updated at its creation anyway.
        if readCfgFile:
            self.config.update(path)
        self.aircraftSearch.delete(0, 'end')
        self.airportSearch.delete(0, 'end')
        self._updUpdateInstalledAptListMenuEntryState()
        self.resetLists()
        self.updateImage()
        self.resetText()
        # Update selected carrier
        if self.config.carrier.get() != 'None':

            for i in range(len(self.config.carrier_list)):
                if self.config.carrier.get() == self.config.carrier_list[i][0]:
                    self.currentCarrier = self.config.carrier_list[i]

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
        if self.config.carrier.get() != 'None':
            self.config.park.set('None')
        self.config.carrier.set('None')
        self.airport_label.config(text=_('Airport:'))
        self.airportLabel.config(textvariable=self.config.airport,
                                 bg=self.default_bg)
        self.rwy_label.config(fg=self.default_fg)
        self.rwyLabel.config(fg=self.default_fg)
        self.config.airport.set(self.getAirport())
        self.updateImage()

        try:
            c = self.config.scenario.get().split()
            if self.currentCarrier[-1] in c:
                c.pop(c.index(self.currentCarrier[-1]))
                self.config.scenario.set(' '.join(c))
        except IndexError:
            pass

    def resetLists(self):
        # Take focus out of search entry to stop search loop.
        self.master.focus()
        self.buildAircraftList()
        self.buildAirportList()
        self.aircraftList.select_set(self.getIndex('a'))
        self.airportList.select_set(self.getIndex('p'))
        self.aircraftList.see(self.getIndex('a'))
        self.airportList.see(self.getIndex('p'))

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
            title = _('Sorry!')
            msg = _("FlightGear is already running and we'd rather not run "
                    "two instances simultaneously under the same account.")
            message = '{0}\n\n{1}'.format(title, msg)
            self.error_message = showerror(_('{prg}').format(prg=PROGNAME),
                                           message)

    def _runFG(self, event=None):
        """Run FlightGear.

        Run FlightGear in a child process and start a new thread to
        monitor it (read its stdout and stderr, wait for the process to
        exit). This way, this won't freeze the GUI during the blocking
        calls.

        Return a boolean indicating whether FlightGear could actually be
        started.

        """
        t = self.options.get()
        self.config.write(text=t)

        program = self.config.FG_bin.get()
        FG_working_dir = self.config.FG_working_dir.get()
        if not FG_working_dir:
            FG_working_dir = HOME_DIR

        if self.FGCommand.argList is None:
            message = _('Cannot start FlightGear now.')
            # str(self.lastConfigParsingExc) is not translated...
            detail = _("The configuration in the main text field has an "
                       "invalid syntax:\n\n{errmsg}\n\n"
                       "See docs/README.conditional-config or the "
                       "CondConfigParser Manual for a description of the "
                       "syntax rules.").format(
                           errmsg=self.FGCommand.lastConfigParsingExc)
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

        self.stopLoops()
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

        return True

    def runFGErrorMessage(self, exc):
        title = _('Unable to run FlightGear!')
        msg = _('Please make sure that paths: FG_BIN and FG_ROOT\n'
                'in "Preferences" window are pointing to right directories.')
        message = '{0}\n\n{1}\n\n{2}'.format(title, exc, msg)
        self.error_message = showerror(_('Error'), message)

    def _monitorFgfsProcessThreadFunc(self, process, outputQueue, statusQueue):
        # We are using Tk.event_generate() to notify the main thread. This
        # particular method, when passed 'when="tail"', is supposed to be safe
        # to call from other threads than the Tk GUI thread
        # (cf. <http://stackoverflow.com/questions/7141509/tkinter-wait-for-item-in-queue#comment34432041_14809246>
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
        self.startLoops()
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

    def saveAndQuit(self, event=None):
        """Save options to file (incl. geometry of windows) and quit."""
        self.saveWindowsGeometry()
        t = self.options.get()
        self.config.write(text=t)
        self.master.quit()

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

    def search(self, entry, list_, build_method):
        entry = entry.lower()
        if entry != '':
            build_method()
            L = []

            for i in range(list_.size()):
                if entry in list_.get(i).lower():
                    L.append(list_.get(i))

            list_.delete(0, 'end')
            for i in L:
                list_.insert('end', i)

        else:
            build_method()

    def searchAirports(self):
        entry = self.airportSearch.get()
        list_ = self.airportList
        build_method = self.buildAirportList

        self.search(entry, list_, build_method)

    def setCarrier(self, L):
        old_scenario = ''
        if self.currentCarrier:
            old_scenario = self.currentCarrier[-1]
        if self.config.carrier.get() != L[0]:
            self.config.park.set('None')
        self.config.carrier.set(L[0])
        self.currentCarrier = L
        self.airport_label.config(text=_('Carrier:'))
        self.airportLabel.config(textvariable=self.config.carrier,
                                 bg=CARRIER_COL)
        self.rwy_label.config(fg=GRAYED_OUT_COL)
        self.rwyLabel.config(fg=GRAYED_OUT_COL)
        self.config.rwy.set('Default')
        self.config.airport.set('None')
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
        self.frame.wait_window(self.configWindow.top)
        if self.configWindow.reset_flag:
            self.reset()

    def showHelpWindow(self):
        """Display help window."""
        try:
            self.helpWindow.destroy()
        except AttributeError:
            pass
        # Find currently used language.
        language = self.config.language.get()
        if language:
            lang_code = language
        else:
            lang_code = translation(MESSAGES, LOCALE_DIR).info()['language']

        if not resourceExists(HELP_STEM + lang_code):
            lang_code = 'en'

        with textResourceStream(HELP_STEM + lang_code) as readme:
            text = readme.read()

        self.helpWindow = Toplevel(self.master)
        self.helpWindow.title(_('Help'))
        self.helpWindow.transient(self.master)
        self.helpWindow.bind('<Escape>', self._destroyHelpWindow)

        self.helpText = ScrolledText(self.helpWindow, bg=TEXT_BG_COL, width=80)
        self.helpText.pack(side='left', fill='both', expand=True)
        self.helpText.insert('end', text)
        self.helpText.configure(state='disabled')

    def _destroyHelpWindow(self, event=None):
        self.helpWindow.destroy()

    def showMETARWindow(self, event=None):
        try:
            self.metar.quit()
        except AttributeError:
            pass

        self.metar = Metar(self.master, self.config, MESSAGE_BG_COL)

    def startLoops(self):
        """Activate all loops."""
        self.mainLoopIsRuning = True
        self.commentText()
        self.updateAircraft()
        self.updateAirport()

    def stopLoops(self):
        """Stop all loops."""
        self.mainLoopIsRuning = False

    def updateAircraft(self):
        """Update aircraft selection."""
        now = self.getAircraft()

        if now != self.config.getCurrentAircraft():
            self.config.setCurrentAircraft(now)
            self.updateImage()

        if self.mainLoopIsRuning:
            self.master.after(100, self.updateAircraft)
        else:
            return

    def updateAirport(self):
        """Update airport selection."""
        if self.config.airport.get() != 'None':
            selected_apt = self.getAirport()

            if selected_apt != self.config.airport.get():
                self.config.park.set('None')
                self.config.rwy.set('Default')
                self.config.airport.set(selected_apt)

            # Let user select only one option: rwy or park position.
            if self.config.rwy.get() != 'Default':
                if self.config.rwy.get() != self.old_rwy:
                    self.old_rwy = self.config.rwy.get()
                    self.config.park.set('None')
            if self.config.park.get() != 'None':
                if self.config.park.get() != self.old_park:
                    self.old_park = self.config.park.get()
                    self.config.rwy.set('Default')
            else:
                self.old_park = self.config.park.get()
                self.old_rwy = self.config.rwy.get()

            if self.old_rwy != 'Default' and self.old_park != 'None':
                self.old_rwy = 'Default'

        # Translate rwy and park buttons
        self.translatedPark.set(_(self.config.park.get()))
        self.translatedRwy.set(_(self.config.rwy.get()))

        if self.mainLoopIsRuning:
            self.master.after(250, self.updateAirport)
        else:
            return

    def updateImage(self):
        aircraft = self.config.getCurrentAircraft()
        self.image = self.getImage(aircraft)
        self.thumbnail.config(image=self.image)

    def updateInstalledAptList(self):
        """Rebuild installed airports list."""
        if self.config.filteredAptList.get():
            self.config.makeInstalledAptList()
            self.filterAirports()

    def updateOptions(self, event=None):
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
                 geomVariable):
        """Initialize a DetachableWindowManagerBase instance.

            app       -- application instance
            showVariable
                      -- Tkinter variable linked to the menu checkbutton
                         used to toggle the shown/hidden status of the
                         widgets making up the detachable “window”
            parent    -- parent of the outer Frame among the widgets to be
                         created
            title     -- displayed when the window is detached
            show      -- whether to show the widgets on instance creation
                         (regardless of the detached state)
            windowDetached
                      -- whether the “window” should start in detached state
            geomVariable
                      -- Tkinter variable used to remember the geometry of
                         the window in its detached state

        """
        for name in ("app", "parent", "title", "showVariable", "geomVariable"):
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
    def __init__(self, app, showVariable, parent=None,
                 title="FlightGear Command", show=True,
                 windowDetached=False, geomVariable=None):
        DetachableWindowManagerBase.__init__(
            self, app, showVariable, parent, title,
            show, windowDetached, geomVariable)

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
        outerFrame.pack(side='top', fill='both', expand=True)

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
                               relief='flat', bg=GRAYED_OUT_COL,
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
        program = "xdg-open"
        try:
            process = subprocess.Popen([program, LOG_DIR])
        except OSError as exc:
            msg = _("Unable to start the file manager with '{0}'.").format(
                program)
            detail = _('Problem: {0}').format(exc)
            showerror(_('{prg}').format(prg=PROGNAME), msg, detail=detail)
        else:
            # xdg-open normally doesn't return immediately (cf.
            # <http://unix.stackexchange.com/a/74631>). The thread will wait()
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
    def __init__(self, app, showVariable,
                 parent=None, title="FlightGear Output", show=True,
                 windowDetached=False, geomVariable=None):
        # Manages the logic independently of the GUI. It stores all of
        # the FG output, which is essential when the window is hidden or
        # detached/attached (since the widgets are destroy()ed in these
        # cases).
        self.logManager = LogManager(app)
        DetachableWindowManagerBase.__init__(
            self, app, showVariable, parent, title,
            show, windowDetached, geomVariable)

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
        outerFrame.pack(side='left', fill='both', expand=True)

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
                              self.frame2, foreground=COMMENT_COL,
                              bg=MESSAGE_BG_COL, wrap='none',
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
