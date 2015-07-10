"""Application main window."""


import os
import sys
import subprocess
import threading
import socket
import re
import functools
import operator
from gettext import translation
import threading
import queue as queue_mod       # keep 'queue' available for variable bindings
from tkinter import *
import tkinter.filedialog as fd
from tkinter.scrolledtext import ScrolledText
from xml.etree.ElementTree import ElementTree
from tkinter.messagebox import showerror

try:
    from PIL import Image, ImageTk
    PIL = True
except ImportError:
    PIL = False
    print ('[FGo! Warning] PIL library not found. Aircraft thumbnails '
           'will not be displayed.', file=sys.stderr)

import condconfigparser
print("Using CondConfigParser version {}".format(condconfigparser.__version__))

from .metar import Metar
from .configwindow import ConfigWindow
from ..constants import *


class App:

    def __init__(self, master, config):
        self.master = master
        self.config = config

        self.translatedPark = StringVar()
        self.translatedRwy = StringVar()
        self.options = StringVar()
        self.translatedPark.set(_('None'))
        self.translatedRwy.set(_('Default'))
        self.options.set('')
#------ Menu ------------------------------------------------------------------
        self.menubar = Menu(self.master)

        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label=_('Load'), command=self.configLoad)
        self.filemenu.add_command(label=_('Save as...'),
                                  command=self.configSave)
        self.filemenu.add_separator()
        self.filemenu.add_command(label=_('Save & Quit (Ctrl-Q)'),
                                  command=self.saveAndQuit)
        self.filemenu.add_command(label=_('Quit'), command=self.quit)
        self.menubar.add_cascade(label=_('File'), menu=self.filemenu)

        self.settmenu = Menu(self.menubar, tearoff=0)
        self.settmenu.add_checkbutton(label=_('Show installed airports only'),
                                      variable=self.config.filtredAptList,
                                      command=self.filterAirports)
        self.settmenu.add_command(label=_('Update list of installed airports'),
                                  command=self.updateInstalledAptList)
        self.settmenu.add_separator()
        self.settmenu.add_command(label=_('Preferences'),
                                  command=self.showConfigWindow)
        self.menubar.add_cascade(label=_('Settings'), menu=self.settmenu)

        self.toolsmenu = Menu(self.menubar, tearoff=0)
        self.toolsmenu.add_command(label='METAR',
                                   command=self.showMETARWindow)
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
        self.aircraftList.see(self.getIndex('a'))
        self.aircraftList.bind('<Button-1>', self.focusAircraftList)

        self.frame12 = Frame(self.frame1, borderwidth=1)
        self.frame12.pack(side='top', fill='x')

        self.aircraftSearch = Entry(self.frame12, bg=TEXT_BG_COL)
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

        self.airportSearch = Entry(self.frame32, bg=TEXT_BG_COL)
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
        self.frame41.pack(side='right')

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

        self.reset_button = Button(self.frame41, text=_('Reset'), width=10,
                                   command=self.reset)
        self.reset_button.pack(side='left')

        self.run_button = Button(self.frame41, text=_('Run FG'), width=10,
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
        self.option_window = Text(self.frame51, bg=TEXT_BG_COL, wrap='none',
                                  yscrollcommand=option_window_sv.set,
                                  xscrollcommand=option_window_sh.set)
        option_window_sv.config(command=self.option_window.yview, takefocus=0)
        option_window_sh.config(command=self.option_window.xview, takefocus=0)
        self.option_window.bind('<<Modified>>', self.updateOptions)
        option_window_sh.pack(side='bottom', fill='x')
        self.option_window.pack(side='left', fill='both', expand=True)
        option_window_sv.pack(side='left', fill='y')
        # Elements of 52-th frame are defined in reverse order to make sure
        # that bottom buttons are always visible when resizing.
        self.frame52 = Frame(self.frame5top)
        self.frame52.pack(side='left', fill='both', expand=True)

        self.frame521 = Frame(self.frame52)
        self.frame521.pack(side='bottom', fill='y')

        self.save_output_button = Button(self.frame521, text=_('Save Log'),
                                         command=self.saveLog)
        self.save_output_button.pack(side='left')

        self.open_log_dir_button = Button(self.frame521,
                                          text=_('Open Log Directory'),
                                          command=self.openLogDir)
        self.open_log_dir_button.pack(side='left')

        self.frame522 = Frame(self.frame52)
        self.frame522.pack(side='bottom', fill='both', expand=True)

        output_window_sv = Scrollbar(self.frame522, orient='vertical')
        output_window_sh = Scrollbar(self.frame522, orient='horizontal')
        self.output_window = Text(self.frame522, foreground=COMMENT_COL,
                                  bg=MESSAGE_BG_COL, wrap='none',
                                  yscrollcommand=output_window_sv.set,
                                  xscrollcommand=output_window_sh.set,
                                  state='disabled')
        output_window_sv.config(command=self.output_window.yview, takefocus=0)
        output_window_sh.config(command=self.output_window.xview, takefocus=0)
        output_window_sh.pack(side='bottom', fill='x')
        self.output_window.pack(side='left', fill='both', expand=True)
        output_window_sv.pack(side='left', fill='y')

        self.frame5bottom = Frame(self.frame5, relief='groove', borderwidth=2)
        self.frame5bottom.pack(side='top', fill='x')

        command_window_label = Label(self.frame5bottom,
                   text=_('FlightGear will be started with following options:'))
        command_window_label.pack(side='top', fill='y', anchor='nw')

        self.frame53 = Frame(self.frame5bottom)
        self.frame53.pack(side='bottom', fill='x', expand=True)

        command_window_sv = Scrollbar(self.frame53, orient='vertical')
        command_window_sh = Scrollbar(self.frame53, orient='horizontal')
        self.command_window = Text(self.frame53, wrap='none', height=10,
                                   relief='flat', bg=GRAYED_OUT_COL,
                                   yscrollcommand=command_window_sv.set,
                                   xscrollcommand=command_window_sh.set,
                                   state='disabled')
        command_window_sv.config(command=self.command_window.yview, takefocus=0)
        command_window_sh.config(command=self.command_window.xview, takefocus=0)
        command_window_sh.pack(side='bottom', fill='x')
        self.command_window.pack(side='left', fill='x', expand=True)
        command_window_sv.pack(side='left', fill='y')

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
        self.reset(first_run=True)
        self.registerTracedVariables()
        # Lock used to prevent concurent calls of self._runFG()
        # (disabling the "Run FG" button is not enough, as self.runFG()
        # can be invoked through a keyboard shortcut).
        self.runFGLock = threading.Lock()
        self.setupKeyboardShortcuts()
        self.startLoops()

    def setupKeyboardShortcuts(self):
        self.master.bind('<Control-KeyPress-f>', self.runFG)
        self.master.bind('<Control-KeyPress-r>', self.reset)
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
        about_text = '{0}\n\n{1}\n{2}{3}'.format(COPYRIGHT, authors, AUTHORS,
                                                 translator)

        self.aboutWindow = Toplevel(borderwidth=4)
        self.aboutWindow.title(_('About'))
        self.aboutWindow.resizable(width=False, height=False)
        self.aboutWindow.transient(self.master)
        self.aboutWindow.bind('<Escape>', self._destroyAboutWindow)

        self.aboutTitle = Label(self.aboutWindow,
                                font=self.config.aboutTitleFont, text=NAME)
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
        if self.aircraftList:
            self.aircraftList.delete(0, 'end')

        for i in self.config.aircraft_list:
            self.aircraftList.insert('end', i)

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
        p = fd.askopenfilename(initialdir=USER_DATA_DIR,
                               filetypes=[(_('Config Files'), '*.fgo')])
        if p:
            self.reset(path=p)

    def configSave(self):
        asf = fd.asksaveasfilename
        p = asf(initialdir=USER_DATA_DIR,
                filetypes=[(_('Config Files'), '*.fgo')])
        if p:
            try:
                if p[-4:] != '.fgo':
                    p += '.fgo'
            except TypeError:
                pass
            t = self.options.get()
            self.config.write(text=t, path=p)

    def filterAirports(self):
        """Update airportList.

        Apply filter to airportList if self.config.filtredAptList is True.

        """
        self.config.updateAptLists()
        self.buildAirportList()
        self.airportList.see(self.getIndex('p'))
        self.airportList.select_set(self.getIndex('p'))

    def focusAircraftList(self, event=None):
        self.aircraftList.focus_set()

    def focusAirportList(self, event=None):
        self.airportList.focus_set()

    def getAircraft(self):
        """Get aircraftList current selection and return aircraft name."""
        index = self.aircraftList.curselection()
        if index:
            return self.aircraftList.get(index)

        aircraft = self.aircraftList.get(ACTIVE)
        if not aircraft:
            aircraft = 'None'
        return aircraft

    def getAirport(self):
        """Get airportList current selection and return airport ICAO."""
        index = self.airportList.curselection()
        if index:
            return self.airportList.get(index).split()[0]
        try:
            return self.airportList.get(ACTIVE).split()[0]
        except IndexError:
            return self.config.airport.get()

    def getImage(self):
        """Find thumbnail in aircraft directory."""
        if PIL:
            try:
                name = self.config.aircraft.get()
                index = self.config.aircraft_list.index(name)
                path = os.path.join(self.config.aircraft_path[index],
                                    'thumbnail.jpg')
                image = ImageTk.PhotoImage(Image.open(path))
            except:
                image = ImageTk.PhotoImage(Image.open(NO_THUMBNAIL_PIC))
        else:
            image = PhotoImage(file=NO_PIL_PIC)

        return image

    def getIndex(self, type_):
        """Get aircraft name ('a') or airport ICAO ('p')
        and return its index."""
        if type_ == 'a':
            name = self.config.aircraft.get()
            try:
                return self.config.aircraft_list.index(name)
            except ValueError:
                try:
                    return self.config.aircraft_list.index(DEFAULT_AIRCRAFT)
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

    def openLogDir(self):
        command = 'exo-open --launch FileManager'
        c = command.split()
        subprocess.Popen(c+[LOG_DIR])

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

    def popupPark(self, event):
        """Make pop up menu."""
        # Take focus out of search entry to stop search loop.
        self.master.focus()
        popup = Menu(tearoff=0)
        if self.config.airport.get() != 'None':
            popup.add_command(label=_('None'),
                              command=lambda: self.config.park.set('None'))
            count = 1
            for i in self.read_airport_data(self.config.airport.get(), 'park'):
                #  Cut menu
                if count % 20:
                    popup.add_command(label=i,
                                    command=lambda i=i: self.config.park.set(i))
                else:
                    popup.add_command(label=i,
                                    command=lambda i=i: self.config.park.set(i),
                                    columnbreak=1)
                count += 1
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
            for i in self.read_airport_data(self.config.airport.get(), 'rwy'):
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

    def read_airport_data(self, icao, type_):
        """Get runway or parking names.

        type_ should be: 'rwy' or 'park'

        """
        res = []
        if type_ == 'rwy':
            path = os.path.join(self.config.ai_path, DEFAULT_AIRPORTS_DIR)
            if os.path.exists(path):
                # Runway
                if type_ == 'rwy':
                    index = self.getIndex('p')
                    rwy = self.config.airport_rwy[index]
                    for i in rwy:
                        res.append(i)
        else:
            # If airport data source is set to: From scenery...
            if self.config.apt_data_source.get():
                paths = []
                L = self.config.FG_scenery.get().split(':')
                for path in L:
                    paths.append(os.path.join(path, DEFAULT_AIRPORTS_DIR))

                for path in paths:
                    for i in range(3):
                        path = os.path.join(path, icao[i])
                    if os.path.exists(path):
                        files = os.listdir(path)
                        parking = '.'.join([icao, 'parking.xml'])
                        groundnet = '.'.join([icao, 'groundnet.xml'])
                        for f in files:
                            file_path = os.path.join(path, f)
                            if f == parking or f == groundnet and not res:
                                res = self.read_parking(file_path)
            # If airport data source is set to: Standard...
            else:
                path = os.path.join(self.config.ai_path, DEFAULT_AIRPORTS_DIR)
                if os.path.exists(path):
                    dirs = os.listdir(path)
                    if icao in dirs:
                        path = os.path.join(path, icao)
                        file_path = os.path.join(path, 'parking.xml')
                        if os.path.exists(file_path):
                            res = self.read_parking(file_path)

        return res

    def read_parking(self, xml_file):
        """Read parking positions from XML file."""
        res = []
        with open(xml_file) as xml:
            root = self._get_root(xml)
            parking_list = root.find('parkingList')
            if parking_list is None:
                parking_list = root.find('parkinglist')
            parkings = parking_list.findall('Parking')
            for p in parkings:
                name = p.get('name').split('"')[0]
                number = p.get('number').split('"')[0]
                res.append(''.join((name, number)))
        res = list(set(res))  # Remove doubles
        res.sort()
        return res

    def read_scenario(self, scenario):
        """Read description from a scenario."""
        text = ''
        file_name = scenario + '.xml'
        path = os.path.join(self.config.ai_path, file_name)
        with open(path) as xml:
            root = self._get_root(xml)
            # There is no consistency along scenario files where
            # the <description> tag can be found in the root tree,
            # therefore we are making a list of all occurrences
            # of the tag and return the first element (if any).
            descriptions = root.findall('.//description')
            if descriptions:
                text = self._rstrip_text_block(descriptions[0].text)
        return text

    def _get_root(self, xml):
        tree = ElementTree()
        tree.parse(xml)
        return tree.getroot()

    def _rstrip_text_block(self, text):
        rstripped_text = '\n'.join(line.lstrip() for line in text.splitlines())
        return rstripped_text

    def registerTracedVariables(self):
        self.options.trace('w', self.updateCommand)
        self.config.aircraft.trace('w', self.updateCommand)
        self.config.airport.trace('w', self.updateCommand)
        self.config.scenario.trace('w', self.updateCommand)
        self.config.carrier.trace('w', self.updateCommand)
        self.config.FG_root.trace('w', self.updateCommand)
        self.config.FG_scenery.trace('w', self.updateCommand)
        self.config.park.trace('w', self.updateCommand)
        self.config.rwy.trace('w', self.updateCommand)

    def reset(self, event=None, path=None, first_run=False):
        """Reset data"""
        # Don't call config.update() at application initialization
        # as config object is updated at its creation anyway.
        if not first_run:
            self.config.update(path)
        self.aircraftSearch.delete(0, 'end')
        self.airportSearch.delete(0, 'end')
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
        self.updateCommand()

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

    _rawCfgLineComment_cre = re.compile(r"[ \t]*#")

    def processRawConfigLines(self, rawConfigLines):
        r"""Handle backslash escape sequences and remove comments in fgfs opts.

        Comments start with '#' and end at the end of the line. Spaces
        and tabs right before a comment are ignored (except if a space
        is part of a \<space> escape sequence).

        Outside comments, the following escape sequences are recognized
        (the expansion of each escape sequence is given in the second
        column):

          \\          \ (produces a single backslash)
          \[          [ (useful at the beginning of a line to avoid
                         confusion with the start of a predicate)
          \]          ] (for symmetry with '\[')
          \#          # (literal '#' character, doesn't start a comment)
          \t          tab character
          \n          newline character (doesn't start a new option)
          \<space>    space character (useful to include a space at the
                      end of an option, which would be ignored without
                      the backslash)
          \<newline>  continuation line (i.e., make as if the next line
                      were really the continuation of the current line,
                      with the \<newline> escape sequence removed)

        """
        res = []                # list of strings: the output lines
        # After escape sequences processing: stores the characters forming each
        # output line as it is being constructed from one or more input lines
        # (continuation lines are started with a backslash at the end of the
        # previous input line)
        chars = []
        # i: input line number; j: column number in this line
        i = j = 0

        while i < len(rawConfigLines):
            if j >= len(rawConfigLines[i]):
                res.append(''.join(chars)) # finish the output line
                del chars[:]
                i += 1          # next input line
                j = 0
                continue

            mo = self._rawCfgLineComment_cre.match(
                rawConfigLines[i][j:])
            if mo:
                res.append(''.join(chars)) # finish the output line
                del chars[:]
                i += 1          # next input line
                j = 0
                continue

            c = rawConfigLines[i][j]

            if c == "\\":
                if j + 1 == len(rawConfigLines[i]): # end of input line
                    if i + 1 == len(rawConfigLines):
                        res.append(''.join(chars)) # finish the output line
                    else:
                        j = -1  # continuation line

                    i += 1      # next input line
                else:
                    j += 1      # next char of input line
                    c = rawConfigLines[i][j]

                    if c == "\\":
                        chars.append("\\")
                    elif c == "n":
                        chars.append("\n")
                    elif c == "t":
                        chars.append("\t")
                    elif c == '#':
                        chars.append('#')
                    elif c == ' ':
                        chars.append(' ')
                    elif c == '[':
                        chars.append('[')
                    elif c == ']':
                        chars.append(']')
                    else:
                        title = _('Error in configuration file!')
                        msg = _('Invalid escape sequence in option line: '
                                '\\{}').format(c)
                        message = '{0}\n\n{1}'.format(title, msg)
                        self.error_message = showerror(_('Error'), message)
            elif c == '#':
                assert False, "Comment char # should have been handled " \
                    "earlier (by regexp)"
            else:
                chars.append(c)

            j += 1              # next input char

        return res

    def mergeFGOptions(self, mergedOptions, optionList):
        """Merge identical options in 'optionList'.

        Return a new list containing all options from 'optionList',
        except that the elements of 'optionList' that start with an
        element of 'mergedOptions' are merged together.

        More precisely, for a given element e (a string) of
        'mergedOptions', the first element of 'optionList' that starts
        with e is replaced by the last element of 'optionList' that
        starts with e and all other such elements of 'optionList' are
        omitted from the result. In other words, the last element of
        'optionList' that starts with e "wins", replaces the first one,
        and other occurrences are ignored.

        """
        d = {}
        l = []

        for opt in optionList:
            for prefix in mergedOptions:
                if opt.startswith(prefix):
                    if prefix not in d: # first time we encounter this prefix?
                        l.append( (False, prefix) )
                    d[prefix] = opt # overwrites previous ones
                    break
            else:
                l.append( (True, opt) )  # non-merged option

        # If isOpt is False, s is a prefix and d[s] the last element of
        # optionList starting with that prefix.
        return [ s if isOpt else d[s] for isOpt, s in l ]

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
            self.error_message = showerror(_('FGo!'), message)

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
        options = []
        FG_working_dir = HOME_DIR

        with open(CONFIG, mode='r', encoding='utf-8') as config_in:
            # Parse config file.
            for line in config_in:
                line = line.strip()
                if line == CUT_LINE:
                    # Options after CUT_LINE are handled by CondConfigParser
                    break

                if line.startswith('--'):
                    options.append(line)

                if line.startswith('AI_SCENARIOS='):
                    L = line[13:].split()
                    for scenario in L:
                        options.append('--ai-scenario=' + scenario)
                elif line.startswith('FG_AIRCRAFT='):
                    L = line[12:].split(':')
                    for dir_ in L:
                        if dir_:
                            options.append('--fg-aircraft=' + dir_)
                elif line[:15] == 'FG_WORKING_DIR=':
                    if os.path.exists(line[15:]):
                        FG_working_dir = line[15:]
                elif line[:7] == 'FG_BIN=':
                    program = line[7:]

        try:
            condConfig = condconfigparser.RawConditionalConfig(
                t, extvars=("aircraft", "airport", "parking", "runway",
                            "carrier", "scenarios"))
            context = {"aircraft": self.config.aircraft.get(),
                       "airport": self.config.airport.get(),
                       "parking": self.config.park.get(),
                       "runway": self.config.rwy.get(),
                       "carrier": self.config.carrier.get(),
                       "scenarios": self.config.scenario.get().split()}

            # configVars:
            #   external and non-external (assigned in the cfg file) variables
            #
            # rawConfigSections:
            #   list of lists of strings which are fgfs options. The first list
            #   corresponds to the "default", unconditional section of the
            #   config file; the other lists come from the conditional sections
            #   whose predicate is true according to 'context'.
            configVars, rawConfigSections = condConfig.eval(context)
            optionLineGroups = [ self.processRawConfigLines(lines) for lines in
                                 rawConfigSections ]
            # Concatenate all lists together
            additionalLines = functools.reduce(operator.add, optionLineGroups,
                                               [])
            options.extend(additionalLines)

            # Merge options starting with an element of MERGED_OPTIONS
            # The default for MERGED_OPTIONS is the empty list.
            mergedOptions = configVars.get("MERGED_OPTIONS", [])
            options = self.mergeFGOptions(mergedOptions, options)
        except condconfigparser.error as e:
            title = _('Error in configuration file!')
            msg = _('Error: {}').format(e) # str(e) not translated...
            message = '{0}\n\n{1}'.format(title, msg)
            self.error_message = showerror(_('Error'), message)
            return False

        print('\n' + '=' * 80 + '\n')
        print(_('Starting %s with following options:') % program)

        for i in options:
            print('\t%s' % i)
        print('\n' + '-' * 80 + '\n')

        try:
            process = subprocess.Popen([program] + options,
                                       cwd=FG_working_dir,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       universal_newlines=True,
                                       bufsize=1) # Use line buffering
        except OSError as e:
            self.runFGErrorMessage(e)
            return False

        self.stopLoops()
        self.output_window.config(state='normal')
        self.output_window.delete('1.0', 'end')
        self.output_window.config(state='disabled')

        # One queue for fgfs' stdout and stderr, the other for its exit
        # status (or killing signal)
        outputQueue, statusQueue = queue_mod.Queue(), queue_mod.Queue()

        self.master.bind("<<FGoNewFgfsOutputQueued>>",
                         functools.partial(self._updateFgfsProcessOutput,
                                           queue=outputQueue))
        self.master.bind("<<FGoFgfsProcessTerminated>>",
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
            print(line, end='')
            outputQueue.put(line)
            try:
                self.master.event_generate("<<FGoNewFgfsOutputQueued>>",
                                           when="tail")
                # In case Tk is not here anymore
            except TclError:
                return

        exitStatus = process.wait()
        # FlightGear is terminated and all its output has been read
        statusQueue.put(exitStatus)
        try:
            self.master.event_generate("<<FGoFgfsProcessTerminated>>",
                                       when="tail")
        except TclError:
            return

    def _updateFgfsProcessOutput(self, event, queue=None):
        self.output_window.config(state='normal')
        while True:             # Pop all elements present in the queue
            try:
                line = queue.get_nowait()
            except queue_mod.Empty:
                break

            self.output_window.insert('end', line)

        self.output_window.config(state='disabled')
        self.output_window.see('end')

    def _onFgfsProcessTerminated(self, event, queue=None):
        # There should be exactly one item in the queue now. Get it.
        exitStatus = queue.get()
        if exitStatus >= 0:
            complement = _("FG's last exit status: {0}").format(exitStatus)
            shortComplement = _("exit status: {0}").format(exitStatus)
        else:
            complement = _("FG last killed by signal {0}").format(-exitStatus)
            shortComplement = _("killed by signal {0}").format(-exitStatus)

        print("fgfs process terminated ({0})".format(shortComplement))

        self.fgStatusText.set(_('Ready ({0})').format(complement))
        self.fgStatusLabel.config(background="#88ff88")
        self.run_button.configure(state='normal')
        self.startLoops()
        self.runFGLock.release()

    def saveAndQuit(self, event=None):
        """Save options to file and quit."""
        # Save window resolution.
        geometry = self.master.geometry().split('+')[0]
        self.config.window_geometry.set(geometry)

        t = self.options.get()
        self.config.write(text=t)
        self.master.quit()

    def saveLog(self):
        p = fd.asksaveasfilename(initialdir=LOG_DIR,
                                 initialfile=DEFAULT_LOG_NAME)
        if p:
            with open(p, mode='w', encoding='utf-8') as logfile:
                text = self.output_window.get('0.0', 'end')
                # Cutoff trailing new line that Tk always adds at the end.
                if text.endswith('\n'):
                    text = text[:-1]
                logfile.write(text)

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

    def searchAircrafts(self):
        entry = self.aircraftSearch.get()
        list_ = self.aircraftList
        build_method = self.buildAircraftList

        self.search(entry, list_, build_method)

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
        path = os.path.join(HELP_DIR, 'help_' + lang_code)
        if not os.path.isfile(path):
            lang_code = 'en'
            path = os.path.join(HELP_DIR, 'help_' + lang_code)

        readme_in = open(path, encoding='utf-8')
        text = readme_in.read()
        readme_in.close()

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

        if now != self.config.aircraft.get():
            self.config.aircraft.set(now)
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

    def updateCommand(self, *args):
        t = self.options.get()
        options = self._getOptions()

        try:
            condConfig = condconfigparser.RawConditionalConfig(
                t, extvars=("aircraft", "airport", "parking", "runway",
                            "carrier", "scenarios"))
            context = {"aircraft": self.config.aircraft.get(),
                       "airport": self.config.airport.get(),
                       "parking": self.config.park.get(),
                       "runway": self.config.rwy.get(),
                       "carrier": self.config.carrier.get(),
                       "scenarios": self.config.scenario.get().split()}

            # configVars:
            #   external and non-external (assigned in the cfg file) variables
            #
            # rawConfigSections:
            #   list of lists of strings which are fgfs options. The first list
            #   corresponds to the "default", unconditional section of the
            #   config file; the other lists come from the conditional sections
            #   whose predicate is true according to 'context'.
            configVars, rawConfigSections = condConfig.eval(context)
            optionLineGroups = [ self.processRawConfigLines(lines) for lines in
                                 rawConfigSections ]
            # Concatenate all lists together
            additionalLines = functools.reduce(operator.add, optionLineGroups,
                                               [])
            options.extend(additionalLines)

            # Merge options starting with an element of MERGED_OPTIONS
            # The default for MERGED_OPTIONS is the empty list.
            mergedOptions = configVars.get("MERGED_OPTIONS", [])
            options = self.mergeFGOptions(mergedOptions, options)
            options = '\n'.join(options)

            self.command_window.config(state='normal')
            self.command_window.delete('1.0', 'end')
            self.command_window.insert('end', options)
            self.command_window.config(state='disabled')
        except condconfigparser.error as e:
            title = _('Error in configuration file!')
            msg = _('Error: {}').format(e) # str(e) not translated...
            message = '{0}\n\n{1}'.format(title, msg)
            self.error_message = showerror(_('Error'), message)
            return

    def _getOptions(self):
        options = []
        options.append('--fg-root=' + self.config.FG_root.get())
        options.append('--aircraft=' + self.config.aircraft.get())
        if self.config.carrier.get() != 'None':
            options.append('--carrier=' + self.config.carrier.get())
        if self.config.airport.get() != 'None':
            options.append('--airport=' + self.config.airport.get())
        if self.config.park.get() != 'None':
            options.append('--parkpos=' + self.config.park.get())
        if self.config.rwy.get() != 'Default':
            options.append('--runway=' + self.config.rwy.get())
        if self.config.scenario.get() != '':
            options.append('--ai-scenario=' + self.config.scenario.get())
        if self.config.FG_aircraft.get() != '':
            options.append('--fg-aircraft=' + self.config.FG_aircraft.get())
        if self.config.FG_scenery.get() != 'None':
            options.append('--fg-scenery=' + self.config.FG_scenery.get())
        return options

    def updateImage(self):
        self.image = self.getImage()
        self.thumbnail.config(image=self.image)

    def updateInstalledAptList(self):
        """Rebuild installed airports list."""
        if self.config.filtredAptList.get():
            self.config.makeInstalledAptList()
            self.filterAirports()

    def updateOptions(self, event=None):
        self.options.set(self.option_window.get('1.0', 'end'))
        self.option_window.edit_modified(False)
