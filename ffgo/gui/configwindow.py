"""Display preferences window."""


import os
from tkinter import *
import tkinter.filedialog as fd

from .. import misc
from .tooltip import ToolTip
from ..constants import *


class ConfigWindow:

    def __init__(self, master, config, text):
        self.master = master
        self.config = config
        self.text = text

        self.apt_data_source = StringVar()
        self.auto_update_apt = StringVar()
        self.FG_bin = StringVar()
        self.FG_root = StringVar()
        self.FG_scenery = StringVar()
        self.FG_aircraft = StringVar()
        self.FG_working_dir = StringVar()
        self.language = StringVar()
        self.baseFontSize = StringVar()

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
        self.FG_working_dir.set(self.config.FG_working_dir.get())
        if self.config.language.get():
            self.language.set(self.config.language.get())
        else:
            self.language.set('-')
        self.baseFontSize.set(self.config.baseFontSize.get())

        self.reset_flag = False
        self.initToolTipMessages()

# -----------------------------------------------------------------------------

        self.top = Toplevel(self.master)
        self.top.grab_set()  # Focus input on that window.
        self.top.title(_('Preferences'))
        self.top.transient(self.master)

        self.main = Frame(self.top, borderwidth=0)
        self.main.pack(side='top', padx=12, fill='x', expand=True, anchor='n')

        self.frame = Frame(self.main, borderwidth=1, relief='sunken')
        self.frame.pack(side='top', fill='x', expand=True)
# ----- Tabs ------------------------------------------------------------------
        self.tabs = Frame(self.frame)
        self.tabs.pack(side='top', fill='x', expand=True)

        self.tabFG = Button(self.tabs, text=_('FlightGear settings'),
                            borderwidth=1, relief='ridge',
                            command=self.showFGSettings)
        self.tabFG.pack(side='left')

        self.tabMisc = Button(self.tabs, text=_('Miscellaneous'),
                              borderwidth=1, relief='ridge',
                              command=self.showMiscSettings)
        self.tabMisc.pack(side='left')
# ----- Main content ----------------------------------------------------------
        # Here is placed content from: widgetFG, widgetTS, and widgetMics.
        self.frame = Frame(self.frame, borderwidth=1, relief='raised')
        self.frame.pack(side='top', fill='x', expand=True)
# ----- Buttons ---------------------------------------------------------------
        self.frame_Buttons = Frame(self.main, borderwidth=12)
        self.frame_Buttons.pack(side='bottom')

        self.frame_save_button = Frame(self.frame_Buttons, borderwidth=4)
        self.frame_save_button.pack(side='left')

        self.save = Button(self.frame_save_button, text=_('Save settings'),
                           command=self.saveAndQuit)
        self.save.pack(side='left')

        self.frame_close_button = Frame(self.frame_Buttons, borderwidth=4)
        self.frame_close_button.pack(side='right')

        self.close = Button(self.frame_close_button, text=_('Cancel'),
                            command=self.quit)
        self.close.pack(side='left')
        self.top.bind('<Escape>', lambda event: self.close.invoke())
# -----------------------------------------------------------------------------
        # Show FG settings tab by default.
        self.showFGSettings()

    def cleanUpWidgets(self):
        """Destroy active widget."""
        try:
            self.frame_FG.destroy()
        except AttributeError:
            pass
        try:
            self.frame_misc.destroy()
        except AttributeError:
            pass

    def findFG_bin(self):
        try:
            p = fd.askopenfilename(parent=self.top,
                                   initialdir=self.getInitialDir(
                                       self.FG_bin.get()),
                                   title=_('Path to executable file:'))
            if p:
                self.FG_bin.set(p)

        except TclError:
            return

    def findFG_root(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_root.get()),
                                title='FG_ROOT:')
            if p:
                self.FG_root.set(p)

        except TclError:
            return

    def findFG_scenery(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_scenery.get()),
                                title='FG_SCENERY:')
            if p:
                self.FG_scenery.set(p)

        except TclError:
            return

    def findFG_aircraft(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_aircraft.get()),
                                title=_('Additional aircraft path:'))
            if p:
                self.FG_aircraft.set(p)

        except TclError:
            return

    def findFgWorkingDir(self):
        try:
            p = fd.askdirectory(parent=self.top,
                                initialdir=self.getInitialDir(
                                    self.FG_working_dir.get()),
                                title=_('Working directory (optional):'))
            if p:
                self.FG_working_dir.set(p)

        except TclError:
            return

    def getInitialDir(self, path):
        if os.path.isdir(path):
            return path
        if os.path.isfile(path) or os.path.islink(path):
            return os.path.split(path)[0]
        else:
            return HOME_DIR

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
Enter the path to the "fgfs" executable, or "run_fgfs.sh", if you are
using download_and_compile.sh scripts.

