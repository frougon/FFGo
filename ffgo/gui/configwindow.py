"""Display preferences window."""


import os
import platform
import sys
import tkinter as tk
import tkinter.filedialog as fd
from tkinter.messagebox import showinfo, showerror
from tkinter import ttk

from .. import misc
from .tooltip import ToolTip
from ..constants import *


def setupTranslationHelper(config):
    global pgettext

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext


class ValidatingWidget:
    """Class holding widget-metadata to ease input validation.

    This class allows a number of widgets to have their input validated
    using the same code, with error reporting when the input is invalid.

    """
    def __init__(self, widget, paneWidget, validateFunc, invalidFunc):
        for attr in ("widget", "paneWidget", "validateFunc", "invalidFunc"):
            setattr(self, attr, locals()[attr])


class ConfigWindow:

    def __init__(self, master, config, text):
        self.master = master
        self.config = config
        self.text = text

        setupTranslationHelper(config)

        # List of ValidatingWidget instances for “standard” input validation.
        self.validatingWidgets = []

        self.apt_data_source = tk.StringVar()
        self.auto_update_apt = tk.StringVar()
        self.FG_bin = tk.StringVar()
        self.FG_root = tk.StringVar()
        self.FG_scenery = tk.StringVar()
        self.FG_aircraft = tk.StringVar()
        self.FG_download_dir = tk.StringVar()
        self.FG_working_dir = tk.StringVar()
        self.MagneticField_bin = tk.StringVar()
        self.language = tk.StringVar()
        self.baseFontSize = tk.StringVar()
        self.rememberMainWinPos = tk.IntVar()
        self.autoscrollFGOutput = tk.IntVar()
        self.fakeParkposOption = tk.IntVar()

        if self.config.apt_data_source.get():
            self.apt_data_source.set(_('Scenery'))
        else:
            self.apt_data_source.set(_('Old default'))

        if self.config.auto_update_apt.get():
            self.auto_update_apt.set(_('Automatic'))
        else:
            self.auto_update_apt.set(_('Manual'))
        self.FG_bin.set(self.config.FG_bin.get())
        self.FG_root.set(self.config.FG_root.get())
        self.FG_scenery.set(self.config.FG_scenery.get())
        self.FG_aircraft.set(self.config.FG_aircraft.get())
        self.FG_download_dir.set(self.config.FG_download_dir.get())
        self.FG_working_dir.set(self.config.FG_working_dir.get())
        self.MagneticField_bin.set(self.config.MagneticField_bin.get())
        if self.config.language.get():
            self.language.set(self.config.language.get())
        else:
            self.language.set('-')
        self.baseFontSize.set(self.config.baseFontSize.get())
        self.rememberMainWinPos.set(self.config.saveWindowPosition.get())
        self.autoscrollFGOutput.set(self.config.autoscrollFGOutput.get())
        self.fakeParkposOption.set(self.config.fakeParkposOption.get())

        for name in ("aircraftStatsShowPeriod", "aircraftStatsExpiryPeriod",
                     "airportStatsShowPeriod", "airportStatsExpiryPeriod"):
            setattr(self, name, tk.IntVar())
            tkVar = getattr(self, name)
            tkVar.set(getattr(self.config, name).get())

        self.reset_flag = False
        self.initToolTipMessages()

# -----------------------------------------------------------------------------

        self.top = tk.Toplevel(self.master)
        self.top.grid_rowconfigure(0, weight=100)
        self.top.grid_columnconfigure(0, weight=100)
        self.top.grab_set()  # Focus input on that window.
        self.top.title(_('Preferences'))
        self.top.transient(self.master)

        self.main = ttk.Frame(self.top, padding=("12p", "12p", "12p", 0))
        self.main.grid(row=0, column=0, sticky="nsew")
        self.top.grid_rowconfigure(0, weight=100)
        self.top.grid_columnconfigure(0, weight=100)

        self.noteBook = ttk.Notebook(self.main)
        self.noteBook.grid(row=0, column=0, sticky="nsew")
        self.main.grid_rowconfigure(0, weight=100)
        self.main.grid_columnconfigure(0, weight=100)
        # Padding inside each pane of the notebook
        self.paddingInsideNotebookPanes = "12p"

        self.frameFG = self.widgetFG(self.noteBook)
        self.noteBook.add(self.frameFG, text=_('FlightGear settings'))

        self.frameStats = self.widgetStats(self.noteBook)
        self.noteBook.add(self.frameStats, text=_('Statistics'))

        self.frameMisc = self.widgetMisc(self.noteBook)
        self.noteBook.add(self.frameMisc, text=_('Miscellaneous'))

