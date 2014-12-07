"""This module process data from ~/.fgo folder."""

import sys
import os
import gzip
import gettext
import traceback
from xml.etree.ElementTree import ElementTree
from tkinter import IntVar, StringVar
from tkinter.messagebox import showerror
import tkinter.font

from .gui.infowindow import InfoWindow
from .constants import *


class Config:

    """Read/write and store all data from config files."""

    def __init__(self, master=None):
        self.master = master

        self.ai_path = ''  # Path to FG_ROOT/AI directory.
        self.apt_path = ''  # Path to FG_ROOT/Airports/apt.dat.gz file.
        self.default_aircraft_dir = ''  # Path to FG_ROOT/Aircraft directory.
        self.metar_path = ''  # Path to FG_ROOT/Airports/metar.dat.gz file.

        self.aircraft_dirs = []  # List of aircraft directories.
        self.aircraft_list = []  # List of aircraft names.
        self.aircraft_path = []  # List of paths to each aircraft.
        self.airport_icao = []  # List of ICAO codes for each airport.
        self.airport_name = []  # List of airport names.
        self.airport_rwy = []  # List of runways present in each airport.

        self.scenario_list = []  # List of selected scenarios.
        # List of all aircraft carriers found in AI scenario folder.
        # Each entry format is:
        # ["ship name", "parking position"... , "scenario name"]
        self.carrier_list = []

        self.settings = []  # List of basic settings read from config file.
        self.text = ''  # String to be shown in command line options window.

        self.aircraft = StringVar()
        self.airport = StringVar()
        self.apt_data_source = IntVar()
        self.auto_update_apt = IntVar()
        self.carrier = StringVar()
        self.FG_aircraft = StringVar()
        self.FG_bin = StringVar()
        self.FG_root = StringVar()
        self.FG_scenery = StringVar()
        self.FG_working_dir = StringVar()
        self.filtredAptList = IntVar()
        self.language = StringVar()
        self.park = StringVar()
        self.rwy = StringVar()
        self.scenario = StringVar()
        self.TS = IntVar()
        self.TS_bin = StringVar()
        self.TS_port = StringVar()
        self.TS_scenery = StringVar()
        self.window_geometry = StringVar()
        self.baseFontSize = StringVar()
        self.TkDefaultFontSize = IntVar()

        self.keywords = {'--aircraft=': self.aircraft,
                         '--airport=': self.airport,
                         '--fg-root=': self.FG_root,
                         '--fg-scenery=': self.FG_scenery,
                         '--carrier=': self.carrier,
                         '--parkpos=': self.park,
                         '--runway=': self.rwy,
                         'AI_SCENARIOS=': self.scenario,
                         'APT_DATA_SOURCE=': self.apt_data_source,
                         'AUTO_UPDATE_APT=': self.auto_update_apt,
                         'FG_BIN=': self.FG_bin,
                         'FG_AIRCRAFT=': self.FG_aircraft,
                         'FG_WORKING_DIR=': self.FG_working_dir,
                         'FILTER_APT_LIST=': self.filtredAptList,
                         'LANG=': self.language,
                         'TERRASYNC=': self.TS,
                         'TERRASYNC_BIN=': self.TS_bin,
                         'TERRASYNC_PORT=': self.TS_port,
                         'TERRASYNC_SCENERY=': self.TS_scenery,
                         'WINDOW_GEOMETRY=': self.window_geometry,
                         'BASE_FONT_SIZE=': self.baseFontSize}

        self._createConfDirectory()
        self.update(first_run=True)

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
        airports = sorted(self._findInstalledApt())
        s = '\n'.join(airports)
        with open(INSTALLED_APT, 'w') as fout:
            fout.writelines(s)

    def readCoord(self):
        """Read coordinates list (makes new one if non exists).

        Return dictionary of ICAO codes and its coordinates.

        """
        try:
            # Make new file.
            if not os.path.exists(APT):
                self._makeApt()

            res = {}
            with open(APT, encoding='utf-8') as fin:
                for line in fin:
                    line = line.strip().split('=')
                    icao = line[0]
                    # Read coordinates.
                    coords_line = line[-1].split(';')
                    coords = (float(coords_line[0]), float(coords_line[1]))
                    res[icao] = coords
            return res

        except IOError:
            return None

    def readMetarDat(self):
        """Fetch METAR station list from metar.dat.gz file"""
        try:
            fin = gzip.open(self.metar_path, mode='rt', encoding='utf-8')
            res = []
            for line in fin:
                if not line.startswith('#'):
                    line = line.strip()
                    res.append(line)
            fin.close()
            return res
        except IOError:
            return ['IOError']

    def rebuildApt(self):
        """Rebuild apt file."""
        self._makeApt()

    def update(self, path=None, first_run=False):
        """Read config file and update variables.

        path is a path to different than default config file
        first_run specifies if TS_checkbutton and filtered airports list
        will be updated.

        """
        del self.settings
        del self.text
        del self.aircraft_dirs
        del self.default_aircraft_dir
        del self.apt_path
        del self.ai_path
        del self.metar_path
        del self.aircraft_list
        del self.aircraft_path
        del self.airport_icao
        del self.airport_name
        del self.airport_rwy
        del self.scenario_list
        del self.carrier_list

        self.aircraft.set(DEFAULT_AIRCRAFT)
        self.airport.set(DEFAULT_AIRPORT)
        self.apt_data_source.set(0)
        self.auto_update_apt.set(0)
        self.carrier.set('None')
        self.FG_aircraft.set('')
        self.FG_bin.set('')
        self.FG_root.set('')
        self.FG_scenery.set('')
        self.FG_working_dir.set('')
        self.language.set('')
        self.baseFontSize.set(DEFAULT_BASE_FONT_SIZE)
        self.park.set('None')
        self.rwy.set('Default')
        self.scenario.set('')
        self.TS_bin.set('')
        self.TS_port.set('')
        self.TS_scenery.set('')
        if first_run:
            self.TS.set(0)
            self.filtredAptList.set(0)

        self.settings, self.text = self._read(path)

        for line in self.settings:
            cut = line.find('=') + 1

            if cut:
                name = line[:cut]
                value = line[cut:]

                if value:
                    if name in self.keywords:
                        if name == 'FILTER_APT_LIST=' and not first_run:
                            pass
                        elif name == 'TERRASYNC=' and not first_run:
                            pass
                        else:
                            var = self.keywords[name]
                            var.set(value)

        self._setLanguage(self.language.get())

        self.default_aircraft_dir = os.path.join(self.FG_root.get(),
                                                 DEFAULT_AIRCRAFT_DIR)
        self.aircraft_dirs = self._readAircraftDirs()
        self.aircraft_dirs = [self.default_aircraft_dir] + self.aircraft_dirs

        self.apt_path = os.path.join(self.FG_root.get(), APT_DAT)
        self.ai_path = os.path.join(self.FG_root.get(), AI_DIR)
        self.metar_path = os.path.join(self.FG_root.get(), METAR_DAT)

        self.aircraft_list, self.aircraft_path = self._readAircraft()
        self.scenario_list, self.carrier_list = self._readScenarios()
        self.updateAptLists()

    def updateAptLists(self):
        if self.auto_update_apt.get() and os.path.exists(self.apt_path):
            self._autoUpdateApt()
        self.airport_icao, self.airport_name, self.airport_rwy = \
            self._readApt()

    def write(self, text, path=None):
        """Write options to a file.

        text argument should be the content of text window
        path is a path to different than default config file.

        """
        if not path:
            path = CONFIG
        options = []
        keys = list(self.keywords.keys())
        keys.sort()

        for k in keys:
            v = self.keywords[k]
            if v.get() not in ('Default', 'None'):
                options.append(k + str(v.get()))

        s = '\n'.join(options)

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

        The result is a list of matching airports.

        """
        coord_dict = {}
        sceneries = self.FG_scenery.get().split(':')

        for scenery in sceneries:
            path = os.path.join(scenery, 'Terrain')
            if os.path.exists(path):
                for dir in os.listdir(path):
                    p = os.path.join(path, dir)
                    for coords in os.listdir(p):
                        converted = self._stringToCoordinates(coords)
                        coord_dict[converted] = None

        apt_coords = self.readCoord()
        coords = coord_dict.keys()
        res = {}
        for k, v in apt_coords.items():
            for c in coords:
                if v[0] > c[0][0] and v[0] < c[0][1] and \
                   v[1] > c[1][0] and v[1] < c[1][1]:
                    res[k] = None

        res = res.keys()
        return res

    def _calculateRange(self, coordinates):
        c = coordinates
        if c.startswith('s') or c.startswith('w'):
            c = int(c[1:]) * (-1)
            return c, c + 1
        else:
            c = int(c[1:])
            return c, c + 1

    def _createConfDirectory(self):
        """Create config directory if non exists."""
        if not os.path.exists(USER_DATA_DIR):
            os.mkdir(USER_DATA_DIR)

    def _makeApt(self, head=None):
        """Build apt database from apt.dat.gz"""
        if self.FG_root.get():
            _ProcessApt(self.master, self.apt_path, head)

    def _read(self, path=None):
        """Read config file"""
        # Data before the CUT_LINE in the config file, destined to
        # self.settings
        settings = []
        # Data after the CUT_LINE in the config file, destined to
        # self.text and to be parsed by CondConfigParser
        condConfLines = []
        if not path:
            path = CONFIG
        # Use default config if no regular config exists.
        if not os.path.exists(path):
            # Find currently used language.
            try:
                lang_code = gettext.translation(
                    MESSAGES, LOCALE_DIR).info()['language']
            except IOError:
                lang_code = 'en'
            path = os.path.join(DEFAULT_CONFIG_DIR, 'config_' + lang_code)
            if not os.path.isfile(path):
                lang_code = 'en'
                path = os.path.join(DEFAULT_CONFIG_DIR, 'config_' + lang_code)
            # Load presets if exists.
            try:
                with open(PRESETS, encoding='utf-8') as presets:
                    for line in presets:
                        line = line.strip()
                        if not line.startswith('#'):
                            settings.append(line)
            except IOError:
                pass

        try:
            with open(path, encoding='utf-8') as config_in:
                beforeCutLine = True
                for line in config_in:
                    if beforeCutLine:
                        line = line.strip()

                    if line != CUT_LINE:
                        if beforeCutLine:
                            settings.append(line)
                        else:
                            condConfLines.append(line)
                    else:
                        beforeCutLine = False

            return (settings, ''.join(condConfLines))
        except IOError:
            return ([''], '')

    def _readAircraft(self):
        """Walk through Aircraft directories and return two sorted lists:
        list of aircraft names and list of paths to them."""
        n, p = [], []
        for dir_ in self.aircraft_dirs:
            if os.path.isdir(dir_):
                self._readAircraftData(dir_, dir_, n)
                for d in os.listdir(dir_):
                    self._readAircraftData(dir_, d, n)
        n.sort()

        for i in range(len(n)):
            p.append(n[i][2])
            n[i] = n[i][1]

        return n, p

    def _readAircraftData(self, dir_, d, n):
        path = os.path.join(dir_, d)
        if os.path.isdir(path):
            try:
                for f in os.listdir(path):
                    self._appendAircraft(f, n, path)
            except OSError:
                pass

    def _appendAircraft(self, f, n, path):
        if f.endswith('-set.xml'):
            # Dirty and ugly hack to prevent carrier-set.xml in
            # seahawk directory to be attached to the aircraft
            # list.
            if (not path.startswith('seahawk') and
                    f != 'carrier-set.xml'):
                name = f[:-8]
                n.append([name.lower(), name, path])

    def _readAircraftDirs(self):
        return self.FG_aircraft.get().split(':')

    def _readApt(self):
        """Read apt list (makes new one if non exists).

        Return tuple of three lists:
        airports ICAO codes, airports names, airports runways

        Take a note that those lists are synchronized - each list holds
        information about the same airport at given index.

        """
        try:
            # Make new file.
            if not os.path.exists(APT):
                self._makeApt()

            icao, name, rwy = [], [], []
            with open(APT, encoding='utf-8') as fin:

                if self.filtredAptList.get():
                    installed_apt = self._readInstalledAptList()
                    for line in fin:
                        line = line.strip().split('=')
                        if line[0] in installed_apt:
                            installed_apt.remove(line[0])
                            icao.append(line[0])
                            name.append(line[1])
                            rwy_list = []
                            for i in line[2:-1]:
                                rwy_list.append(i)
                            rwy_list.sort()
                            rwy.append(rwy_list)

                else:
                    for line in fin:
                        line = line.strip().split('=')
                        icao.append(line[0])
                        name.append(line[1])
                        rwy_list = []
                        for i in line[2:-1]:
                            rwy_list.append(i)
                        rwy.append(rwy_list)

            fin.close()
            return icao, name, rwy

        except IOError:
            return [], [], []

    def _readInstalledAptList(self):
        """Read locally installed airport list.

        Make new one if non exists.

        """
        if not os.path.exists(INSTALLED_APT):
            self.makeInstalledAptList()

        res = []
        with open(INSTALLED_APT, encoding='utf-8') as fin:
            for line in fin:
                icao = line.strip()
                res.append(icao)

        return res

    def _readScenarios(self):
        """Walk through AI scenarios and read carrier data.

        Return two lists:
            scenarios: [scenario name, ...]
            carrier data: [[name, parkking pos, ..., scenario name], ...]
        Return two empty lists if no scenario is found.
        """
        try:
            carriers = []
            scenarios = []
            for f in os.listdir(self.ai_path):
                path = os.path.join(self.ai_path, f)

                if os.path.isfile(path):
                    if f.lower().endswith('xml'):
                        scenario_name = f[:-4]
                        scenarios.append(scenario_name)
                        carriers = self._append_carrier_data(carriers, path,
                                                             scenario_name)
            carriers.sort()
            scenarios.sort()
            return scenarios, carriers

        except OSError:
            return [], []

    def _append_carrier_data(self, list_, path, scenario_name):
        with open(path) as xml:
            try:
                list_copy = list_[:]
                root = self._get_root(xml)
                scenario = root.find('scenario')
                entries = scenario.findall('entry')
                for e in entries:
                    name = e.find('type')
                    if name.text == 'carrier':
                        data = self._get_carrier_data(e, scenario_name)
                        list_copy.append(data)
                return list_copy
            except (AttributeError, OSError):
                return list_

    def _get_root(self, xml):
        tree = ElementTree()
        tree.parse(xml)
        return tree.getroot()

    def _get_carrier_data(self, e, scenario_name):
        data = []
        for child in e:
            if child.tag == 'name':
                data.append(child.text)
            if child.tag == 'parking-pos':
                parking_name = child.find('name')
                data.append(parking_name.text)
        data.append(scenario_name)
        return data

    def _setLanguage(self, lang):
        # Initialize provided language...
        try:
            L = gettext.translation(MESSAGES, LOCALE_DIR, languages=[lang])
            L.install()
        # ...or fallback to system default.
        except:
            gettext.install(MESSAGES, LOCALE_DIR)

    def _stringToCoordinates(self, coordinates):
        """Convert geo coordinates to decimal format."""
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
        with open(APT_TIMESTAMP) as timestamp:
            old_modtime = timestamp.read()
        timestamp.close()
        return old_modtime

    def _writeAptTimestamp(self, s):
        with open(APT_TIMESTAMP, 'w') as timestamp:
            timestamp.write(s)
        timestamp.close()

    def _getAptModTime(self):
        return str(os.path.getmtime(self.apt_path))

    def _updateApt(self, old_timestamp):
        if old_timestamp != self._getAptModTime():
            self._makeApt(head=_('Modification of apt.dat.gz detected.'))
            self._writeAptTimestamp(self._getAptModTime())


class _ProcessApt:

    """Build apt database from apt.dat.gz"""

    def __init__(self, master, apt_path, head=None):
        self.master = master
        self.apt_path = apt_path
        self.data = []
        self.main(head)

    def main(self, head):
        if os.path.exists(self.apt_path):
            self.make_window(head)
            try:
                self.makeApt()
            except AptdatHeaderError:
                self.show_aptdat_header_error()
                self.close_window()
                return
            except:
                print(traceback.format_exc(), file=sys.stderr)
                self.show_aptdat_general_error()
                self.close_window()
                return
            self.close_window()
        else:
            self.show_no_aptdat_error()

    def make_window(self, head=None):
        message = _('Generating airport database,\nthis can take a while...')
        if head:
            message = '\n'.join((head, message))
        self.window = InfoWindow(self.master, message)
        self.window.update()

    def makeApt(self):
        self.reset_variables()
        version = self.get_apt_version_number()
        self.process_atp(version)

        self.data.sort()
        self.save_atp_data()

    def reset_variables(self):
        self.entry = ''
        self.lat, self.lon = 0.0, 0.0
        self.runway_count = 0

    def get_apt_version_number(self):
        """Return version number of apt.dat.gz file.

        It can be found at the beginning of a second line of the header.

        """
        with gzip.open(self.apt_path) as fin:
            origin, number, version = self.read_header(fin)
            number = self.get_version_number(origin, number, version)
            return number

    def read_header(self, fin):
        data = fin.read(24).decode('utf-8')
        d = data.split()
        try:
            origin, number, version = d[0], d[1], d[2]
            return origin, number, version
        except:
            raise AptdatHeaderError

    def get_version_number(self, origin, number, version):
        if ((origin == 'A' or origin == 'I') and
                number.isdigit() and version == 'Version'):
            return number
        else:
            raise AptdatHeaderError

    def process_atp(self, version):
        with gzip.open(self.apt_path) as fin:
            for line in fin:
                # The apt.dat is using iso-8859-1 encoding.
                line = line.decode('iso-8859-1')
                e = line.strip().split()

                self.process_airport_data(version, e)
                self.finalize_processing_airport(line)

    def process_airport_data(self, version, e):
        if int(version) < 850:
            self.process_data_v810(e)
        else:
            self.process_data_v850(e)

    def process_data_v810(self, e):
        if e and e[0] in ('1', '16', '17'):
            self.get_atp_name(e)
        # Find runways.
        elif self.entry and e and e[0] == '10':
            if e[3] != 'xxx':
                rwy = e[3]
                if rwy.endswith('x'):
                    rwy = rwy[:-1]

                lat, lon = e[1], e[2]
                self.set_rwy_data(rwy, lat, lon, addotherend=True)

                self.runway_count += 1

    def set_rwy_data(self, rwy, lat, lon, addotherend=False):
        """Set runway data.

        If addotherend is set to True, it computes and adds 
        other end of given rwy. It is needed for apt.dat v 810 
        and earlier data format, where only one runway end is provided.

        """
        self.entry += ('=' + rwy)
        if addotherend:
            self.add_other_end(rwy)
        self.set_position_data(lat, lon)

    def set_position_data(self, lat, lon):
        self.lat += float(lat)
        self.lon += float(lon)

    def add_other_end(self, rwy):
        rwy_number = self.compute_other_end(rwy)
        if rwy_number:
            self.entry += ('=' + rwy_number)

    def compute_other_end(self, rwy):
        if not rwy.startswith('H'):
            prefix = self.compute_heading(rwy)
            suffix = self.change_left_right(rwy)
            return prefix + suffix

    def compute_heading(self, rwy):
        number = self.get_heading(rwy)
        if number <= 36 and number > 18:
            prefix = str(number - 18)
        elif number > 0 and number <= 18:
            prefix = str(number + 18)
        return prefix

    def get_heading(self, rwy):
        while not rwy.isdigit():
            rwy = rwy[:-1]
        return int(rwy)

    def change_left_right(self, rwy):
        suffix = ''
        if rwy.endswith('L'):
            suffix = 'R'
        elif rwy.endswith('R'):
            suffix = 'L'
        elif rwy.endswith('C'):
            suffix = 'C'
        return suffix

    def process_data_v850(self, e):
        if e and e[0] in ('1', '16', '17'):
            self.get_atp_name(e)
        # Find runways.
        elif self.entry and e and e[0] == '100':
            self.set_first_rwy_v850(e)
            self.set_second_rwy_v850(e)
            self.runway_count += 2
        # Find water runways.
        elif self.entry and e and e[0] == '101':
            self.set_first_water_rwy_v850(e)
            self.set_second_water_rwy_v850(e)
            self.runway_count += 2
        # Find helipads.
        elif self.entry and e and e[0] == '102':
            self.set_helipad_v850(e)
            self.runway_count += 1

    def set_first_rwy_v850(self, e):
        self.set_rwy_data(e[8], e[9], e[10])

    def set_second_rwy_v850(self, e):
        self.set_rwy_data(e[17], e[18], e[19])

    def set_first_water_rwy_v850(self, e):
        self.set_rwy_data(e[3], e[4], e[5])

    def set_second_water_rwy_v850(self, e):
        self.set_rwy_data(e[6], e[7], e[8])

    def set_helipad_v850(self, e):
        self.set_rwy_data(e[1], e[2], e[3])

    def get_atp_name(self, e):
        """Get ICAO and airport name."""
        name = [e[4], ' '.join(e[5:])]
        name = '='.join(name)
        self.entry = name

    def finalize_processing_airport(self, line):
        if self.entry and (line in ['\n', '\r\n'] or line.startswith('99')):
            self.averaged_coordinates()
            self.set_coordinates()
            self.reset_variables()

    def averaged_coordinates(self):
        if self.runway_count:
            self.lat /= self.runway_count
            self.lon /= self.runway_count

    def set_coordinates(self):
        coords = ';'.join(['{0:.8f}'.format(round(self.lat, 8)),
                           '{0:.8f}'.format(round(self.lon, 8))])
        self.entry = '='.join([self.entry, coords])
        self.data.append(self.entry)

    def save_atp_data(self):
        with open(APT, 'w') as fin:
            for i in self.data:
                fin.write(str(i) + '\n')

    def show_aptdat_header_error(self):
        message = _('Cannot read version number of apt.dat database.\n\n'
                    'FGo! expects a proper header information at the '
                    'beginning of apt.dat. For details about data format see '
                    'http://data.x-plane.com/designers.html#Formats')
        showerror(_('Error'), message)

    def show_aptdat_general_error(self):
        message = _('Cannot read apt.dat database.')
        showerror(_('Error'), message)

    def show_no_aptdat_error(self):
        message = _('Cannot find apt.dat database.')
        showerror(_('Error'), message)

    def close_window(self):
        self.window.destroy()


class AptdatHeaderError(Exception):
    pass
