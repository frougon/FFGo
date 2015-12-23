# apt_dat.py --- Parse X-Plane/FlightGear's apt.dat file; create and read the
#                “apt digest file”
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import gzip
import re
import textwrap
import bisect
from math import degrees, radians, cos, sin

try:
    from geographiclib.geodesic import Geodesic
    HAS_GEOGRAPHICLIB = True
except ImportError:
    HAS_GEOGRAPHICLIB = False

from .. import constants
from ..constants import PROGNAME
from .. import misc
from ..logging import logger
from .airport import Airport, AirportStub, AirportType, LandRunway, \
    WaterRunway, Helipad, RunwayType, SurfaceType, V810SurfaceType, \
    ShoulderSurfaceType, RunwayMarkings, PerimeterBuoys, HelipadEdgeLighting
from . import parking
from .parking import ParkingSource
from ..geo import geodesy
from ..geo.geodesy import cosd, sind, normLon, NVector

# This import requires the translation system [_() function] to be in
# place.
from ..exceptions import FFGoException


class error(FFGoException):
    """Base class for exceptions in the apt_dat module."""
    ExceptionShortDescription = _("Error caught in the apt_dat module")

class UnableToParseAptDat(error):
    """
    Exception raised when we cannot parse the apt.dat (or apt.dat.gz) file."""
    ExceptionShortDescription = _(
        "Unable to parse the apt.dat (or apt.dat.gz) file")
    def __init__(self, lineNb, message=None):
        error.__init__(self, message)
        self.lineNb = lineNb

    def __repr__(self):
        return "{0}.{1}({2!r}, {3!r})".format(__name__, type(self).__name__,
                                              self.lineNb, self.message)

    def detail(self):
        if self.message:
            return _("line {line}: {msg}").format(line=self.lineNb,
                                                  msg=self.message)
        else:
            return _("line {line}").format(line=self.lineNb)

    def completeMessage(self):
        if self.message:
            return _("{shortDesc}: {detail}").format(
                shortDesc=self.ExceptionShortDescription,
                detail=self.detail())
        else:
            return _("{shortDesc} ({detail})").format(
                shortDesc=self.ExceptionShortDescription,
                detail=self.detail())

class UnableToParseAptDatHeader(UnableToParseAptDat):
    """
    Exception raised when we cannot parse the apt.dat (or apt.dat.gz) header."""
    ExceptionShortDescription = _(
        "Unable to parse the apt.dat (or apt.dat.gz) header")

class UnableToParseAptDigest(error):
    """Exception raised when we can't parse the apt digest file."""
    ExceptionShortDescription = _("Unable to parse the apt digest file")

class UnrecognizedFormatForAptDigest(UnableToParseAptDigest):
    """
    Exception raised when we can't recognize the format of the apt digest file."""
    ExceptionShortDescription = _(
        "Unable to recognize the format of the apt digest file")


