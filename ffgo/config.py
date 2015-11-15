"""This module processes data from FFGo's configuration directory."""

import sys
import os
import re
import gzip
import contextlib
import gettext
import traceback
import collections
import itertools
from xml.etree import ElementTree
from tkinter import IntVar, StringVar
from tkinter.messagebox import askyesno, showinfo, showerror
import tkinter.font

from .gui.infowindow import InfoWindow
from . import misc
from .misc import resourceExists, textResourceStream
from .constants import *
from .logging import logger, LogLevel
from .fgdata.aircraft import Aircraft


def setupTranslationHelper(config):
    global pgettext

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext


class AbortConfig(Exception):
    pass


class Config:

    """Read/write and store all data from config files."""

    def __init__(self, master=None):
        self.master = master

        self.ai_path = ''  # Path to FG_ROOT/AI directory.
        self.apt_path = ''  # Path to FG_ROOT/Airports/apt.dat.gz file.
        self.metar_path = ''  # Path to FG_ROOT/Airports/metar.dat.gz file.

        self.aircraft_dirs = [] # List of aircraft directories.
        self.aircraftDict = {}  # Keys: aircraft names; values: Aircraft
                                # instances.
        self.aircraftList = []  # Sorted list of Aircraft instances.

        self.scenario_list = []  # List of selected scenarios.
        # List of all aircraft carriers found in AI scenario folder.
        # Each entry format is:
        # ["ship name", "parking position"... , "scenario name"]
        self.carrier_list = []

        self.settings = []  # List of basic settings read from config file.
        self.text = ''  # String to be shown in command line options window.

        self.aircraft = StringVar()
        self.aircraftDir = StringVar()
        self.airport = StringVar()
        self.alreadyProposedChanges = StringVar()
        self.apt_data_source = IntVar()
        self.auto_update_apt = IntVar()
        self.carrier = StringVar()
        self.FG_aircraft = StringVar()
        self.FG_bin = StringVar()
        self.FG_root = StringVar()
        self.FG_scenery = StringVar()
        self.FG_working_dir = StringVar()

        self.MagneticField_bin = StringVar()
        self.MagneticField_bin.trace('w', self.updateMagFieldProvider)

        self.filteredAptList = IntVar()
        self.language = StringVar()
        self.park = StringVar()
        self.rwy = StringVar()
        self.scenario = StringVar()
        self.mainWindowGeometry = StringVar()
        self.saveWindowPosition = IntVar()
        self.baseFontSize = StringVar()
        self.TkDefaultFontSize = IntVar()

        # tkinter.BooleanVar feels kind of messy. Sometimes, it prints out as
        # 'True', other times as '1'... IntVar seems more predictable.
        self.showFGCommand = IntVar()
        self.showFGCommandInSeparateWindow = IntVar()
        self.FGCommandGeometry = StringVar()
        self.showFGOutput = IntVar()
        self.showFGOutputInSeparateWindow = IntVar()
        self.FGOutputGeometry = StringVar()

        self.keywords = {'--aircraft=': self.aircraft,
                         '--airport=': self.airport,
                         '--fg-root=': self.FG_root,
                         '--fg-scenery=': self.FG_scenery,
                         '--carrier=': self.carrier,
                         '--parkpos=': self.park,
                         '--runway=': self.rwy,
                         'AIRCRAFT_DIR=': self.aircraftDir,
                         'AI_SCENARIOS=': self.scenario,
                         'ALREADY_PROPOSED_CHANGES=':
                                             self.alreadyProposedChanges,
                         'APT_DATA_SOURCE=': self.apt_data_source,
                         'AUTO_UPDATE_APT=': self.auto_update_apt,
                         'FG_BIN=': self.FG_bin,
                         'FG_AIRCRAFT=': self.FG_aircraft,
                         'FG_WORKING_DIR=': self.FG_working_dir,
                         'MAGNETICFIELD_BIN=': self.MagneticField_bin,
                         'FILTER_APT_LIST=': self.filteredAptList,
                         'LANG=': self.language,
                         'WINDOW_GEOMETRY=': self.mainWindowGeometry,
                         'SAVE_WINDOW_POSITION=': self.saveWindowPosition,
                         'BASE_FONT_SIZE=': self.baseFontSize,
                         'SHOW_FG_COMMAND=': self.showFGCommand,
                         'SHOW_FG_COMMAND_IN_SEPARATE_WINDOW=':
                         self.showFGCommandInSeparateWindow,
                         'FG_COMMAND_GEOMETRY=': self.FGCommandGeometry,
                         'SHOW_FG_OUTPUT=': self.showFGOutput,
                         'SHOW_FG_OUTPUT_IN_SEPARATE_WINDOW=':
                         self.showFGOutputInSeparateWindow,
                         'FG_OUTPUT_GEOMETRY=': self.FGOutputGeometry}

        # In order to avoid using a lot of memory, detailed airport data is
        # only loaded on demand. Since this is quite slow, keep a cache of the
        # last retrieved data.
        self.aptDatCache = collections.deque(maxlen=50)

        self._earlyTranslationsSetup()
        self._createUserDirectories()
        self._maybeMigrateFromFGoConfig()
        # Not having the FlightGear version at this point is not important
        # enough to justify pestering the user about it. :-)
        # Defer logging of the detected FG version to fit nicely with
        # the other startup messages.
        self.update(ignoreFGVersionError=True, logFGVersion=False)

        self.setTkDefaultFontSize()
        self.setupFonts(init=True)

    def setTkDefaultFontSize(self):
        """Save unaltered TkDefaultFont size."""
        size = tkinter.font.nametofont("TkDefaultFont").actual()["size"]
        self.TkDefaultFontSize.set(size)

    def setupFonts(self, init=False):
        """Setup the default fonts.

        When called with init=True, custom fonts are created and
        stored as attributes of self. Otherwise, they are simply
        configured.

        """
        # According to <http://www.tcl.tk/man/tcl8.4/TkCmd/font.htm>, font
        # sizes are interpreted this way:
        #   - for positive values, the unit is points;
        #   - for negative values, the unit is pixels;
        #   - 0 is a special value for "a platform-dependent default size".
        #
        # Apparently, Tkinter doesn't accept floats for the 'size' parameter of
        # <font>.configure(), even when positive (tested with Python 2.7.3).
        baseSize = int(float(self.baseFontSize.get()))
        # Get the actual size when baseSize == 0, otherwise scaling won't work
        # since 0*factor == 0, regardless of the (finite) factor.
        if baseSize == 0:
            baseSize = self.TkDefaultFontSize.get()

        def scale(factor):
            return int(round(baseSize * factor))

        def configFontSize(style, factor):
            font = tkinter.font.nametofont("Tk%sFont" % style)
            font.configure(size=scale(factor))

        # Configure built-in fonts
        for style in ("Default", "Text", "Fixed", "Caption", "Tooltip"):
            configFontSize(style, 1)

        for style, factor in (("Menu", 20 / 18.), ("Heading", 20 / 18.),
                              ("SmallCaption", 16 / 18.), ("Icon", 14 / 18.)):
            configFontSize(style, factor)

        # Create or configure custom fonts, depending on 'init'
        aboutTitleFontSize = scale(42 / 18.)
        if init:
            self.aboutTitleFont = tkinter.font.Font(
                family="Helvetica", weight="bold", size=aboutTitleFontSize)
        else:
            self.aboutTitleFont.configure(size=aboutTitleFontSize)

    def makeInstalledAptList(self):
        logger.notice(_("Building the list of installed airports "
                        "(this may take some time)..."))
        # writelines() used below doesn't automatically add line terminators
        airports = [ icao + '\n' for icao in self._findInstalledApt() ]
        logger.info("Opening '{}' for writing".format(INSTALLED_APT))
        with open(INSTALLED_APT, "w", encoding="utf-8") as fout:
            fout.writelines(airports)

    def readMetarDat(self):
        """Fetch METAR station list from metar.dat.gz file"""
        logger.info("Opening '{}' for reading".format(self.metar_path))
        res = []

        with gzip.open(self.metar_path, mode='rt', encoding='utf-8') as fin:
            for line in fin:
                if not line.startswith('#'):
                    res.append(line.strip())

        return res

    def rebuildApt(self):
        """Rebuild apt file."""
        self._makeAptDigest()

    def _computeAircraftDirList(self):
        FG_AIRCRAFT_env = os.getenv("FG_AIRCRAFT", "")
        if FG_AIRCRAFT_env:
            FG_AIRCRAFT_envList = FG_AIRCRAFT_env.split(os.pathsep)
        else:
            FG_AIRCRAFT_envList = []

        # FG_ROOT/Aircraft
        defaultAircraftDir = os.path.join(self.FG_root.get(),
                                          DEFAULT_AIRCRAFT_DIR)

        aircraft_dirs = (self.FG_aircraft.get().split(os.pathsep)
                         + FG_AIRCRAFT_envList + [defaultAircraftDir])
        return aircraft_dirs

    def logDetectedFlightGearVersion(self, logLevel=LogLevel.notice,
                                     prefix=True):
        if self.FG_version is not None:
            FG_version = str(self.FG_version)
        else:
            FG_version = pgettext("FlightGear version", "none")

        # Uses the same string as in App.about()
        message = _("Detected FlightGear version: {ver}").format(
            ver=FG_version)
        logger.log(logLevel, prefix, message)

    def getFlightGearVersion(self, ignoreFGVersionError=False, log=False):
        # This import requires the translation system [_() function] to be in
        # place.
        from .fgdata import fgversion

        self.FG_version = None  # in case an exception is raised below
        FG_bin = self.FG_bin.get()
        exc = None

        if FG_bin:
            try:
                self.FG_version = fgversion.getFlightGearVersion(FG_bin)
            except fgversion.error as e:
                exc = e         # may need to be raised later

        if log:
            self.logDetectedFlightGearVersion()

        if exc is not None and not ignoreFGVersionError:
            raise exc

    def getCurrentAircraft(self):
        return self.currentAircraft

    def setCurrentAircraft(self, ac):
        self.currentAircraft = ac
        if ac is not None:
            self.aircraft.set(self.currentAircraft.name)
            self.aircraftDir.set(self.currentAircraft.dir)
        else:
            self.aircraft.set(DEFAULT_AIRCRAFT)
            self.aircraftDir.set('')

    def sanityChecks(self):
        status, *rest = self.decodeParkingSetting(self.park.get())
        if status == "invalid":
            logger.warning(
                _("Invalid syntax for the parking setting ({setting!r}), "
                  "resetting it.").format(setting=self.park.get()))
            self.park.set('')

        if self.rwy.get() and self.park.get():
            # Impossible to at the same time set a non-default runway and a
            # parking position. The latter wins. :-)
            self.rwy.set('')

    def update(self, path=None, ignoreFGVersionError=False, logFGVersion=True):
        """Read config file and update variables.

        path is a path to different than default config file

        """
        del self.settings
        del self.text
        del self.aircraft_dirs
        del self.apt_path
        del self.ai_path
        del self.metar_path
        del self.aircraftDict
        del self.aircraftList
        del self.scenario_list
        del self.carrier_list

        self.setCurrentAircraft(None) # sets self.aircraft and self.aircraftDir
        self.airport.set(DEFAULT_AIRPORT)
        self.alreadyProposedChanges.set('')
        self.apt_data_source.set(1)
        self.auto_update_apt.set(1)
        self.carrier.set('')
        self.FG_aircraft.set('')
        self.FG_bin.set('')
        self.FG_root.set('')
        self.FG_scenery.set('')
        self.FG_working_dir.set('')
        self.MagneticField_bin.set('')
        self.language.set('')
        self.baseFontSize.set(DEFAULT_BASE_FONT_SIZE)
        self.mainWindowGeometry.set('')
        self.saveWindowPosition.set('1')
        self.showFGCommand.set('1')
        self.showFGCommandInSeparateWindow.set('0')
        self.FGCommandGeometry.set('')
        self.showFGOutput.set('1')
        self.showFGOutputInSeparateWindow.set('0')
        self.FGOutputGeometry.set('')
        self.park.set('')
        self.rwy.set('')
        self.scenario.set('')
        self.filteredAptList.set(0)

        self.settings, self.text = self._read(path)

        for line in self.settings:
            cut = line.find('=') + 1

            if cut:
                name = line[:cut]
                value = line[cut:]

                if value:
                    if name in self.keywords:
                        var = self.keywords[name]
                        var.set(value)

        self._setLanguage(self.language.get())
        setupTranslationHelper(self)

        self.aircraft_dirs = self._computeAircraftDirList()
        self.apt_path = os.path.join(self.FG_root.get(), APT_DAT)
        self.ai_path = os.path.join(self.FG_root.get(), AI_DIR)
        self.metar_path = os.path.join(self.FG_root.get(), METAR_DAT)

        self.aircraftDict, self.aircraftList = self._readAircraft()
        self.setCurrentAircraft(self._findAircraft(self.aircraft.get()))

        self.scenario_list, self.carrier_list = self._readScenarios()
        self.sanityChecks()
        self.getFlightGearVersion(ignoreFGVersionError=ignoreFGVersionError,
                                  log=logFGVersion)

    def write(self, text=None, path=None):
        """Write the configuration to a file.

        text -- content of text window processed by CondConfigParser
                (pass None to use the value of Config.text)
        path -- path to the file the config will be written to
                (the default config file is used if this argument is
                empty or None)

        """
        if not path:
            path = CONFIG
        if text is None:
            text = self.text

        options = []
        keys = list(self.keywords.keys())
        keys.sort()

        for k in keys:
            v = self.keywords[k]
            if k in ('--carrier=', '--airport=', '--parkpos=', '--runway='):
                if v.get():
                    options.append(k + v.get())
            else:
                options.append(k + str(v.get()))

        s = '\n'.join(options)
        logger.info("Opening config file for writing: '{}'".format(path))

        with open(path, mode='w', encoding='utf-8') as config_out:
            config_out.write(s + '\n' + CUT_LINE + '\n')
            # Make sure the config file has exactly one newline at the end
            while text.endswith('\n\n'):
                text = text[:-1]
            if not text.endswith('\n'):
                text += '\n'
            config_out.write(text)

    def _findInstalledApt(self):
        """Walk thru all scenery and find installed airports.

        Take geographic coordinates from directories names and compare them
        with airports coordinates in apt file.

        The result is a sorted list of ICAO codes for matching airports.

        """
        coord_dict = {}
        sceneries = self.FG_scenery.get().split(os.pathsep)

        for scenery in sceneries:
            path = os.path.join(scenery, 'Terrain')
            if os.path.exists(path):
                for dir in os.listdir(path):
                    p = os.path.join(path, dir)
                    for coords in os.listdir(p):
                        d = os.path.join(p, coords)
                        if not os.path.isdir(d):
                            continue

                        logger.debug("Exploring Terrain directory '{}' -> '{}'"
                                     .format(p, coords))
                        converted = self._stringToCoordinates(coords)
                        if converted is not None:
                            coord_dict[converted] = None
                        else:
                            logger.notice(
                                _("Ignoring directory '{}' (unexpected name)")
                                .format(d))

        coords = coord_dict.keys()
        res = []
        for icao in self.sortedIcao():
            airport = self.airports[icao]
            for c in coords:
                if (c[0][0] < airport.lat < c[0][1] and
                    c[1][0] < airport.lon < c[1][1]):
                    res.append(icao)

        return res

    def _calculateRange(self, coordinates):
        c = coordinates
        if c.startswith('s') or c.startswith('w'):
            c = int(c[1:]) * (-1)
            return c, c + 1
        else:
            c = int(c[1:])
            return c, c + 1

    def _createUserDirectories(self):
        """Create config and log directories if they don't exist."""
        for d in USER_DATA_DIR, LOG_DIR:
            os.makedirs(d, exist_ok=True)

    def _maybeMigrateFromFGoConfig_dialogs(self, parent):
        message = _("Initialize {prg}'s configuration from your existing " \
                    "FGo! configuration?").format(prg=PROGNAME)
        detail = (_("""\
You have no {cfgfile} file but you do have a {fgo_cfgfile} file,
which normally belongs to FGo!. Except in rare circumstances
(such as using braces or backslashes, or opening brackets at the
beginning of a config line), a configuration file from
FGo! 1.5.5 or earlier should be usable as is by {prg}.""")
                  .replace('\n', ' ') + "\n\n" + _("""\
If {fgo_cfgfile} was written by FGo! 1.5.5 or earlier, you
should probably say “Yes” here in order to initialize {prg}'s
configuration based on your FGo! config file (precisely:
copy {fgo_cfgfile} to {cfgfile}).""")
                  .replace('\n', ' ') + "\n\n" + _("""\
If {fgo_cfgfile} was written by a version of FGo! that is greater
than 1.5.5, it is advised to say “No” here.""")
                  .replace('\n', ' ')
                 ).format(prg=PROGNAME, cfgfile=CONFIG, fgo_cfgfile=FGO_CONFIG)

        if askyesno(PROGNAME, message, detail=detail, parent=parent):
            choice = "migrate from FGo!"
        else:
            message = _("Create a default {prg} configuration?").format(
                prg=PROGNAME)
            detail = _("""\
Choose “Yes” to create a basic {prg} configuration now. If you
choose “No”, {prg} will exit and you'll have to create {cfgfile}
yourself, or restart {prg} to see the same questions again.""") \
                     .replace('\n', ' ').format(prg=PROGNAME, cfgfile=CONFIG)

            if askyesno(PROGNAME, message, detail=detail, parent=parent):
                choice = "create default cfg"
                message = _("Creating a default {prg} configuration.").format(
                    prg=PROGNAME)
                detail = (_("""\
It is suggested that you go to the Settings menu and choose
Preferences to review your newly-created configuration.""")
                          .replace('\n', ' ') + "\n\n" + _("""\
You can also reuse most, if not all FlightGear options you
had in FGo!'s main text box (the “options window”). Just copy
them to the corresponding {prg} text box.""")
                          .replace('\n', ' ') + "\n\n" + _("""\
Note: you may run both FGo! and {prg} simultaneously, as their
configurations are kept separate.""")
                          .replace('\n', ' ')
                         ).format(prg=PROGNAME)
                showinfo(PROGNAME, message, detail=detail, parent=parent)
            else:
                choice = "abort"

        return choice

    def _maybeMigrateFromFGoConfig(self):
        if os.path.isfile(FGO_CONFIG) and not os.path.isfile(CONFIG):
            baseSize = tkinter.font.nametofont("TkDefaultFont").actual()["size"]
            def configFontSize(val, absolute=False):
                for style in ("Default", "Text", "Fixed", "Caption", "Tooltip"):
                    font = tkinter.font.nametofont("Tk{}Font".format(style))
                    if absolute:
                        font.configure(size=val)
                    else:
                        font.configure(size=int(round(baseSize * val)))

            # Make sure most people can read the following dialogs (the
            # standard Tk size may be rather small): 140% increase
            configFontSize(1.4, absolute=False)

            choice = None       # user choice in the to-be-displayed dialogs
            # It seems we need an otherwise useless Toplevel window in order to
            # center the Tk standard dialogs...
            t = tkinter.Toplevel()
            try:
                # Transparent if the OS supports it
                t.attributes('-alpha', '0.0')
                # Center the Toplevel. To be effective, this would probably
                # need a visit to the Tk event loop, however it is enough to
                # have the child dialogs centered, which is what matters here.
                self.master.eval('tk::PlaceWindow {} center'.format(
                    t.winfo_pathname(t.winfo_id())))
                choice = self._maybeMigrateFromFGoConfig_dialogs(t)
            finally:
                t.destroy()

            # Restore font size for later self.setupFonts() call
            configFontSize(baseSize, absolute=True)

            if choice in (None, "abort"):
                raise AbortConfig
            elif choice == "migrate from FGo!":
                # shutil.copy() and shutil.copy2() attempt to preserve the file's
                # permission mode, which is undesirable here → manual copy.
                with open(FGO_CONFIG, "r", encoding='utf-8') as fgoConfig, \
                     open(CONFIG, "w", encoding='utf-8') as config:
                    config.write(fgoConfig.read())
            else:
                assert choice == "create default cfg", repr(choice)

    def _makeAptDigest(self, head=None):
        """Build apt database from apt.dat.gz"""
        if self.FG_root.get():
            _ProcessApt(self.master, self.apt_path, head)

    def _read(self, path=None):
        """Read the specified or a default configuration file.

        - If 'path' is None and CONFIG exists, load CONFIG;
        - if 'path' is None and CONFIG does not exist, load the
          configuration from the presets and default, localized
          config_ll resource;
        - otherwise, load configuration from the specified file.

        """
        try:
            # ExitStack not strictly necessary here, but allows clean and
            # convenient handling of the various files or resources the
            # configuration may be loaded from.
            with contextlib.ExitStack() as stack:
                res = self._read0(stack, path)
        except OSError as e:
            message = _('Error loading configuration')
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=str(e))
            res = ([''], '')

        return res

    _presetsBlankLineOrCommentCre = re.compile(r"^[ \t]*(#|$)")

    def _read0(self, stack, path):
        # Data before the CUT_LINE in the config file, destined to
        # self.settings
        settings = []
        # Data after the CUT_LINE in the config file, destined to
        # self.text and to be parsed by CondConfigParser
        condConfLines = []

        if path is not None or (path is None and os.path.exists(CONFIG)):
            if path is None:
                path = CONFIG
            logger.info("Opening config file '{}' for reading".format(path))
            configStream = stack.enter_context(open(path, "r",
                                                    encoding="utf-8"))
            beforeCutLine = True
        else:                 # Use default config if no regular config exists.
            # Load presets if exists.
            if resourceExists(PRESETS):
                with textResourceStream(PRESETS) as presets:
                    for line in presets:
                        line = line.strip()
                        if not self._presetsBlankLineOrCommentCre.match(line):
                            settings.append(line)

            # Find the currently used language according to the environment.
            try:
                lang_code = gettext.translation(
                    MESSAGES, LOCALE_DIR).info()['language']
            except OSError:
                lang_code = 'en'

            if not resourceExists(DEFAULT_CONFIG_STEM + lang_code):
                lang_code = 'en'
            resPath = DEFAULT_CONFIG_STEM + lang_code

            configStream = stack.enter_context(textResourceStream(resPath))
            # There is no "cut line" in the template config files.
            beforeCutLine = False

        for line in configStream:
            if beforeCutLine:
                line = line.strip()

            if line != CUT_LINE:
                if beforeCutLine:
                    # Comments wouldn't be preserved on saving, therefore don't
                    # try to handle them before the "cut line".
                    if line:
                        settings.append(line)
                else:
                    condConfLines.append(line)
            else:
                beforeCutLine = False

        return (settings, ''.join(condConfLines))

    def _readAircraft(self):
        """
        Walk through Aircraft directories and return the available aircrafts.

        Return a tuple (aircraftDict, aircraftList) listing all
        aircrafts found via self.aircraft_dirs.

        aircraftDict is a dictionary whose keys are the names (derived
        from the -set.xml files) of all aircrafts. For each aircraft
        name 'n', aircraftDict[n] is the list, in self.aircraft_dirs
        priority order, of all Aircraft instances with that name.

        aircraftList is the sorted list of all Aircraft instances,
        suitable for quick building of the aircraft list in the GUI.

        """
        aircraftDict = {}
        for dir_ in self.aircraft_dirs:
            if os.path.isdir(dir_):
                for d in os.listdir(dir_):
                    self._readAircraftData(dir_, d, aircraftDict)

        aircraftList = []
        # First sort by lowercased aircraft name
        sortFunc = lambda s: (s.lower(), s)
        for acName in sorted(aircraftDict.keys(), key=sortFunc):
            # Then sort by position in self.aircraft_dirs
            aircraftList.extend(aircraftDict[acName])

        return (aircraftDict, aircraftList)

    def _readAircraftData(self, dir_, d, aircraftDict):
        path = os.path.join(dir_, d)
        if os.path.isdir(path):
            for f in os.listdir(path):
                self._appendAircraft(f, aircraftDict, path)

    def _appendAircraft(self, f, aircraftDict, path):
        if f.endswith('-set.xml'):
            # Dirty and ugly hack to prevent carrier-set.xml in
            # seahawk directory to be attached to the aircraft
            # list.
            if (not path.startswith('seahawk') and
                    f != 'carrier-set.xml'):
                name = f[:-8]
                if name not in aircraftDict:
                    aircraftDict[name] = []

                aircraft = Aircraft(name, path)
                aircraftDict[name].append(aircraft)

    def _findAircraft(self, acName):
        if acName in self.aircraftDict:
            for ac in self.aircraftDict[acName]:
                if ac.dir == self.aircraftDir.get():
                    aircraft = ac
                    break
            else:
                aircraft = self.aircraftDict[acName][0]
                logger.notice(
                    _("Could not find aircraft '{aircraft}' under '{dir}', "
                      "taking it from '{fallback}' instead").format(
                          aircraft=acName, dir=self.aircraftDir.get(),
                          fallback=aircraft.dir))
        else:
            try:
                defaultAircrafts = self.aircraftDict[DEFAULT_AIRCRAFT]
            except KeyError:
                aircraft = None
                logger.warning(
                    _("Could not find the default aircraft: {aircraft}")
                    .format(aircraft=DEFAULT_AIRCRAFT))
            else:
                aircraft = defaultAircrafts[0]
                logger.notice(
                    _("Could not find aircraft '{aircraft}', using "
                      "'{fallback}' from '{dir}' instead").format(
                          aircraft=acName, fallback=aircraft.name,
                          dir=aircraft.dir))

        return aircraft

    def sortedIcao(self):
        return sorted(self.airports.keys())

    def _readApt(self):
        """Read the apt digest file (create a new one if none exists).

        Return a list of AirportStub instances.

        """
        from .fgdata import apt_dat

        if not os.path.exists(APT):
            # Create a new file if self.FG_root is non-empty
            self._makeAptDigest()

        if not os.path.isfile(APT): # may happen if self.FG_root was empty
            return []

        for attempt in itertools.count(start=1):
            try:
                self.aptDatSize, self.airports = apt_dat.AptDatDigest.read(APT)
            except apt_dat.UnableToParseAptDigest:
                if attempt < 2:
                    self._makeAptDigest()
                else:
                    raise
            else:
                break

        if self.filteredAptList.get():
            installedApt = self._readInstalledAptSet()
            res = [ self.airports[icao] for icao in self.sortedIcao()
                    if icao in installedApt ]
        else:
            res = [ self.airports[icao] for icao in self.sortedIcao() ]

        return res

    def _readInstalledAptSet(self):
        """Read the set of locally installed airports from INSTALLED_APT.

        Create a new INSTALLED_APT file if none exists yet.
        Return a frozenset(), which offers very fast membership test
        compared to a list.

        """
        if not os.path.exists(INSTALLED_APT):
            self.makeInstalledAptList()

        logger.info("Opening installed apt file '{}' for reading".format(
            INSTALLED_APT))

        with open(INSTALLED_APT, "r", encoding="utf-8") as f:
            # Strip the newline char ending every line
            res = frozenset([ line[:-1] for line in f ])

        return res

    def _readScenarios(self):
        """Walk through AI scenarios and read carrier data.

        Return two lists:
            scenarios: [scenario name, ...]
            carrier data: [[name, parkking pos, ..., scenario name], ...]
        Return two empty lists if no scenario is found.
        """
        carriers = []
        scenarios = []
        if os.path.isdir(self.ai_path):
            for f in os.listdir(self.ai_path):
                path = os.path.join(self.ai_path, f)

                if os.path.isfile(path) and f.lower().endswith('.xml'):
                    scenario_name = f[:-4]
                    scenarios.append(scenario_name)
                    # Appends to 'carriers'
                    self._append_carrier_data(carriers, path, scenario_name)

        return sorted(scenarios), sorted(carriers)

    def _append_carrier_data(self, carriers, xmlFilePath, scenario_name):
        logger.info("Reading scenario data from '{}'".format(xmlFilePath))
        root = self._get_root(xmlFilePath)
        scenario = root.find('scenario')

        if scenario is not None:
            for e in scenario.iterfind('entry'):
                typeElt = e.find('type')
                if typeElt is not None and typeElt.text == 'carrier':
                    data = self._get_carrier_data(e, scenario_name)
                    carriers.append(data)

    def _get_root(self, xmlFilePath):
        tree = ElementTree.parse(xmlFilePath)
        return tree.getroot()

    def _get_carrier_data(self, e, scenario_name):
        nameElt = e.find('name')
        if nameElt is not None:
            data = [nameElt.text]
        else:
            data = ['unnamed']

        for child in e.iterfind('parking-pos'):
            parkingNameElt = child.find('name')
            if parkingNameElt is not None:
                data.append(parkingNameElt.text)

        data.append(scenario_name)
        return data

    # The '1' is the version number of this custom format for the contents of
    # Config.park, in case we need to change it.
    aptDatParkConfStart_cre = re.compile(r"::apt\.dat::1::(?P<nameLen>\d+),")
    aptDatParkConfEnd_cre = re.compile(
        r"""lat=(?P<lat>{floatRegexp}),
            lon=(?P<lon>{floatRegexp}),
            heading=(?P<heading>{floatRegexp})$""".format(
            floatRegexp=r"-?\d+(\.\d*)?"),
        re.VERBOSE)

    def decodeParkingSetting(self, parkConf):
        status = "invalid"      # will be overridden if correct in the end
        parkName = None
        options = []

        if not parkConf:
            status = "none"     # no parking position
        else:
            mo = self.aptDatParkConfStart_cre.match(parkConf)
            if mo:
                # Length of the following parking name (after the comma)
                nameLen = int(mo.group("nameLen"))
                i = mo.end("nameLen") + 1 + nameLen

                if len(parkConf) > i and parkConf[i] == ";":
                    mo2 = self.aptDatParkConfEnd_cre.match(parkConf[i+1:])
                    if mo2:
                        parkName = parkConf[mo.end("nameLen")+1:i]
                        options = ["--lat=" + mo2.group("lat"),
                                   "--lon=" + mo2.group("lon"),
                                   "--heading=" + mo2.group("heading")]
                        status = "apt.dat"
            else:                   # plain parking name
                parkName = parkConf
                options = ["--parkpos=" + parkName]
                status = "groundnet"

        return (status, parkName, options)

    def _earlyTranslationsSetup(self):
        """Setup translations before the config file has been read.

        The language is determined from the environment (LANGUAGE,
        LC_ALL, LC_MESSAGES, and LANG—cf. gettext.translation() and
        gettext.find()).

        """
        try:
            langCode = gettext.translation(
                MESSAGES, LOCALE_DIR).info()['language']
        except OSError:
            langCode = 'en'

        self._setLanguage(langCode)

    def _setLanguage(self, lang):
        # Initialize provided language...
        try:
            L = gettext.translation(MESSAGES, LOCALE_DIR, languages=[lang])
            L.install()
        # ...or fallback to system default.
        except Exception:
            gettext.install(MESSAGES, LOCALE_DIR)

    # Regexp for directory names such as w040n20
    _geoDirCre = re.compile(r"[we]\d{3}[ns]\d{2}$")

    def _stringToCoordinates(self, coordinates):
        """Convert geo coordinates to decimal format."""
        if not self._geoDirCre.match(coordinates):
            return None

        lat = coordinates[4:]
        lon = coordinates[:4]

        lat_range = self._calculateRange(lat)
        lon_range = self._calculateRange(lon)
        return lat_range, lon_range

    def _autoUpdateApt(self):
        if not self.auto_update_apt.get() or not os.path.exists(self.apt_path):
            return
        old_timestamp = self._readAptTimestamp()
        self._updateApt(old_timestamp)

    def _readAptTimestamp(self):
        if not os.path.exists(APT_TIMESTAMP):
            self._writeAptTimestamp('')

        logger.info("Opening apt timestamp file '{}' for reading".format(
            APT_TIMESTAMP))
        with open(APT_TIMESTAMP, "r", encoding="utf-8") as timestamp:
            old_modtime = timestamp.read()
        return old_modtime

    def _writeAptTimestamp(self, s):
        logger.info("Opening apt timestamp file '{}' for writing".format(
            APT_TIMESTAMP))
        with open(APT_TIMESTAMP, "w", encoding="utf-8") as timestamp:
            timestamp.write(s)

    def _getAptModTime(self):
        return str(os.path.getmtime(self.apt_path))

    def _updateApt(self, old_timestamp):
        if old_timestamp != self._getAptModTime():
            self._makeAptDigest(head=_('Modification of apt.dat.gz detected.'))
            # XXX What follows would probably be better in _ProcessApt
            self._writeAptTimestamp(self._getAptModTime())
            # The new apt.dat may invalidate the current parking
            status, *rest = self.decodeParkingSetting(self.park.get())
            if status == "apt.dat":
                # This was a parking position obtained from apt.dat; it may be
                # invalid with the new file, reset.
                self.park.set('')

            # This is also outdated with respect to the new apt.dat.
            self.aptDatCache.clear()

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def updateMagFieldProvider(self, *args):
        from .geo.magfield import EarthMagneticField, MagVarUnavailable
        try:
            self.earthMagneticField = EarthMagneticField(self)
        except MagVarUnavailable as e:
            self.earthMagneticField = None
            self.earthMagneticFieldLastProblem = e.message


class _ProcessApt:

    """Build apt database from apt.dat.gz"""

    def __init__(self, master, aptPath, head=None):
        self.master = master
        self.aptPath = aptPath
        self.main(head)

    def main(self, head):
        if os.path.exists(self.aptPath):
            self.make_window(head)
            try:
                self.makeAptDigest()
            except Exception:
                self.close_window()
                # Will be handled by master.report_callback_exception
                raise
            self.close_window()
        else:
            self.show_no_aptdat_error()

    def make_window(self, head=None):
        message = _('Generating the airport database,\n'
                    'this may take a while...')
        if head:
            message = '\n'.join((head, message))
        self.window = InfoWindow(self.master, text=message)

    def makeAptDigest(self):
        from .fgdata import apt_dat

        with apt_dat.AptDat(self.aptPath) as aptDat:
            logger.notice(
                _("Generating {prg}'s apt digest file ('{aptDigest}') from "
                  "'{aptDat}'...").format(prg=PROGNAME, aptDigest=APT,
                                          aptDat=self.aptPath))
            aptDat.makeAptDigest(outputFile=APT)

    def show_no_aptdat_error(self):
        message = _('Cannot find apt.dat database.')
        showerror(_('Error'), message)

    def close_window(self):
        self.window.destroy()
