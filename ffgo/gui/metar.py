"""Simple widget to display METAR reports from weather.noaa.gov/."""


from math import sqrt
from socket import setdefaulttimeout, timeout
from urllib.request import Request, build_opener, HTTPHandler
from urllib.error import URLError
from _thread import start_new_thread
from tkinter import *

from ..constants import USER_AGENT


setdefaulttimeout(5.0)


DEBUG_LEVEL = 0


class Metar:

    def __init__(self, master, config, background):
        self.master = master
        self.background = background

        self.icao = config.airport
        self.apt_path = config.apt_path
        self.metar_path = config.metar_path

        self.decoded = IntVar()
        self.nearest_station = StringVar()
        self.report = StringVar()

        self.decoded.set(0)
        self.nearest_station.set('')
        self.report.set('')

        self.metar_list = config.readMetarDat()
        self.apt_dict = config.readCoord()

#------- Main Window ----------------------------------------------------------
        self.top = Toplevel(self.master, borderwidth=4)
        self.top.transient(self.master)
        self.top.resizable(width=False, height=False)
        # Override window close button.
        self.top.protocol("WM_DELETE_WINDOW", self.quit)
        self.top.title('METAR')
        self.top.bind('<Escape>', self.quit)

        self.frame1 = Frame(self.top)
        self.frame1.pack(side='top', fill='x')
#------ Decoded check button --------------------------------------------------
        self.decoded_cb = Checkbutton(self.frame1, text=_('Decoded'),
                                      variable=self.decoded)
        self.decoded_cb.pack(side='left')

        self.frame2 = Frame(self.top, borderwidth=2, relief='sunken')
        self.frame2.pack(side='top')
#------ Report window ---------------------------------------------------------
        self.text = Label(self.frame2, width=0, height=0, bg=self.background,
                          textvariable=self.report)
        self.text.pack(side='top')
        self.text.bind('<Button-1>', self.fetch)
#------------------------------------------------------------------------------
        self._welcomeMessage()

    def fetch(self, event=None):
        """Fetch METAR report."""
        self.text.unbind('<Button-1>')
        self.report.set(_('Fetching report...'))
        # Wait until text is updated.
        self.master.update()
        start_new_thread(self._fetch, ())

    def quit(self, event=None):
        """Clean up data and destroy this window."""
        del self.metar_list
        del self.apt_path
        del self.metar_path
        del self.icao
        del self.master
        del self.background
        del self.apt_dict

        self.top.destroy()

    def _bindButton(self):
        try:
            self.text.bind('<Button-1>', self.fetch)
        except TclError:
            return

    def _compare_pos(self, a, b):
        return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def _fetch(self):
        """Fetch METAR report."""
        icao = self._getIcao()
        if icao == 'None':
            return

        self.nearest_station.set('')
        if self._isOnMetarList(icao):
            decoded = self._getDecoded()
            url = \
                ('http://weather.noaa.gov/pub/data/observations/metar/%s/%s.TXT' %
                 (decoded, icao))
            try:
                request = Request(url)
                request.add_header('User-Agent', USER_AGENT)
                opener = build_opener(HTTPHandler(debuglevel=DEBUG_LEVEL))
                report = opener.open(request).read()
                report = report.decode('ascii')
                report = report.strip()
            except timeout:
                report = _('Unable to download data.')
            except URLError:
                report = _('Unable to download data.')
            self.report.set(report)
            self._setLabelSize()
        else:
            self.nearest_station.set(self._nearestMetar(icao))
            self.fetch()
        # Bind button to text widget after some delay to avoid double clicking.
        self.master.after(1000, self._bindButton)

    def _getIcao(self):
        if self.nearest_station.get() and \
           self.nearest_station.get() == self._nearestMetar(self.icao.get()):
            return self.nearest_station.get()
        else:
            return self.icao.get()

    def _getDecoded(self):
        if self.decoded.get():
            return 'decoded'
        else:
            return 'stations'

    def _isOnMetarList(self, icao):
        """Return True if selected airport is on METAR station list."""
        if icao in self.metar_list:
            return True

    def _nearestMetar(self, icao):
        """Find nearest METAR station"""
        nearest_metar = ''
        nearest_dist = 999
        try:
            airport_pos = self.apt_dict[icao]
        except KeyError:
            return ''
        for icao in self.metar_list:
            try:
                metar_pos = self.apt_dict[icao]
                distance = self._compare_pos(airport_pos, metar_pos)
                if distance < nearest_dist:
                    nearest_metar = icao
                    nearest_dist = distance
            except KeyError:
                pass
        return nearest_metar

    def _setLabelSize(self):
        """Adjust label dimensions according to text size."""
        report = self.report.get()
        report = report.splitlines()
        width = max(len(n) for n in report)
        height = len(report) + 2
        try:
            self.text.configure(width=width, height=height)
        except TclError:
            pass

    def _welcomeMessage(self):
        """Show message at widget's initialization"""
        # Disable widget in case of IOError.
        if self.metar_list[0] == 'IOError':
            self.text.unbind('<Button-1>')
            message = ' ' * 30
        else:
            message = _('Click here to download the METAR report\n'
                        'for selected (or nearest) airport.')

        self.report.set(message)
        self._setLabelSize()