class AptDat:
    """Class for reading X-Plane/FlightGear's apt.dat file.

    The makeAptDigest() method can be used to write an apt digest file
    from the input apt.dat (or apt.dat.gz...). Read support for such
    files is provided by the AptDatDigest class.

    """

    geodCalc = geodesy.GeodCalc()

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def open(self):
        logger.info("Opening '{}' for reading".format(self.path))
        # Binary mode because:
        #   - it seems to offer better guarantees as for being able to reuse an
        #     offset saved with tell() later, after reopening the file (in
        #     binary mode, tell() returns a byte offset whereas the meaning of
        #     the return value is unfortunately unspecified in text mode, and
        #     it is not stated if it can be reused safely once the file is
        #     reopened);
        #   - it considerably increases the speed of tell(), making the
        #     “rebuild airport database” operation take about 25 s on my
        #     computer as opposed to 56 s when apt.dat.gz is opened in text
        #     mode!
        #
        # Note: alternatively, using the line number as an index instead of the
        #       return value of tell() allows to build the database in less
        #       than 12 s, however looking up an airport later using such an
        #       index is significantly slower (about 2.3 s in text mode for
        #       YSSL in apt.dat 'cycle 2013.10', as opposed to 0.8 s with
        #       an index obtained using tell() [the latter in text as well as
        #       binary mode]).
        self.file = gzip.open(self.path, mode="rb")

        return self.file

    def __enter__(self):
        self.open()

        try:
            self.lineNb = 0
            self._readHeader()
            return self
        except:
            self.file.close()
            raise

    def __exit__(self, excType, excVal, excTb):
        self.file.close()
        return False

    def _readline(self):
        """Read a non-empty, non-comment line from apt.dat.

        Store the line read in self.line and its number in self.lineNb
        (starting from 1). Return the empty string when reaching EOF.

        """
        while True:
            self.lineNb += 1
            # As indicated by the copyright sign at the top, apt.dat seems to
            # use the ISO 8859-1 encoding (it might be a similar one such as
            # ISO 8859-15, but I believe the X-Plane maintainers try to use
            # ASCII only in the actual data).
            line = self.file.readline().decode("latin_1", errors="replace")
            if not line:
                self.line = ""
                return ""       # EOF

            # The apt.dat 'cycle 2013.10' has many trailing spaces. This also
            # strips the final \n, which is nicer for error messages.
            line = line.strip()
            # The apt.dat v1000 format allows comments starting with two '#'
            # characters.
            if line and not line.startswith("##"):
                break

        self.line = line        # used when reporting parse errors, etc.
        return line

    _record_cre = re.compile(r"(?P<code>\d+)[ \t]*(?P<rest>.*)$")

    def _readRecord(self):
        """Read an apt.dat record.

        Return a tuple of the form (code, payload) where 'code' is an
        integer and 'payload' a string, or (None, None) if called at
        EOF.

        """
        line = self._readline()
        if not line:
            return (None, None) # EOF

        mo = self._record_cre.match(line)
        if not mo:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not a valid record: {!r}").format(self.line))

        return (int(mo.group("code")), mo.group("rest"))

    _formatLine_cre = re.compile(r"""(?P<version>\d+ (\.\d+)* )""", re.VERBOSE)
    def _readHeader(self):
        """Read the apt.dat header."""
        line = self._readline()
        if not line:
            raise UnableToParseAptDatHeader(
                self.lineNb,
                _("EOF reached while looking for the first non-empty line"))
        if len(line) != 1:     # should be either 'I' (“PC”) or 'A' (“MAC”)
            raise UnableToParseAptDatHeader(
                self.lineNb,
                _("first non-empty line should contain exactly one character"))

        line = self._readline()
        if not line:
            raise UnableToParseAptDatHeader(
                self.lineNb,
                _("EOF reached while looking for the version of the format"))

        mo = self._formatLine_cre.match(line)
        if not mo:
            raise UnableToParseAptDatHeader(
                self.lineNb,
                _("unexpected header line: {line!r}").format(line=self.line))

        self.formatVersion = int(mo.group("version"))
        if self.formatVersion > 1000:
            logger.warning(
                _("'{aptDat}' reports a format version {ver}, which this "
                  "version of {prg} doesn't know about. Things may not work "
                  "correctly. Please report a bug.").format(
                      aptDat=self.path, ver=self.formatVersion,
                      prg=PROGNAME))

        self.endOfHeader = self.file.tell()
        self.endOfHeaderLineNb = self.lineNb

    def reset(self):
        """Position the apt.dat file pointer right after the header.

        Adjust self.lineNb accordingly.

        """
        self.file.seek(self.endOfHeader)
        self.lineNb = self.endOfHeaderLineNb

    def _readLatitude(self, s):
        try:
            res = misc.DecimalCoord(s)
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a latitude: {0!r} in line {1!r}").format(
                    s, self.line)) from e
        else:
            return res

    def _readLongitude(self, s):
        try:
            res = misc.DecimalCoord(s)
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a longitude: {0!r} in line {1!r}")
                .format(s, self.line)) from e
        else:
            return res

    def _readHeading(self, s):
        try:
            res = float(s)
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a heading: {0!r} in line {1!r}").format(
                    s, self.line)) from e
        else:
            return res

    def _readLength(self, s):
        try:
            res = float(s)
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a length: {0!r} in line {1!r}")
                .format(s, self.line)) from e
        else:
            return res

    def _readElevation(self, s):
        try:
            res = float(s)
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as an elevation: {0!r} in line {1!r}")
                .format(s, self.line)) from e
        else:
            return res

    def _readSurfaceType(self, s):
        try:
            res = SurfaceType(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a surface type code: {0!r} in line "
                  "{1!r}").format(s, self.line)) from e
        else:
            return res

    def _readV810SurfaceType(self, s):
        try:
            res = V810SurfaceType(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a v810 surface type code: {0!r} in line "
                  "{1!r}").format(s, self.line)) from e
        else:
            return res

    def _readShoulderSurfaceType(self, s):
        try:
            res = ShoulderSurfaceType(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a shoulder surface type code: {0!r} in "
                  "line {1!r}").format(s, self.line)) from e
        else:
            return res

    def _readSmoothness(self, s):
        try:
            res = float(s)
            if not (0 <= res <= 1):
                raise ValueError(_("invalid smoothness value: {0!r}").format(
                    res))
        except ValueError:
            # Tolerate this error for now in order to allow FFGo to run (error
            # present in some versions of apt.dat, cf.
            # <http://gatewaybugs.x-plane.com/browse/XSG-1218>).
            logger.warning(
                _("Error in apt.dat: unable to parse as a smoothness value: "
                  "{val!r} in line {lineNb} ({line!r})")
                .format(val=s, lineNb=self.lineNb, line=self.line))
            res = None

        return res

    def _readRunwayMarkings(self, s):
        try:
            res = RunwayMarkings(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a code for runway markings: {0!r} in "
                  "line {1!r}").format(s, self.line)) from e
        else:
            return res

    def _readV810RunwayMarkings(self, s):
        try:
            code = int(s)
            if code in range(0, 4):
                res = RunwayMarkings(code)
            else:
                raise ValueError(_("invalid v810 code for runway markings: "
                                   "{0!r}").format(code))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a v810 code for runway markings: "
                  "{0!r} in line {1!r}").format(s, self.line)) from e
        else:
            return res

    def _readPerimeterBuoysFlag(self, s):
        try:
            res = PerimeterBuoys(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as a perimeter buoys flag: {0!r} in line "
                  "{1!r}").format(s, self.line)) from e
        else:
            return res

    def _readHelipadEdgeLighting(self, s):
        try:
            res = HelipadEdgeLighting(int(s))
        except ValueError as e:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unable to parse as an helipad edge lighting flag: {0!r} in "
                  "line {1!r}").format(s, self.line)) from e
        else:
            return res

    def _processPotentialParkingRow(self, code, payload, startupLocations):
        """Read “parking” information from (code, payload) if applicable.

        'startupLocations' is supposed to be a dictionary whose keys are
        a type of location according to the apt.dat spec (string among
        "hangar", "gate", "misc" or "tie-down" according to APT1000) and
        values a list of startup locations of this type.
        'startupLocations' is *modified in-place*, the startup locations
        found being appended.

        This method is a no-op if 'code' doesn't correspond to an
        apt.dat startup location.

        """
        if code == 15: # Startup location (v850, deprecated)
            l = payload.split(None, maxsplit=3)
            if len(l) < 3:
                raise UnableToParseAptDat(
                    self.lineNb,
                    _("not enough fields in record: {!r}").format(
                        self.line))
            elif len(l) == 3:
                l.append('?') # parking name missing in apt.dat

            parkName = l[3] or '?'
            p = parking.Parking(
                name=parkName, lat=self._readLatitude(l[0]),
                lon=self._readLongitude(l[1]),
                heading=self._readHeading(l[2]),
                source=ParkingSource.apt_dat)

            if "" not in startupLocations:
                startupLocations[""] = []

            startupLocations[""].append(p) # flight type unknown for these parks
        elif code == 1300:    # Airport location (v1000, deprecates
                              # code 15)
            l = payload.split(None, maxsplit=5)
            if len(l) < 6:
                raise UnableToParseAptDat(
                    self.lineNb,
                    _("not enough fields in record: {!r}").format(
                        self.line))

            locType = l[3]
            parkName = l[5] or '?'
            p = parking.Parking(
                name=parkName, type=locType,
                lat=self._readLatitude(l[0]),
                lon=self._readLongitude(l[1]),
                heading=self._readHeading(l[2]),
                source=ParkingSource.apt_dat)

            if locType not in startupLocations:
                startupLocations[locType] = []

            startupLocations[locType].append(p)

    # This method is not used anymore.
    def readParkingForIcao(self, icao):
        """Read startup locations for an airport without using any index.

        apt.dat.gz being large, this method can be very slow (on the
        order of 10 seconds).

        """
        self.reset()
        parkings = {}
        finished = False

        while not finished:
            code, payload = self._readRecord()

            if code is None:    # EOF
                break
            elif code in (1, 16, 17): # Land airport, seaplane base or heliport
                l = payload.split(None, maxsplit=4)
                if len(l) < 5:
                    raise UnableToParseAptDat(
                        self.lineNb,
                        _("not enough fields in record: {!r}").format(
                            self.line))

                if l[3].upper() != icao:
                    continue

                while not finished:
                    code, payload = self._readRecord()

                    if code in (None, 1, 16, 17):
                        finished = True
                    else:
                        self._processPotentialParkingRow(
                            code, payload, parkings)

        for parkList in parkings.values():
            parkList.sort(key=parking.Parking.fullNameSortKey)

        return parkings

    def makeAptDigest(self, outputFile=None):
        """Write the apt digest file.

        The resulting file is read on each startup of FFGo, therefore
        parsing it must be much quicker than parsing apt.dat. The file
        thus contains the minimum information needed to:
          - build the airport list;
          - find the nearest METAR station for a given airport;
          - look up more information about a given airport in apt.dat
            (an index allows to do that efficiently), and be able to
            display the relevant apt.dat line number in case an error is
            encountered;
          - perform the searches offered by the Airport Finder.

        """
        if outputFile is None:
            outputFile = constants.APT

        self.reset()
        airports = []
        eof = False
        # Start index for the first airport header (byte offset + line number)
        index = (self.file.tell(), self.lineNb)
        code, payload = self._readRecord()

        while not eof:
            if code in (1, 16, 17): # Land airport, seaplane base or heliport
                icao, type_, name, elev = self._processAirportHeader(code,
                                                                     payload)
                eof, nextIndex, code, payload, avgLat, avgLon, landRunways, \
                    waterRunways, helipads, minRwyLength, maxRwyLength, \
                    parkings = self._readAirportData(calcCoords=True,
                                                     readDetails=False)
                # This should be better than sorting the list once complete
                # from an algorithmic point of view, however the difference is
                # hardly measurable with apt.dat 2013.10, build 20131335,
                # containing 34074 airports (the sort() taking about 0.04 s).
                bisect.insort_right(airports,
                                    (icao, type_.value, name, elev, avgLat,
                                     avgLon, len(landRunways),
                                     len(waterRunways), len(helipads),
                                     minRwyLength, maxRwyLength, index))
                index = nextIndex
            elif code in (None, 99): # None: EOF; 99: X-Plane's convention
                break
            else:
                raise UnableToParseAptDat(
                    self.lineNb,
                    _("unexpected row code: {code} (line: {line!r})").format(
                        code=code, line=self.line))

        if code is not None:
            self.file.read()    # go to the end of the file
        # This will be used later for a basic safety check when using an
        # index, because the seek() method of gzip.GzipFile behaves
        # pretty badly in some cases (seemingly never returning), and I
        # suppose this may be due to the use of an invalid index.
        aptDatSize = self.file.tell()

        logger.info("Opening {prg}'s apt digest file ('{aptDigest}') for "
                    "writing".format(prg=PROGNAME, aptDigest=outputFile))

        with open(outputFile, "w", encoding="utf-8") as f:
            f.write(AptDatDigest.header(aptDatSize))

            # Optimizing this with writelines() doesn't seem to be worth it
            # (0.11 seconds instead of 0.12, while the whole method takes about
            # 28 seconds for 34074 airprts).
            for icao, type_, name, elev, avgLat, avgLon, nbLandRunways, \
                nbWaterRunways, nbHelipads, minRwyLength, maxRwyLength, \
                index in airports:
                nbRunways = ';'.join(( str(s) for s in
                                       (nbLandRunways, nbWaterRunways,
                                        nbHelipads) ))
                if minRwyLength is None:
                    minMaxRwyLengths = ""
                else:
                    minMaxRwyLengths = "{:.04f};{:.04f}".format(minRwyLength,
                                                                maxRwyLength)

                # Byte offset followed by line number
                indexRepr = ';'.join(( str(i) for i in index ))

                f.write(
                    '\0'.join([icao, name, str(type_),
                               avgLat.precisionRepr(), avgLon.precisionRepr(),
                               nbRunways, minMaxRwyLengths, indexRepr])
                    + '\n')

    def _processAirportHeader(self, code, payload):
        l = payload.split(None, maxsplit=4)
        if len(l) < 5:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(
                    self.line))

        # Land airport, seaplane base or heliport
        type_ = AirportType(code)
        # The type (int or float) is unspecified in X-Plane's APT1000 spec
        elev = self._readElevation(l[0])
        icao = l[3].upper()
        name = l[4]

        return (icao, type_, name, elev)

    def _readAirportData(self, calcCoords=False, readRunways=False,
                         readParkings=False, readDetails=True):
        landRunways = []
        waterRunways = []
        helipads = []
        # Will give the coordinates of the centroid of all runway ends +
        # helipads of the airport (each runway has a sort of “double weight”
        # because of its two ends, contrary to a helipad).
        avgLat, avgLon = None, None
        nvecSum = NVector(0.0, 0.0, 0.0)
        minRwyLength = maxRwyLength = None
        parkings = {}
        eof = False

        while True:
            index = (self.file.tell(), self.lineNb)
            code, payload = self._readRecord()

            if code in (1, 16, 17): # Land airport, seaplane base or heliport
                break
            elif code in (None, 99):    # None: EOF; 99: X-Plane's convention
                eof = True
                break
            else:
                if calcCoords or readRunways:
                    isRwyRecord, nvecSum0, rwyLength = \
                        self._processPotentialRunwayRow(
                            code, payload, landRunways, waterRunways, helipads,
                            readDetails=readDetails)
                    if isRwyRecord:
                        nvecSum += nvecSum0

                        if rwyLength is not None:
                            if minRwyLength is None: # no length encountered yet
                                minRwyLength = maxRwyLength = rwyLength
                            else:
                                minRwyLength = min(minRwyLength, rwyLength)
                                maxRwyLength = max(maxRwyLength, rwyLength)

                if readParkings:
                    self._processPotentialParkingRow(code, payload, parkings)

        if calcCoords:
            # Each land or water runway is counted twice, once for each runway
            # end.
            n = 2*len(landRunways) + 2*len(waterRunways) + len(helipads)
            if n > 0:
                avgLat, avgLon = map(misc.DecimalCoord,
                                     nvecSum.scalarDiv(n).latLon())

        if readRunways:
            for runwayList in (landRunways, waterRunways, helipads):
                runwayList.sort(key=lambda runway: runway.name)

        if readParkings:
            for parkList in parkings.values():
                parkList.sort(key=parking.Parking.fullNameSortKey)

        return (eof, index, code, payload, avgLat, avgLon, landRunways,
                waterRunways, helipads, minRwyLength, maxRwyLength, parkings)

    def _processPotentialRunwayRow(self, code, payload, landRunways,
                                   waterRunways, helipads, readDetails=True):
        """Read runway information from (code, payload) if applicable.

        'landRunways', 'waterRunways' and 'helipads' should behave like
        lists and are *modified in-place*, the runways found being
        appended. When 'readDetails' is False, None is used instead of
        instances of a subclass of RunwayBase (but the number of None
        objects added does correspond to the number of runways found).

        Return a tuple of the form (isRwyRecord, nvecSum) where:
          - 'isRwyRecord' is a boolean indicating whether 'code' is
            recognized as a runway code;
          - 'nvecSum' is the sum of the n-vectors for each runway end
            defined by (code, payload) (i.e., typically two opposite
            runway ends for one “physical runway”, but a helipad also
            counts as one “runway end”). This can be used as a basis for
            computing the “centroid” of an airport, so to speak.

        This method is a no-op if 'code' doesn't correspond to an
        apt.dat runway (helipads counting as runways in this context).

        """
        isRwyRecord = True
        length = None

        if code == 10:  # Runway or taxiway from the APT810 spec (old)
            e = payload.split()
            # 'xxx' would indicate a taxiway
            if len(e) >= 3 and e[2] != 'xxx':
                # “Latitude/longitude [...] of runway or
                # taxiway segment center” according to the APT810 spec
                lat, lon, landRwys, waterRwys, helip, length = \
                            self._processV810Runway(e, readDetails=readDetails)
                landRunways.extend(landRwys)
                waterRunways.extend(waterRwys)
                helipads.extend(helip)
                # May be one helipad or two reciprocal runway ends
                nvecSum = NVector.fromLatLon(lat, lon)
                if len(rwys) > 1:  # Two reciprocal runway ends
                    nvecSum += nvecSum
            else:
                isRwyRecord = False
        elif code == 100:
            lat1, lon1, lat2, lon2, length, rwys = self.processLandRunway(
                payload, readDetails=readDetails)
            nvecSum = (NVector.fromLatLon(lat1, lon1) +
                       NVector.fromLatLon(lat2, lon2))
            landRunways.extend(rwys)
        elif code == 101:
            lat1, lon1, lat2, lon2, length, rwys = self.processWaterRunway(
                payload, readDetails=readDetails)
            nvecSum = (NVector.fromLatLon(lat1, lon1) +
                       NVector.fromLatLon(lat2, lon2))
            waterRunways.extend(rwys)
        elif code == 102:
            # Helipad length is not counted as a “runway length”
            lat, lon, rwys = self.processHelipad(payload,
                                                 readDetails=readDetails)
            nvecSum = NVector.fromLatLon(lat, lon)
            helipads.extend(rwys)
        else:
            isRwyRecord = False

        if not isRwyRecord:
            nvecSum = None      # no runway found

        return (isRwyRecord, nvecSum, length)

    def _computeV810RunwayEnds(self, lat, lon, length, azimuth1, azimuth2):
        """Compute the coordinates of the opposite ends of a v810 runway.

        lat, lon:
          coordinates of the “runway center” (midpoint of the two runway
          ends)
        azimuth1 and azimuth2:
          headings of each of the reciprocal runways (they should differ
          by 180°)

        """
        earth = self.geodCalc.earthModel

        def clampLat(l):
            if l > 90.0:
                l = 90.0
            elif l < -90.0:
                l = -90.0
            return l

        tmp = lat - degrees(0.5*length*cosd(azimuth1) /
                            earth.meridionalRadius(lat))
        # Of course, this is not good at the poles, but the whole
        # calculation method is pretty bad there anyway...
        lat1 = clampLat(tmp)
        tmp = lat - degrees(0.5*length*cosd(azimuth2) /
                            earth.meridionalRadius(lat))
        lat2 = clampLat(tmp)

        cosLat = cosd(lat)
        try:
            tmp = lon - degrees(0.5*length*sind(azimuth1) /
                                (cosLat*earth.normalRadius(lat)))
            lon1 = normLon(tmp)
            tmp = lon - degrees(0.5*length*sind(azimuth2) /
                                (cosLat*earth.normalRadius(lat)))
            lon2 = normLon(tmp)
        except ZeroDivisionError:
            # If the runway center is at the North or South pole, there
            # is no way to interpret its heading (the north direction
            # is undefined at these particular places)!
            lon1 = lon2 = None

        return (lat1, lon1, lat2, lon2)

    _v810Helipad_cre = re.compile(r"(?P<name>H(?P<number>\d+))x$")

    def processV810Runway(self, e, readDetails=True):
        # This whole method is untested, as apt.dat 2013.10 (build 20131335)
        # does not contain any runway declared in this old format...
        if len(e) < 14:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(
                    self.line))

        landRunways = []
        waterRunways = []
        helipads = []
        # 'rwyLength' is for real runways, not helipads (convert to meters)
        rwyLength = length = self._readLength(e[4]) * 0.3048
        lat = self._readLatitude(e[0])
        lon = self._readLongitude(e[1])
        v810SurfaceType = self._readV810SurfaceType(e[9])

        if readDetails:
            name = e[2]
            heading = self._readHeading(e[3])
            # In v810 format, runway lengths and widths are given in feet
            width = self._readLength(e[5]) * 0.3048  # convert to meters
            surfaceType = v810SurfaceType.v1000Equivalent()
            shoulderSurfaceType = self._readShoulderSurfaceType(e[10])
            runwayMarkings = self._readV810RunwayMarkings(e[11])
            smoothness = self._readSmoothness(e[12])

        if v810SurfaceType.isHelipad():
            rwyLength = None
            if readDetails:
                mo = self._v810Helipad_cre.match(name) # Helipad?
                if mo:
                    # Override 'name' (remove trailing "x")
                    name = mo.group("name")

                helipads.append(
                    Helipad(name, lat, lon, heading, length, width,
                            surfaceType, shoulderSurfaceType, None,
                            smoothness, None))
            else:
                helipads.append(None)
        elif readDetails:
            if name.endswith('x'): # rwy with no L, R, C, S... suffix
                name = name[:-1]

            num1 = self.getRwyNum(name)
            num2, name2 = self.otherRunway(name)
            azimuth1 = self.correctRwyHeadingBasedOnRwyNum(heading, num1)
            azimuth2 = self.correctRwyHeadingBasedOnRwyNum(heading, num2)

            if HAS_GEOGRAPHICLIB:
                # Compute the coordinates of the runway ends based on:
                #   - the coordinates of their midpoint;
                #   - the runway length and heading.
                halfLength_m = 0.5*length
                g1 = Geodesic.WGS84.Direct(lat, lon, azimuth2, halfLength_m)
                g2 = Geodesic.WGS84.Direct(lat, lon, azimuth1, halfLength_m)
                lat1, lon1 = g1['lat2'], g1['lon2']
                lat2, lon2 = g2['lat2'], g2['lon2']
            else:
                # Fallback method. It should work decently everywhere except
                # when very close to the poles, where the direction of "north"
                # can change infinitely fast with tiny changes in longitude if
                # one is close enough to either the North or South pole.
                lat1, lon1, lat2, lon2 = self._computeV810RunwayEnds(
                    lat, lon, length, azimuth1, azimuth2)

            # Two runways, differing in azimuth by 180°
            if v810SurfaceType.isWaterRunway():
                rwy1 = WaterRunway(name, lat1, lon1, azimuth1, length, width,
                                   None)
                rwy2 = WaterRunway(name2, lat2, lon2, azimuth2, length, width,
                                   None)
                waterRunways.extend( (rwy1, rwy2) )
            else:
                rwy1 = LandRunway(
                    name, lat1, lon1, azimuth1, length, width, surfaceType,
                    shoulderSurfaceType, runwayMarkings, smoothness)
                rwy2 = LandRunway(
                    name2, lat2, lon2, azimuth2, length, width, surfaceType,
                    shoulderSurfaceType, runwayMarkings, smoothness)
                landRunways.extend( (rwy1, rwy2) )
        elif v810SurfaceType.isWaterRunway():
            # Two runways, differing in azimuth by 180°
            waterRunways.extend( (None, None) )
        else:
            # Ditto
            landRunways.extend( (None, None) )

        return (lat, lon, landRunways, waterRunways, helipads, rwyLength)

    def otherRunway(self, num, suffix):
        otherNum = self.computeOtherRwyNum(num)
        otherSuffix = self.otherRwySuffix(suffix)
        return (otherNum, "{:02d}{}".format(otherNum, otherSuffix))

    def computeOtherRwyNum(self, number):
        if 18 < number <= 36:
            other = number - 18
        elif 0 < number <= 18:
            other = number + 18
        else:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unexpected runway number: {num!r} "
                  "(line: {line!r})").format(num=number, line=self.line))

        return other

    _rwyNum_cre = re.compile(r"(?P<num>\d+)")

    def getRwyNum(self, rwy):
        mo = self._rwyNum_cre.match(rwy)
        if not mo:
            raise UnableToParseAptDat(
                self.lineNb,
                _("runway name not starting with digits: {rwy!r} "
                  "(line: {line!r})").format(rwy=rwy, line=self.line))

        return int(mo.group("num"))

    def otherRwySuffix(self, suffix):
        if suffix == 'L':
            return 'R'
        elif suffix == 'R':
            return 'L'
        else:
            return suffix

    @classmethod
    def correctRwyHeadingBasedOnRwyNum(cls, azimuth, rwyNum):
        """
        Find the precise runway heading based on 'azimuth' and the runway number.

        If 'azimuth' is in the "wrong direction", return
        (azimuth + 180); otherwise, return 'azimuth'.

        """
        angularDiff = min(abs(10*rwyNum - azimuth),
                          abs(10*(36 + rwyNum) - azimuth),
                          abs(10*rwyNum - (360.0+azimuth)))

        return (azimuth + 180) if angularDiff > 90 else azimuth

    @classmethod
    def computeLengthAndAzimuth(cls, lat1, lon1, lat2, lon2):
        g = cls.geodCalc.inverse(lat1, lon1, lat2, lon2)
        return (g["s12"], g["azi1"], g["azi2"] + 180.0)

    @classmethod
    def computeLengthForAptDigest(cls, lat1, lon1, lat2, lon2):
        try:
            # Fast and accurate method, but might fail in a few cases (not for
            # a runway length, I think, but let's take maximum precautions,
            # because a failure here would prevent FFGo from working at all).
            dist = cls.geodCalc.vincentyInverseWithFallback(lat1, lon1,
                                                            lat2, lon2)["s12"]
        except geodesy.error:
            if cls.geodCalc.karneyMethodAvailable():
                # Slower, extremely accurate and should work in all cases, but
                # may not be installed for all users.
                dist = cls.geodCalc.karneyInverse(lat1, lon1,
                                                  lat2, lon2)["s12"]
            else:
                # Very fast, not very accurate but still OK for a runway
                # length (I believe I found a 9 cm difference for a 3600 m
                # long runway near Paris). Should work in all cases.
                dist = cls.geodCalc.modifiedFccDistance(lat1, lon1, lat2, lon2)
        return dist

    def processLandRunway(self, payload, readDetails=True):
        """Process a runway record with code 100."""
        e = payload.split()
        if len(e) < 22:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(self.line))

        lat1 = self._readLatitude(e[8])
        lon1 = self._readLongitude(e[9])
        lat2 = self._readLatitude(e[17])
        lon2 = self._readLongitude(e[18])

        if readDetails:
            name1, name2 = e[7], e[16]
            length, azimuth1, azimuth2 = self.computeLengthAndAzimuth(
                lat1, lon1, lat2, lon2)
            width = self._readLength(e[0])
            surfaceType = self._readSurfaceType(e[1])
            shoulderSurfaceType = self._readShoulderSurfaceType(e[2])
            smoothness = self._readSmoothness(e[3])
            runwayMarkings1 = self._readRunwayMarkings(e[12])
            runwayMarkings2 = self._readRunwayMarkings(e[21])
            rwy1 = LandRunway(name1, lat1, lon1, azimuth1, length, width,
                              surfaceType, shoulderSurfaceType,
                              runwayMarkings1, smoothness)
            rwy2 = LandRunway(name2, lat2, lon2, azimuth2, length, width,
                              surfaceType, shoulderSurfaceType,
                              runwayMarkings2, smoothness)
            return (lat1, lon1, lat2, lon2, length, (rwy1, rwy2))
        else:
            length = self.computeLengthForAptDigest(lat1, lon1, lat2, lon2)
            return (lat1, lon1, lat2, lon2, length, (None, None))

    def processWaterRunway(self, payload, readDetails=True):
        """Process a runway record with code 101."""
        e = payload.split()
        if len(e) < 8:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(self.line))

        lat1 = self._readLatitude(e[3])
        lon1 = self._readLongitude(e[4])
        lat2 = self._readLatitude(e[6])
        lon2 = self._readLongitude(e[7])

        if readDetails:
            width = self._readLength(e[0])
            # apt.dat 2013.10 (build 20131335) has 35 runways with a buggy
            # 'perimeter buoys' flag (set to -1), and all other water runways
            # have this flag set to 0 (= no buoys) → skip it.
            # perimeterBuoys = self._readPerimeterBuoysFlag(e[1])
            name1, name2 = e[2], e[5]
            length, azimuth1, azimuth2 = self.computeLengthAndAzimuth(
                lat1, lon1, lat2, lon2)
            rwy1 = WaterRunway(name1, lat1, lon1, azimuth1, length, width, None)
            rwy2 = WaterRunway(name2, lat2, lon2, azimuth2, length, width, None)
            return (lat1, lon1, lat2, lon2, length, (rwy1, rwy2))
        else:
            length = self.computeLengthForAptDigest(lat1, lon1, lat2, lon2)
            return (lat1, lon1, lat2, lon2, length, (None, None))

    def processHelipad(self, payload, readDetails=True):
        """Process a “runway” record with code 102 (i.e., a helipad)."""
        e = payload.split()
        if len(e) < 11:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(self.line))

        lat = self._readLatitude(e[1])
        lon = self._readLongitude(e[2])

        if readDetails:
            name = e[0]
            heading = self._readHeading(e[3]) # true heading in degrees
            length = self._readLength(e[4])
            width = self._readLength(e[5])
            surfaceType = self._readSurfaceType(e[6])
            shoulderSurfaceType = self._readShoulderSurfaceType(e[8])
            smoothness = self._readSmoothness(e[9])
            edgeLighting = self._readHelipadEdgeLighting(e[10])
            rwy = Helipad(name, lat, lon, heading, length, width,
                          surfaceType, shoulderSurfaceType, None, smoothness,
                          edgeLighting)
        else:
            rwy = None

        return (lat, lon, (rwy,))

    def readAirportDataUsingIndex(self, icao, index):
        """Read detailed airport data from apt.dat using an index.

        'index' should be a sequence (byteOffset, lineNb) where
        'byteOffset' points to the start of the first line defining the
        airport in apt.dat, and 'lineNb' is the corresponding line
        number (starting from 1).

        Return a tuple of the form (found, data) where:
          - 'found' is a boolean indicating whether airport data for
            the specified 'icao' was found at 'index';
          - 'data' is an Airport instance if the data was found,
            otherwise None.

        """
        logger.debug("{meth}(): entered method".format(
            meth=self.readAirportDataUsingIndex.__qualname__))
        self.file.seek(index[0])
        logger.debug("{meth}(): after the seek()".format(
            meth=self.readAirportDataUsingIndex.__qualname__))
        self.lineNb = index[1]

        code, payload = self._readRecord()

        # 1, 16, 17: land airport, seaplane base or heliport
        if code not in (1, 16, 17):
            return (False, None)

        try:
            foundIcao, type_, name, elev = self._processAirportHeader(code,
                                                                      payload)
        except UnableToParseAptDat:
            return (False, None)

        if foundIcao == icao:
            eof, nextIndex, code, payload, avgLat, avgLon, \
                landRunways, waterRunways, helipads, minRwyLength, \
                maxRwyLength, parkings = self._readAirportData(
                    calcCoords=True, readRunways=True,
                    readParkings=True, readDetails=True)
            airport = Airport(icao, name, type_, avgLat, avgLon, elev, index,
                              landRunways, waterRunways, helipads, parkings)
            return (True, airport)
        else:
            return (False, None)

    # Method largely based on makeAptDigest()
    def testAllAirports(self, outputFile):
        self.reset()
        airports = []
        eof = False
        # Start index for the first airport header (byte offset + line number)
        index = (self.file.tell(), self.lineNb)
        code, payload = self._readRecord()

        while not eof:
            if code in (1, 16, 17): # Land airport, seaplane base or heliport
                icao, type_, name, elev = self._processAirportHeader(code,
                                                                     payload)
                try:
                    eof, nextIndex, code, payload, avgLat, avgLon, \
                    landRunways, waterRunways, helipads, minRwyLength, \
                    maxRwyLength, parkings = self._readAirportData(
                        calcCoords=True, readDetails=True)
                except UnableToParseAptDat as e:
                    logger.error("in airport {}: {}".format(icao, e))
                    # Skip to the next airport
                    while True:
                        code, payload = self._readRecord()
                        if code in (1, 16, 17):
                            index = (self.file.tell(), self.lineNb)
                            break
                        elif code in (None, 99):
                            break
                else:
                    bisect.insort_right(
                        airports,
                        (icao, type_.value, name, elev, avgLat, avgLon, index,
                         landRunways, waterRunways, helipads, parkings))
                    index = nextIndex
            elif code in (None, 99): # None: EOF; 99: X-Plane's convention
                break
            else:
                raise UnableToParseAptDat(
                    self.lineNb,
                    _("unexpected row code: {code} (line: {line!r})").format(
                        code=code, line=self.line))

        with open(outputFile, "w", encoding="utf-8") as f:
            first = True
            for icao, type_, name, elev, avgLat, avgLon, index, landRunways, \
                waterRunways, helipads, parkings in airports:
                if first:
                    first = False
                    l = []
                else:
                    l = ['']

                airport = Airport(icao, name, type_, avgLat, avgLon, elev,
                                  index, landRunways, waterRunways, helipads,
                                  parkings)
                logger.notice("Final: processing airport {0} ({1})...".format(
                    icao, name))
                l.append("* {} ({})\n".format(icao, airport.name))
                for rwy in airport.runways():
                    l.append(rwy.name + '\n'
                             + textwrap.indent(rwy.tooltipText(), '  ')
                             + '\n')
                f.write('\n'.join(l))