Note: this path corresponds to FG_BIN in the configuration file.""")
        self.tooltip_root = _("""\
Path to FlightGear's main data directory, containing the “base package”.
On Linux, this directory is likely to be something like
/usr/share/games/flightgear if FlightGear was installed using your
distribution package manager. This will be passed to fgfs as the value
for the --fg-root= option. You may consult
<http://wiki.flightgear.org/$FG_ROOT> for details.""")
        self.tooltip_scenery = _("""\
Path(s) to scenery directories.
You can specify more than one path (separated by {separator!r}), ordered
from highest to lowest priority. Typical configuration is to have
the TerraSync directory first, followed by custom scenery directories
if you have installed any.

Note:

  The default TerraSync directory in FlightGear 3.6 should be
  '{defaultTSdir}' on your
  operating system (otherwise, please report a bug for {prg}).""").format(
      prg=PROGNAME, defaultTSdir=DEFAULT_TERRASYNC_DIR, separator=os.pathsep)
        self.tooltip_aircraft = _("""\
Path(s) to additional aircraft directories.
Multiple directories separated by {separator!r} may be specified. Leave
this field empty if you are not using additional aircraft directories.""") \
        .format(separator=os.pathsep)
        self.tooltip_working_dir = _("""\
Optional parameter specifying FlightGear's working directory.
That is the directory FlightGear will be run from. It can affect the
default location of some files created by FlightGear (screenshots...).
If left blank, the working directory is the user's home directory.""")
        self.tooltip_langMenu = _("""\
Choose other language. If not selected, {prg} will try to choose the
system language.""").format(prg=PROGNAME)
        self.tooltip_aptMenu = _("""\
Select data source where {prg} will be looking for information about
parking positions. There are two options:

Scenery - Parking data will be read from
    $FG_SCENERY/Airports/[I]/[C]/[A]/[ICAO].groundnet.xml. {prg} will
    use the first match if FG_SCENERY contains several paths.

Old default - Parking data will be read from
    $FG_ROOT/AI/Airports/[ICAO]/parking.xml.

(for example, for the EDDF airport, [ICAO] should be replaced with
EDDF, [I] with E, [C] with D, [A] with D and [O] with F)

With FlightGear 2.6 and later, it is advised to choose "Scenery"; it
is now the default in {prg}.

For more information, you may consult:

  http://wiki.flightgear.org/About_Scenery/Airports""").format(prg=PROGNAME)
        self.tooltip_autoAptMenu = _("""\
Automatic - {prg} will try to keep track of changes to
    FG_ROOT/Airports/apt.dat.gz file, and will automatically rebuild
    its own airport database when this happens.

Manual - The “Rebuild Airport Database” button needs to be used every
    time FG_ROOT/Airports/apt.dat.gz is changed (for instance, this is
    likely to happen when FlightGear is updated).""").format(prg=PROGNAME)
        self.tooltip_rebuildApt = _("""\
Build new airport database from current FG_ROOT/Airports/apt.dat.gz.
Useful when apt.dat.gz file has been updated.""")
        self.tooltip_fontSize = _("""\
Set the base font size in the range from {0} to {1}. Zero is a special
value corresponding to a platform-dependent default size.""").format(
    MIN_BASE_FONT_SIZE, MAX_BASE_FONT_SIZE)
        self.tooltip_rememberMainWinPos = _("""\
When saving the configuration, don't store the main window size only,
but also its position (i.e., the offsets from the screen borders).
When this option is unchecked, only the main window size is stored.""")

    def quit(self):
        """Quit without saving."""
        self.top.destroy()

    def resetBaseFontSize(self):
        self.baseFontSize.set(int(float(DEFAULT_BASE_FONT_SIZE)))

    def resetTabs(self):
        """Reset tabs."""
        self.tabFG.configure(borderwidth=2, relief='ridge')
        self.tabMisc.configure(borderwidth=2, relief='ridge')

    def saveAndQuit(self):
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
        self.config.FG_working_dir.set(self.FG_working_dir.get())
        if self.language.get() == '-':
            self.config.language.set('')
        else:
            self.config.language.set(self.language.get())
        self.saveBaseFontSize()

        self.config.write(text=self.text)
        self.reset_flag = True
        self.top.destroy()

    def saveBaseFontSize(self):
        value = self.validateBaseFontSize()
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

    def showFGSettings(self):
        if self.tabFG.cget('relief') != 'raised':
            self.resetTabs()
            self.tabFG.configure(borderwidth=1, relief='raised')
            self.cleanUpWidgets()
            self.widgetFG()

    def showMiscSettings(self):
        if self.tabMisc.cget('relief') != 'raised':
            self.resetTabs()
            self.tabMisc.configure(borderwidth=1, relief='raised')
            self.cleanUpWidgets()
            self.widgetMisc()

    def widgetFG(self):
        """FlightGear settings widget."""
        self.frame_FG = Frame(self.frame, borderwidth=8)
        self.frame_FG.pack(side='top', fill='x', expand=True)

        self.FG_label = Label(self.frame_FG, text=_('FlightGear settings'))
        self.FG_label.pack(side='top')

        # FG_BIN
        self.frame_FG_1 = Frame(self.frame_FG, borderwidth=4)
        self.frame_FG_1.pack(side='top', fill='x', expand=True)

        self.frame_FG_11 = Frame(self.frame_FG_1)
        self.frame_FG_11.pack(side='top', fill='x', expand=True)

        self.FG_binLabel = Label(self.frame_FG_11,
                                 text=_('Path to executable file:'))
        self.FG_binLabel.pack(side='left')

        self.frame_FG_12 = Frame(self.frame_FG_1)
        self.frame_FG_12.pack(side='top', fill='x', expand=True)

        self.FG_binEntry = Entry(self.frame_FG_12, bg=TEXT_BG_COL,
                                 width=50, textvariable=self.FG_bin)
        ToolTip(self.FG_binEntry, self.tooltip_bin)
        self.FG_binEntry.pack(side='left', fill='x', expand=True)

        self.FG_binFind = Button(self.frame_FG_12, text=_('Find'),
                                 command=self.findFG_bin)
        self.FG_binFind.pack(side='left')
        # FG_ROOT
        self.frame_FG_2 = Frame(self.frame_FG, borderwidth=4)
        self.frame_FG_2.pack(side='top', fill='x', expand=True)

        self.frame_FG_21 = Frame(self.frame_FG_2)
        self.frame_FG_21.pack(side='top', fill='x', expand=True)

        self.FG_rootLabel = Label(self.frame_FG_21, text='FG_ROOT:')
        self.FG_rootLabel.pack(side='left')

        self.frame_FG_22 = Frame(self.frame_FG_2)
        self.frame_FG_22.pack(side='top', fill='x', expand=True)

        self.FG_rootEntry = Entry(self.frame_FG_22, bg=TEXT_BG_COL,
                                  width=50, textvariable=self.FG_root)
        ToolTip(self.FG_rootEntry, self.tooltip_root)
        self.FG_rootEntry.pack(side='left', fill='x', expand=True)

        self.FG_rootFind = Button(self.frame_FG_22, text=_('Find'),
                                  command=self.findFG_root)
        self.FG_rootFind.pack(side='left')
        # FG_SCENERY
        self.frame_FG_3 = Frame(self.frame_FG, borderwidth=4)
        self.frame_FG_3.pack(side='top', fill='x', expand=True)

        self.frame_FG_31 = Frame(self.frame_FG_3)
        self.frame_FG_31.pack(side='top', fill='x', expand=True)

        self.FG_sceneryLabel = Label(self.frame_FG_31, text='FG_SCENERY:')
        self.FG_sceneryLabel.pack(side='left')

        self.frame_FG_32 = Frame(self.frame_FG_3)
        self.frame_FG_32.pack(side='top', fill='x', expand=True)

        self.FG_sceneryEntry = Entry(self.frame_FG_32, bg=TEXT_BG_COL,
                                     width=50, textvariable=self.FG_scenery)
        ToolTip(self.FG_sceneryEntry, self.tooltip_scenery)
        self.FG_sceneryEntry.pack(side='left', fill='x', expand=True)

        self.FG_sceneryFind = Button(self.frame_FG_32, text=_('Find'),
                                     command=self.findFG_scenery)
        self.FG_sceneryFind.pack(side='left')

        # FG_AIRCRAFT
        self.frame_FG_4 = Frame(self.frame_FG, borderwidth=4)
        self.frame_FG_4.pack(side='top', fill='x', expand=True)

        self.frame_FG_41 = Frame(self.frame_FG_4)
        self.frame_FG_41.pack(side='top', fill='x', expand=True)

        self.FG_aircraftLabel = Label(self.frame_FG_41,
                                      text=_('Additional aircraft path(s):'))
        self.FG_aircraftLabel.pack(side='left')

        self.frame_FG_42 = Frame(self.frame_FG_4)
        self.frame_FG_42.pack(side='top', fill='x', expand=True)

        self.FG_aircraftEntry = Entry(self.frame_FG_42, bg=TEXT_BG_COL,
                                      width=50, textvariable=self.FG_aircraft)
        ToolTip(self.FG_aircraftEntry, self.tooltip_aircraft)
        self.FG_aircraftEntry.pack(side='left', fill='x', expand=True)

        self.FG_aircraftFind = Button(self.frame_FG_42, text=_('Find'),
                                      command=self.findFG_aircraft)
        self.FG_aircraftFind.pack(side='left')
        # FG working directory
        self.frame_FG_5 = Frame(self.frame_FG, borderwidth=4)
        self.frame_FG_5.pack(side='top', fill='x', expand=True)

        self.frame_FG_51 = Frame(self.frame_FG_5)
        self.frame_FG_51.pack(side='top', fill='x', expand=True)

        self.FG_working_dirLabel = Label(self.frame_FG_51,
                                         text=_('Working directory (optional):'))
        self.FG_working_dirLabel.pack(side='left')

        self.frame_FG_52 = Frame(self.frame_FG_5)
        self.frame_FG_52.pack(side='top', fill='x', expand=True)

        self.FG_working_dirEntry = Entry(self.frame_FG_52, bg=TEXT_BG_COL,
                                         width=50, textvariable=self.FG_working_dir)
        ToolTip(self.FG_working_dirEntry, self.tooltip_working_dir)
        self.FG_working_dirEntry.pack(side='left', fill='x', expand=True)

        self.FG_working_dirFind = Button(self.frame_FG_52, text=_('Find'),
                                         command=self.findFgWorkingDir)
        self.FG_working_dirFind.pack(side='left')

    def widgetMisc(self):
        """Miscellaneous settings widget."""
        self.frame_misc = Frame(self.frame, borderwidth=8)
        self.frame_misc.pack(side='top', fill='x', expand=True)

        self.misc_label = Label(self.frame_misc, text=_('Miscellaneous'))
        self.misc_label.pack(side='top')

        self.frame_misc_1 = Frame(self.frame_misc, borderwidth=4)
        self.frame_misc_1.pack(side='top', fill='x', expand=True)
        # Language menu
        self.frame_misc_11 = Frame(self.frame_misc_1)
        self.frame_misc_11.pack(side='left', fill='x', expand=True)

        self.lang_label = Label(self.frame_misc_11, text=_('Change language:'))
        ToolTip(self.lang_label, self.tooltip_langMenu)
        self.lang_label.pack(side='left')

        self.langMenu = OptionMenu(self.frame_misc_11, self.language,
                                   *self.getLanguages())
        ToolTip(self.langMenu, self.tooltip_langMenu)
        self.langMenu.pack(side='left')
        # Font size
        frame_misc_12 = Frame(self.frame_misc_1)
        frame_misc_12.pack(side='left', fill='x', expand=True)

        fontsize_label = Label(frame_misc_12, text=_('Font size:'))
        ToolTip(fontsize_label, self.tooltip_fontSize)
        fontsize_label.pack(side='left')

        backupBaseFontSize = str(self.baseFontSize.get())
        v = ((0,) + tuple(range(int(float(MIN_BASE_FONT_SIZE)),
                                int(float(MAX_BASE_FONT_SIZE)) + 1)))
        self.fontsize_entry = Spinbox(frame_misc_12, values=v,
                                      textvariable=self.baseFontSize,
                                      width=4, justify='right')
        # Workaround for a bug (or undocumented feature) of the Spinbox widget
        # that overrides a textvariable value at its initialization if
        # a values option is used. Tested in Python 2.7.3
        self.baseFontSize.set(backupBaseFontSize)

        ToolTip(self.fontsize_entry, self.tooltip_fontSize)
        self.fontsize_entry.pack(side='left')

        fontsize_reset_button = Button(frame_misc_12, text=_('Default'),
                                       command=self.resetBaseFontSize)
        ToolTip(fontsize_reset_button, self.tooltip_fontSize)
        fontsize_reset_button.pack(side='left')

        # Apt source menu
        self.frame_misc_2 = Frame(self.frame_misc, borderwidth=8)
        self.frame_misc_2.pack(side='top', fill='x', expand=True)

        self.frame_misc_22 = Frame(self.frame_misc_2)
        self.frame_misc_22.pack(side='right', fill='x', expand=True)

        self.apt_label = Label(self.frame_misc_22,
                               text=_('Airport data source:'))
        ToolTip(self.apt_label, self.tooltip_aptMenu)
        self.apt_label.pack(side='left')

        self.aptMenu = OptionMenu(self.frame_misc_22, self.apt_data_source,
                                  _('Scenery'), _('Old default'))
        ToolTip(self.aptMenu, self.tooltip_aptMenu)
        self.aptMenu.pack(side='left')

        # Rebuild apt menu
        self.frame_misc_3 = Frame(self.frame_misc, borderwidth=8)
        self.frame_misc_3.pack(side='top', fill='x', expand=True)
        # Auto update apt menu
        self.frame_misc_31 = Frame(self.frame_misc_3)
        self.frame_misc_31.pack(side='top', fill='x', expand=True)

        self.auto_apt_label = Label(self.frame_misc_31,
                                    text=_('Airport database update:'))
        ToolTip(self.auto_apt_label, self.tooltip_autoAptMenu)
        self.auto_apt_label.pack(side='left')

        self.autoAptMenu = OptionMenu(self.frame_misc_31, self.auto_update_apt,
                                      _('Automatic'), _('Manual'))
        ToolTip(self.autoAptMenu, self.tooltip_autoAptMenu)
        self.autoAptMenu.pack(side='left')

        # Rebuild apt menu
        self.frame_misc_4 = Frame(self.frame_misc, borderwidth=8)
        self.frame_misc_4.pack(side='top', fill='x', expand=True)
        # Rebuild apt button
        self.frame_misc_41 = Frame(self.frame_misc_4)
        self.frame_misc_41.pack(side='top', fill='x', expand=True)

        self.rebuildApt = Button(self.frame_misc_41,
                                 text=_('Rebuild Airport Database'),
                                 command=self.config.rebuildApt)
        ToolTip(self.rebuildApt, self.tooltip_rebuildApt)
        self.rebuildApt.pack(side='top', fill='x')

        self.frame_misc_5 = Frame(self.frame_misc, borderwidth=8)
        self.frame_misc_5.pack(side='top', fill='x', expand=True)
        self.frame_misc_51 = Frame(self.frame_misc_5)
        self.frame_misc_51.pack(side='top', fill='x', expand=True)

        self.rememberMainWinPos = Checkbutton(
            self.frame_misc_51,
            text=_('Remember the main window position'),
            variable=self.config.saveWindowPosition)
        ToolTip(self.rememberMainWinPos, self.tooltip_rememberMainWinPos)
        self.rememberMainWinPos.pack(side='left', fill='x')
