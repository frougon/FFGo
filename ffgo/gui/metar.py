# -*- coding: utf-8 -*-

"""Simple widget to display METAR reports from weather.noaa.gov/."""


from math import sqrt
import socket
from urllib.request import Request, build_opener, HTTPHandler
from urllib.error import URLError
import threading
import queue as queue_mod       # keep 'queue' available for variable bindings
import functools
import traceback
from tkinter import *

from .. import constants
from ..logging import logger


socket.setdefaulttimeout(5.0)
HTTP_DEBUG_LEVEL = 0


class Metar:

    def __init__(self, app, master, config, background):
        self.app = app
        self.master = master
        self.background = background

        self.fetchUrlBase = 'http://weather.noaa.gov/'
        self.fetchUrlTemplate = (
            self.fetchUrlBase +
            'pub/data/observations/metar/{reportType}/{icao}.TXT')

        self.icao = config.airport
        self.apt_path = config.apt_path
        self.metar_path = config.metar_path

        self.decoded = IntVar()
        self.decoded.trace('w', self.onDecodedChanged)

        self.report = StringVar()
        self.report.trace('w', self._updateLabelSize)

        self.metar_list = config.readMetarDat()
        self.apt_dict = config.readCoord()

        # Lock used to prevent impatient users from making concurrent requests
        # to the site providing the METAR data, due to frenetic clicking on the
        # main label.
        self.fetchLock = threading.Lock()
        # Queue used to allow the worker thread to safely send its results to
        # the main thread.
        self.queue = queue_mod.Queue()
        # Blocking on the queue would freeze the interface; polling it would be
        # bad (waste of CPU time, poor reactivity...). So, the worker thread
        # uses a virtual event to tell the main thread when there is new data
        # in the queue. Emitting the event is known to be thread-safe, contrary
        # to most other Tkinter calls.
        self.master.bind("<<FFGoMETARQueueUpdated>>",
                         functools.partial(self._onQueueUpdated,
                                           queue=self.queue))

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

    def quit(self, event=None):
        """Destroy this window and tell the App object about it."""
        self.top.destroy()
        self.app.setMetarToNone()

    def _compare_pos(self, a, b):
        return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def onDecodedChanged(self, *args):
        self.fetch()

    def fetch(self, event=None):
        """Fetch METAR report."""
        icao = self.icao.get()
        if not icao:
            self.report.set(_('No airport is selected.'))
            return              # carrier mode

        if self._isOnMetarList(icao):
            station = icao
        else:
            station = self._nearestMetar(icao)
            if not station:
                self.report.set(_('No nearby station found.'))
                return

        # This would probably be unsafe to do in the worker thread because of
        # the 'self.decoded.get()' Tkinter call.
        reportType = 'decoded' if self.decoded.get() else 'stations'
        url = self.fetchUrlTemplate.format(reportType=reportType,
                                           icao=station.upper())
        t = threading.Thread(name="METAR_fetcher",
                             target=self._fetchThreadFunc,
                             args=(self.queue, url),
                             daemon=True)

        # Don't do anything if a request is already being processed (user too
        # impatient!)
        if self.fetchLock.acquire(blocking=False):
            try:
                t.start()
            except BaseException:
                logger.errorNP(traceback.format_exc())
                self.fetchLock.release()
                raise

            self.report.set(_('Fetching report from {site}...').format(
                site=self.fetchUrlBase))

    def _doFetch(self, url):
        """Fetch METAR report.

        Beware: this method may be run from a thread that is *not* the
        main thread.

        """
        try:
            try:
                request = Request(url)
                request.add_header('User-Agent', constants.USER_AGENT)
                opener = build_opener(HTTPHandler(debuglevel=HTTP_DEBUG_LEVEL))
                with opener.open(request) as sock:
                    report = sock.read()
            except (socket.timeout, URLError):
                logger.errorNP(traceback.format_exc())
                report = _('Unable to download data.')
            else:
                report = report.decode('ascii').strip()
        except BaseException as e: # catch *all* exceptions
            logger.errorNP(traceback.format_exc())
            report = str(e)

        return report

    def _fetchThreadFunc(self, queue, url):
        # Thread function → no GUI calls allowed here!
        try:
            report = self._doFetch(url)
            queue.put(report)
        except BaseException:
            logger.errorNP(traceback.format_exc())
            self.fetchLock.release()

        try:
            # This particular method, when passed 'when="tail"', is supposed to
            # be safe to call from other threads than the Tk GUI thread
            # (cf. <http://stackoverflow.com/questions/7141509/tkinter-wait-for-item-in-queue#comment34432041_14809246>
            # and
            # <https://mail.python.org/pipermail/tkinter-discuss/2013-November/003519.html>).
            # Other Tk functions are usually considered unsafe to call from
            # these other threads.
            self.master.event_generate("<<FFGoMETARQueueUpdated>>",
                                       when="tail")
        # In case Tk is not here anymore
        except TclError:
            logger.errorNP(traceback.format_exc())
            return

    def _onQueueUpdated(self, event, queue=None):
        # The caller must pass a real queue object, not None.
        try:
            report = None
            while True:         # Pop all elements present in the queue
                try:
                    # Only use the last report stored in the queue
                    report = queue.get_nowait()
                except queue_mod.Empty:
                    break

            if report is not None:
                self.report.set(report)
        finally:
            self.fetchLock.release()

    def _isOnMetarList(self, icao):
        """Return True if selected airport is on METAR station list."""
        return icao in self.metar_list

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
            except KeyError:
                continue

            distance = self._compare_pos(airport_pos, metar_pos)
            if distance < nearest_dist:
                nearest_metar = icao
                nearest_dist = distance

        return nearest_metar

    # Accept any arguments to allow safe use as a Tkinter variable observer
    def _updateLabelSize(self, *args):
        """Adjust label dimensions according to text size."""
        report = self.report.get().splitlines()
        width = max(len(n) for n in report)
        height = len(report) + 2
        self.text.configure(width=width, height=height)

    def _welcomeMessage(self):
        """Show message at widget's initialization"""
        message = _('Click here to download the METAR report\n'
                    'for the selected (or nearest) airport.')
        self.report.set(message)