class AptDatDigest:
    """Class for managing apt digest files."""

    # Magic number for reliable identification of FFGo's apt file format
    FORMAT_MAGIC_NB = 7856251374982125

    @classmethod
    def header(cls, aptDatSize, formatVersion=3):
        return textwrap.dedent("""\
   -*- coding: utf-8 -*-
   {prg}'s airport database, generated from FlightGear's apt.dat (or apt.dat.gz)
   Magic number: {magicNumber}
   Format version: {fmtVer}
   apt.dat size: {aptDatSize} bytes\n\n""").format(
       prg=PROGNAME, magicNumber=cls.FORMAT_MAGIC_NB, fmtVer=formatVersion,
   aptDatSize=aptDatSize)

    _magicNb_cre = re.compile(r"^Magic number: (?P<number>\d+)$")
    _fmtVersion_cre = re.compile(r"^Format version: (?P<version>\d+)$")
    _aptDatSize_cre = re.compile(r"^apt\.dat size: (?P<size>\d+) bytes$")

    @classmethod
    def _checkHeader(cls, fileObj):
        for lineNb, line in enumerate(fileObj, start=1):
            if lineNb > 3:
                raise UnrecognizedFormatForAptDigest(
                    _("unable to find the magic number"))

            if line == "\n":
                raise UnrecognizedFormatForAptDigest(
                    _("unable to find the magic number"))
            else:
                mo = cls._magicNb_cre.match(line)
                if mo and int(mo.group("number")) == cls.FORMAT_MAGIC_NB:
                    break
        else:                   # EOF reached before finding the magic number
            raise UnrecognizedFormatForAptDigest(
                _("end of file reached before finding the magic number"))

        line = fileObj.readline()
        verMo = cls._fmtVersion_cre.match(line)
        if not verMo:
            raise UnrecognizedFormatForAptDigest(
                _("could not find a valid line specifying the format version"))

        line = fileObj.readline()
        sizeMo = cls._aptDatSize_cre.match(line)
        if not sizeMo:
            raise UnrecognizedFormatForAptDigest(
                _("could not find a valid line specifying the apt.dat size"))

        return map(int, (verMo.group("version"), sizeMo.group("size")))

    @classmethod
    def read(cls, path):
        """Read an apt digest file.

        Return a tuple of the form (aptDatSize, airports) where:
          - 'aptDatSize' is an integer indicating the size in bytes of
            the uncompressed apt.dat file from which the digest file in
            'path' was built;
          - 'airports' is a dictionary whose keys are ICAO codes and
            values AirportStub instances for the corresponding airports.

        """
        airports = {}
        logger.info("Opening {prg}'s apt digest file ('{aptDigest}') for "
                    "reading".format(prg=PROGNAME, aptDigest=path))

        with open(path, "r", encoding="utf-8") as f:
            formatVersion, aptDatSize = cls._checkHeader(f)
            if formatVersion != 3:
                raise UnrecognizedFormatForAptDigest(
                    _("format version number {num} not supported").format(
                    num=formatVersion))

            if f.readline() != "\n":
                raise UnrecognizedFormatForAptDigest(
                    _("header not terminated by a blank line"))

            while True:
                line = f.readline()
                if not line:
                    break

                try:
                    l = line[:-1].split('\0')
                    icao = l[0]
                    name = l[1]
                    type_ = AirportType(int(l[2]))
                    lat, lon = map(misc.DecimalCoord, l[3:5])
                    nbLandRunways, nbWaterRunways, nbHelipads = map(
                        int, l[5].split(';'))

                    if l[6]:
                        minRwyLength, maxRwyLength = map(
                            float, l[6].split(';'))
                    else:
                        # The “airport” has no real runway (one can hope it has
                        # helipads!)
                        minRwyLength, maxRwyLength = None, None

                    # Byte offset and line number (2-tuple)
                    indexInAptDat = tuple(map(int, l[7].split(';')))
                except Exception as e: # could be refined a little bit...
                    raise UnableToParseAptDigest() from e

                airports[icao] = AirportStub(
                    icao, name, type_, lat, lon, nbLandRunways, nbWaterRunways,
                    nbHelipads, minRwyLength, maxRwyLength, indexInAptDat)

        return (aptDatSize, airports)