# ----- Buttons ---------------------------------------------------------------
        self.frame_Buttons = ttk.Frame(self.main, padding=(0, "16p", 0, "16p"))
        self.frame_Buttons.grid(row=1, column=0, sticky="nse")
        self.main.grid_rowconfigure(1, weight=100)

        saveButton = ttk.Button(self.frame_Buttons, text=_('Save settings'),
                                command=self.saveAndQuit, padding="4p")
        saveButton.grid(row=0, column=0)
        self.frame_Buttons.grid_rowconfigure(0, weight=100)
        self.frame_Buttons.grid_columnconfigure(0, pad="18p")

        closeButton = ttk.Button(self.frame_Buttons, text=_('Cancel'),
                                 command=self.quit, padding="4p")
        closeButton.grid(row=0, column=1)

        self.top.protocol("WM_DELETE_WINDOW", closeButton.invoke)
        self.top.bind('<Escape>', lambda event, b=closeButton: b.invoke())

    def findFG_bin(self):
        self.chooseExecutable(self.FG_bin)

    def findMagneticField_bin(self):
        self.chooseExecutable(self.MagneticField_bin)

    def chooseExecutable(self, cfgVar):
        try:
            p = fd.askopenfilename(parent=self.top,
                                   initialdir=self.getInitialDir(cfgVar.get()),
                                   title=_('Path to executable file:'))
            if p:
                cfgVar.set(p)
        except tk.TclError:
            pass

    def findFG_root(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_root.get()),
                                title='FG_ROOT:')
            if p:
                self.FG_root.set(p)

        except tk.TclError:
            return

    def findFG_scenery(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_scenery.get()),
                                title='FG_SCENERY:')
            if p:
                self.FG_scenery.set(p)

        except tk.TclError:
            return

    def findFG_aircraft(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_aircraft.get()),
                                title=_('Additional aircraft path:'))
            if p:
                self.FG_aircraft.set(p)

        except tk.TclError:
            return

    def findFgDownloadDir(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_download_dir.get()),
                                title=_('Download directory (optional):'))
            if p:
                self.FG_download_dir.set(p)

        except tk.TclError:
            return

    def findFgWorkingDir(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_working_dir.get()),
                                title=_('Working directory (optional):'))
            if p:
                self.FG_working_dir.set(p)

        except tk.TclError:
            return

    def getInitialDir(self, path):
        if os.path.isdir(path):
            return path
        elif os.path.isfile(path) or os.path.islink(path):
            return os.path.split(path)[0]
        elif os.path.isdir(HOME_DIR):
            return HOME_DIR
        elif platform.system() == "Windows":
             if os.path.isdir("C:\\"):
                 return "C:\\"
             else:
                 return os.getenv("USERPROFILE", os.getcwd())
        elif os.path.isdir("/"):
            return "/"
        else:
            return os.getcwd()

    def getLanguages(self):
        """Walk through a locale directory and return list of
        supported languages based on directory names."""
        res = []
        for d in misc.resourcelistDir("data/locale"):
            if misc.resourceIsDir("data/locale/" + d):
                res.append(d)
        res.sort()
        res = ['-'] + res
        return res

    def initToolTipMessages(self):
        self.tooltip_bin = _("""\
Name or path to the FlightGear executable ('{fgfs}'), or to
'run_fgfs.sh' in case you are using the 'download_and_compile.sh' script.

Note: this corresponds to FG_BIN in the configuration file.""").format(
    fgfs=FG_EXECUTABLE)
        self.tooltip_root = _("""\
Path to FlightGear's main data directory, containing the “base package”.
On Linux, this directory is likely to be something like
/usr/share/games/flightgear if FlightGear was installed using your
distribution package manager. This will be passed to '{fgfs}' (the
FlightGear executable) as the value for the --fg-root option. You may
consult <http://wiki.flightgear.org/$FG_ROOT> for details.""").format(
    fgfs=FG_EXECUTABLE)
        self.tooltip_scenery = _("""\
Path(s) to scenery directories.
You can specify more than one path (separated by {separator!r}), ordered
from highest to lowest priority. You may want to include your TerraSync
directory (if any) in this list in order to specify its priority
relatively to any custom scenery directories you may have installed.

This setting will be passed to '{fgfs}' (the FlightGear executable) as
the value for the --fg-scenery option. It is documented at
<http://wiki.flightgear.org/$FG_SCENERY>.

Note:

  The default TerraSync directory in FlightGear 2016.1.1 is:
    - $FG_HOME/TerraSync on non-Windows systems;
    - something such as
      C:\\Users\\<username>\\Documents\\FlightGear\\TerraSync
      on Windows.

  You may consult <http://wiki.flightgear.org/TerraSync> and
  <http://wiki.flightgear.org/$FG_HOME> for more information.""").format(
      prg=PROGNAME, separator=os.pathsep, fgfs=FG_EXECUTABLE)
        self.tooltip_aircraft = _("""\
Path(s) to additional aircraft directories.
Multiple directories separated by {separator!r} may be specified.

The $FG_ROOT/{defaultAircraftDir} directory is always used; thus, there
is no need to list it here. Leave this field empty unless you are using
additional aircraft directories.""").format(
    separator=os.pathsep, defaultAircraftDir=DEFAULT_AIRCRAFT_DIR)
        self.tooltip_download_dir = _("""\
Optional parameter specifying FlightGear's download directory.
FlightGear uses this directory to store things it automatically
downloads, such as TerraSync scenery and aircraft (the latter: when
using FlightGear's built-in launcher).

Leave this field empty if you want to use FlightGear's default download
directory.""")
        self.tooltip_working_dir = _("""\
Optional parameter specifying FlightGear's working directory.
That is the directory FlightGear will be run from. It can affect the
default location of some files created by FlightGear (screenshots...).
If left blank, the working directory is the user's home directory.""")
        self.tooltip_langMenu = _("""\
Language used in {prg}. If no language is selected, {prg} will use the
system language.""").format(prg=PROGNAME)
        self.tooltip_aptMenu = _("""\
Select the primary data source where {prg} will be looking for
information about parking positions. There are two options:

Scenery - Parking data will be read from
    $FG_SCENERY/Airports/[I]/[C]/[A]/[ICAO].groundnet.xml. {prg} will
    use the first match if FG_SCENERY contains several paths.

Old default - Parking data will be read from
    $FG_ROOT/AI/Airports/[ICAO]/parking.xml.

(for example, for the EDDF airport, [ICAO] should be replaced with
EDDF, [I] with E, [C] with D, [A] with D and [O] with F:
[I]/[C]/[A]/[ICAO].groundnet.xml → E/D/D/EDDF.groundnet.xml)

Note:

  In both cases, if no parking position is found, {prg} will look into
  the apt.dat files present inside scenery paths under NavData/apt.

With FlightGear 2.6 and later, it is advised to choose "Scenery"; it
is now the default in {prg}.

For more information, you may consult:

  http://wiki.flightgear.org/About_Scenery/Airports""").format(prg=PROGNAME)
        self.tooltip_autoAptMenu = _("""\
Automatic - {prg} will try to keep track of changes to the apt.dat
    files, and will automatically rebuild its own airport database
    ({aptDigest}) when this happens.

Manual - The “Rebuild Airport Database” button must be used every time
    the ordered list of apt.dat files is changed, or any of these
    files.""").format(prg=PROGNAME, aptDigest=APT)
        self.tooltip_rebuildApt = _("""\
Rebuild the airport database from the apt.dat files present inside
scenery paths under NavData/apt. This must be done every time the
ordered list of these files is changed, or any of their contents. If you
have left “Airport database update” to its default setting of Automatic,
you don't have to worry about that: the rebuild will be done
automatically every time it is needed.""")
        self.tooltip_fontSize = _("""\
Set the base font size in the range from {0} to {1}. Zero is a special
value corresponding to a platform-dependent default size.""").format(
    MIN_BASE_FONT_SIZE, MAX_BASE_FONT_SIZE)
        self.tooltip_MagneticFieldBin = _("""\
Name or path to GeographicLib's MagneticField executable. If left
blank, '{MagneticField}' will be searched in your PATH.""").format(
    MagneticField=misc.executableFileName("MagneticField"))
        self.tooltip_rememberMainWinPos = _("""\
When saving the configuration, don't store the main window size only,
but also its position (i.e., the offsets from the screen borders).
When this option is unchecked, only the main window size is stored.""")
        self.tooltip_autoscrollFGOutput = _(
            "Automatically scroll the FlightGear Output Window to the end "
            "every time new text is received from FlightGear's stdout or "
            "stderr stream.")
        self.tooltip_fakeParkposOption = _(
            "Translate the --parkpos option into a sequence of --lat, --lon "
            "and --heading options. This is useful when --parkpos is broken "
            "in FlightGear; otherwise, it is probably better to leave this "
            "option disabled.")

    def quit(self):
        """Quit without saving."""
        # Destroying more widgets would probably be better for memory...
        for w in (self.top, self.main, self.noteBook, self.frameFG,
                  self.frameMisc):
            w.destroy()

    def resetBaseFontSize(self):
        self.baseFontSize.set(int(float(DEFAULT_BASE_FONT_SIZE)))

    def saveAndQuit(self):
        if not self.validateStandardWidgets():
            return

        if self.apt_data_source.get() == _('Scenery'):
            self.config.apt_data_source.set(1)
        else:
            self.config.apt_data_source.set(0)

        if self.auto_update_apt.get() == _('Automatic'):
            self.config.auto_update_apt.set(1)
        else:
            self.config.auto_update_apt.set(0)

        self.config.FG_bin.set(self.FG_bin.get())
        self.config.FG_root.set(self.FG_root.get())
        self.config.FG_scenery.set(self.FG_scenery.get())
        self.config.FG_aircraft.set(self.FG_aircraft.get())
        self.config.FG_download_dir.set(self.FG_download_dir.get())
        self.config.FG_working_dir.set(self.FG_working_dir.get())
        self.config.MagneticField_bin.set(self.MagneticField_bin.get())
        if self.language.get() == '-':
            self.config.language.set('')
        else:
            self.config.language.set(self.language.get())
        self.saveBaseFontSize()
        self.config.saveWindowPosition.set(self.rememberMainWinPos.get())
        self.config.autoscrollFGOutput.set(self.autoscrollFGOutput.get())
        self.config.fakeParkposOption.set(self.fakeParkposOption.get())

        for name in ("aircraftStatsShowPeriod", "aircraftStatsExpiryPeriod",
                     "airportStatsShowPeriod", "airportStatsExpiryPeriod"):
            tkConfigVar = getattr(self.config, name)
            tkConfigVar.set(getattr(self, name).get())

        self.config.write(text=self.text)
        self.reset_flag = True
        self.quit()

    def saveBaseFontSize(self):
        value = self.validateBaseFontSize()
        if int(self.config.baseFontSize.get()) != int(value):
            message = _('Some changes may need a restart to be effective')
            detail = _("It may be necessary to restart {prg} in order to "
                       "see the full effects of changing the font size.") \
                       .format(prg=PROGNAME)
            showinfo(_('{prg}').format(prg=PROGNAME), message, detail=detail,
                     parent=self.top)

            self.config.baseFontSize.set(value)
            self.config.setupFonts()  # Apply the change

    def validateBaseFontSize(self):
        v = self.getBaseFontSize()
        min_size = int(float(MIN_BASE_FONT_SIZE))
        max_size = int(float(MAX_BASE_FONT_SIZE))
        if v != 0 and v < min_size:
            size = min_size
        elif v > max_size:
            size = max_size
        else:
            size = v
        return str(size)

    def getBaseFontSize(self):
        try:
            v = int(float(self.baseFontSize.get()))
        except ValueError:
            v = int(float(DEFAULT_BASE_FONT_SIZE))
        return v

    def widgetFG(self, parent):
        """FlightGear settings widget."""
        frame_FG = ttk.Frame(parent, padding=self.paddingInsideNotebookPanes)
        frame_FG.grid_columnconfigure(0, weight=100)

        def addSettingsLine(rowNum, isLast, container, labelText, tkVar,
                            tooltipText, buttonCallback):
            verticalSpaceBetweenRows = "12p"

            label = ttk.Label(container, text=labelText)
            label.grid(row=3*rowNum, column=0, columnspan=2, sticky="w")
            container.grid_rowconfigure(3*rowNum, weight=100)
            ToolTip(label, tooltipText)

            entry = ttk.Entry(container, width=50, textvariable=tkVar)
            entry.grid(row=3*rowNum+1, column=0, sticky="ew")
            container.grid_rowconfigure(3*rowNum+1, weight=100)
            ToolTip(entry, tooltipText)

            button = ttk.Button(container, text=_('Find'),
                                command=buttonCallback)
            button.grid(row=3*rowNum+1, column=1, padx="12p")

            if not isLast:
                spacer = ttk.Frame(container)
                spacer.grid(row=3*rowNum+2, column=0, sticky="nsew")
                container.grid_rowconfigure(
                    3*rowNum+2, minsize=verticalSpaceBetweenRows, weight=100)

        t = ((_("FlightGear executable:"),
              self.FG_bin, self.tooltip_bin, self.findFG_bin),
             ('FG_ROOT:', self.FG_root,
              self.tooltip_root, self.findFG_root),
             ('FG_SCENERY:', self.FG_scenery,
              self.tooltip_scenery, self.findFG_scenery),
             (_('Additional aircraft path(s):'), self.FG_aircraft,
              self.tooltip_aircraft, self.findFG_aircraft),
             (_('Download directory (optional):'), self.FG_download_dir,
              self.tooltip_download_dir, self.findFgDownloadDir),
             (_('Working directory (optional):'), self.FG_working_dir,
              self.tooltip_working_dir, self.findFgWorkingDir))
        lt = len(t)

        for i, (labelText, tkVar, tooltipText, buttonCallback) in enumerate(t):
            addSettingsLine(i, i == lt-1, frame_FG, labelText, tkVar,
                            tooltipText, buttonCallback)

        return frame_FG

    def widgetStats(self, parent):
        """Widget used for the “Statistics” pane of the Notebook."""
        outerFrame = ttk.Frame(parent, padding=self.paddingInsideNotebookPanes)
        outerFrame.grid_columnconfigure(0, weight=0) # default: non-stretchable
        outerFrame.grid_columnconfigure(1, weight=100)

        # Common width for all 4 Spinbox instances that are going to be created
        spinboxWd = 6
        nonNegativeIntValidateCmd = self.master.register(
            self._nonNegativeIntValidateFunc)
        statsPeriodInvalidCmd = self.master.register(
            self._statsPeriodInvalidFunc)

        def createLine(rowNum, isLast, container, tkVar, labelText,
                       tooltipText):
            verticalSpaceBetweenRows = "12p"

            label = ttk.Label(container, text=labelText)
            label.grid(row=2*rowNum, column=0, sticky="w")
            container.grid_rowconfigure(2*rowNum, weight=0) # not stretchable
            ToolTip(label, tooltipText, autowrap=True)

            spinbox = tk.Spinbox(
                container, from_=0, to=sys.maxsize, increment=1,
                repeatinterval=20, textvariable=tkVar,
                width=spinboxWd, validate="focusout",
                validatecommand=(nonNegativeIntValidateCmd, "%P"),
                invalidcommand=(statsPeriodInvalidCmd, "%W", "%P"))
            # Used to run the validation code manually in some cases, such as
            # when the user clicks on the “Save” button (otherwise, the
            # validate command isn't called).
            self.validatingWidgets.append(
                # 'container': pane of self.noteBook that must be selected to
                # allow the user to see the widget with invalid contents
                 ValidatingWidget(spinbox, container,
                                  self._nonNegativeIntValidateFunc,
                                  self._statsPeriodInvalidFunc))
            spinbox.grid(row=2*rowNum, column=1, sticky="w")
            ToolTip(spinbox, tooltipText, autowrap=True)

            if not isLast:      # insert a non-stretchable spacer
                spacer = ttk.Frame(container)
                spacer.grid(row=2*rowNum+1, column=0, sticky="nsew")
                container.grid_rowconfigure(
                    2*rowNum+1, minsize=verticalSpaceBetweenRows, weight=0)

        t = ((self.aircraftStatsShowPeriod,
              _("Aircraft statistics show period: "),
              _("The “use count” for each aircraft is the number of days "
                "it was used during the last n days, where n is the number "
                "entered here.")),
             (self.aircraftStatsExpiryPeriod,
              _("Aircraft statistics expiry period: "),
              _("{prg} automatically forgets about dates you used a "
                "given aircraft when they get older than this number of "
                "days.").format(prg=PROGNAME)),
             (self.airportStatsShowPeriod,
              _("Airports statistics show period: "),
              _("The “visit count” for each airport is the number of days "
                "it was visited during the last n days, where n is the "
                "number entered here.")),
             (self.airportStatsExpiryPeriod,
              _("Airports statistics expiry period: "),
              _("{prg} automatically forgets about dates you visited a "
                "given airport when they get older than this number of "
                "days.").format(prg=PROGNAME)))
        lt = len(t)

        for i, (tkVar, labelText, tooltipText) in enumerate(t):
            createLine(i, i == lt-1, outerFrame, tkVar, labelText, tooltipText)

        return outerFrame

    def _nonNegativeIntValidateFunc(self, text):
        """Validate a string that should contain a non-negative integer."""
        try:
            n = int(text)
        except ValueError:
            return False

        return (n >= 0)

    def _statsPeriodInvalidFunc(self, widgetPath, text):
        """
        Callback function used when an invalid number of days has been input."""
        widget = self.master.nametowidget(widgetPath)

        # Get the Tkinter “window name” of the current pane
        currentPaneWPath = self.noteBook.select()
        # If the validation failure was triggered by the user switching to
        # another pane, get back to the pane where there is invalid input.
        if (self.master.nametowidget(currentPaneWPath) is not self.frameStats):
            self.noteBook.select(self.frameStats)

        message = _('Invalid number of days')
        detail = _("A non-negative integer is required.")
        showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail,
                  parent=self.top)

        widget.focus_set()      # give focus to the widget with invalid input

    def widgetMisc(self, parent):
        """Miscellaneous settings widget."""
        outerFrame = ttk.Frame(parent, padding=self.paddingInsideNotebookPanes)
        verticalSpaceBetweenRows = "6p"
        horizSpaceBetweenLabelAndControl = "6p"
        horizSeparationForUnrelatedThings = "15p"

        def addHorizSpacer(container, rowNum, colNum,
                           minWidth=horizSpaceBetweenLabelAndControl,
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

        # Logical row number in OuterFrame. For each “logical” row, there are
        # two “physical” rows in OuterFrame's grid, one with widgets followed
        # by one only containing a spacer frame (except there is no spacer
        # after the last row).
        rowNum = 0

        frame1 = ttk.Frame(outerFrame)
        frame1.grid(row=2*rowNum, column=0, sticky="ew")
        outerFrame.grid_rowconfigure(2*rowNum, weight=0) # non-stretchable
        outerFrame.grid_columnconfigure(0, weight=100) # stretchable

        # Language menu
        rowNum += 1
        frame1Left = ttk.Frame(frame1)
        frame1Left.grid(row=0, column=0, sticky="ew")
        frame1.grid_columnconfigure(0, weight=100) # stretchable

        langLabel = ttk.Label(frame1Left, text=_('Language:'))
        ToolTip(langLabel, self.tooltip_langMenu)
        langLabel.grid(row=0, column=0, sticky="w")

        addHorizSpacer(frame1Left, 0, 1)

        languages = self.getLanguages()
        langMenu = ttk.OptionMenu(frame1Left, self.language,
                                  self.language.get(), *languages)
        ToolTip(langMenu, self.tooltip_langMenu)
        langMenu.grid(row=0, column=2, sticky="w")
        frame1Left.grid_columnconfigure(2, weight=100)

        # Make sure there is a space between what is defined above and what is
        # defined below, even if some translated string is very long.
        addHorizSpacer(frame1Left, 0, 3,
                       minWidth=horizSeparationForUnrelatedThings, weight=100)

        # Font size
        frame1Right = ttk.Frame(frame1)
        frame1Right.grid(row=0, column=1, sticky="e")

        fontsizeLabel = ttk.Label(frame1Right, text=_('Font size:'))
        ToolTip(fontsizeLabel, self.tooltip_fontSize)
        fontsizeLabel.grid(row=0, column=0, sticky="w")

        addHorizSpacer(frame1Right, 0, 1)

        backupBaseFontSize = str(self.baseFontSize.get())
        v = ((0,) + tuple(range(int(float(MIN_BASE_FONT_SIZE)),
                                int(float(MAX_BASE_FONT_SIZE)) + 1)))
        fontsizeSpinbox = tk.Spinbox(frame1Right, values=v,
                                     textvariable=self.baseFontSize,
                                     width=4, justify='right')
        # Workaround for a bug (or undocumented feature) of the Spinbox widget
        # that overrides a textvariable value at its initialization if
        # a values option is used. Tested in Python 2.7.3
        self.baseFontSize.set(backupBaseFontSize)

        ToolTip(fontsizeSpinbox, self.tooltip_fontSize)
        fontsizeSpinbox.grid(row=0, column=2, sticky="w")

        fontsizeResetButton = ttk.Button(
            frame1Right, text=pgettext('font size', 'Default'),
            command=self.resetBaseFontSize)
        ToolTip(fontsizeResetButton, self.tooltip_fontSize)
        fontsizeResetButton.grid(row=0, column=3, sticky="w", padx="12p")

        addVertSpacer(outerFrame, 2*rowNum+1)

        # Apt source menu
        rowNum += 1
        frame2 = ttk.Frame(outerFrame)
        frame2.grid(row=2*rowNum, column=0, sticky="w")

        aptLabel = ttk.Label(frame2, text=_('Airport data source:'))
        ToolTip(aptLabel, self.tooltip_aptMenu)
        aptLabel.grid(row=0, column=0, sticky="w")

        addHorizSpacer(frame2, 0, 1)

        aptMenu = ttk.OptionMenu(frame2, self.apt_data_source,
                                 self.apt_data_source.get(),
                                 _('Scenery'), _('Old default'))
        ToolTip(aptMenu, self.tooltip_aptMenu)
        aptMenu.grid(row=0, column=2, sticky="w")

        addVertSpacer(outerFrame, 2*rowNum+1)

        # “Airport database update” menu and “Rebuild airport database” button
        rowNum += 1
        frame3 = ttk.Frame(outerFrame)
        frame3.grid(row=2*rowNum, column=0, sticky="ew")

        autoAptLabel = ttk.Label(frame3,
                                 text=_('Airport database update:') + " ")
        ToolTip(autoAptLabel, self.tooltip_autoAptMenu)
        autoAptLabel.grid(row=0, column=0, sticky="w")

        addHorizSpacer(frame3, 0, 1)

        autoAptMenu = ttk.OptionMenu(frame3, self.auto_update_apt,
                                     self.auto_update_apt.get(),
                                     _('Automatic'), _('Manual'))
        ToolTip(autoAptMenu, self.tooltip_autoAptMenu)
        autoAptMenu.grid(row=0, column=2, sticky="w")
        frame3.grid_columnconfigure(2, weight=100) # stretchable

        addHorizSpacer(frame3, 0, 3,
                       minWidth=horizSeparationForUnrelatedThings, weight=100)

        rebuildAptDbButton = ttk.Button(frame3,
                                        text=_('Rebuild airport database'),
                                        command=self.config.makeAptDigest,
                                        padding="6p")
        ToolTip(rebuildAptDbButton, self.tooltip_rebuildApt)
        rebuildAptDbButton.grid(row=0, column=4, sticky="e")

        addVertSpacer(outerFrame, 2*rowNum+1)

        # MagneticField executable
        rowNum += 1
        frame_MagField = ttk.Frame(outerFrame)
        frame_MagField.grid(row=2*rowNum, column=0, sticky="ew")

        magneticFieldBinLabel = ttk.Label(frame_MagField,
            text=_("GeographicLib's MagneticField executable:"))
        ToolTip(magneticFieldBinLabel, self.tooltip_MagneticFieldBin)
        magneticFieldBinLabel.grid(row=0, column=0, sticky="w")

        frame_MagFieldInner = ttk.Frame(frame_MagField)
        frame_MagFieldInner.grid(row=1, column=0, sticky="ew")
        magneticFieldBinEntry = ttk.Entry(frame_MagFieldInner, width=50,
                                          textvariable=self.MagneticField_bin)
        ToolTip(magneticFieldBinEntry, self.tooltip_MagneticFieldBin)
        magneticFieldBinEntry.grid(row=0, column=0, sticky="ew")

        magneticFieldBinFind = ttk.Button(frame_MagFieldInner, text=_('Find'),
                                          command=self.findMagneticField_bin)
        magneticFieldBinFind.grid(row=0, column=1, sticky="w", padx="12p")

        addVertSpacer(outerFrame, 2*rowNum+1)

        # “Remember main windows position” checkbox
        rowNum += 1
        frame_checkboxes = ttk.Frame(outerFrame)
        frame_checkboxes.grid(row=2*rowNum, column=0, sticky="ew")

        rememberMainWinPosCb = ttk.Checkbutton(
            frame_checkboxes,
            text=_('Remember the main window position'),
            variable=self.rememberMainWinPos)
        ToolTip(rememberMainWinPosCb, self.tooltip_rememberMainWinPos)
        rememberMainWinPosCb.grid(row=0, column=0, sticky="w")

        # “Automatically scroll the Output Window” checkbox
        rowNum += 1
        autoscrollFGOutputCb = ttk.Checkbutton(
            frame_checkboxes,
            text=_('Automatically scroll the Output Window'),
            variable=self.autoscrollFGOutput)
        ToolTip(autoscrollFGOutputCb, self.tooltip_autoscrollFGOutput,
                autowrap=True)
        autoscrollFGOutputCb.grid(row=1, column=0, sticky="w")

        # “Fake the --parkpos option” checkbox
        rowNum += 1
        fakeParkposOptionCb = ttk.Checkbutton(
            frame_checkboxes,
            text=_('Fake the --parkpos option'),
            variable=self.fakeParkposOption)
        ToolTip(fakeParkposOptionCb, self.tooltip_fakeParkposOption,
                autowrap=True)
        fakeParkposOptionCb.grid(row=2, column=0, sticky="w")

        return outerFrame

    def validateStandardWidgets(self):
        # Validate the contents of some widgets in case one of them still
        # has the focus.
        for validating in self.validatingWidgets:
            val = validating.widget.get()
            if not validating.validateFunc(val):
                self.noteBook.select(validating.paneWidget)
                validating.widget.focus_set()
                validating.invalidFunc(str(validating.widget), val)
                return False

        return True
