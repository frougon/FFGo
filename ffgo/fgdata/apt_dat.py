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

from .. import constants
from ..constants import PROGNAME
from .. import misc
from ..logging import logger
from .airport import Airport, AirportStub, AirportType, Runway, RunwayType
from . import parking
from .parking import ParkingSource

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
        self.lineNb = lineNb
        self.message = message

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

    _formatLine_cre = re.compile(r"""(?P<version>\d+)
                                     [ \t]+
                                     Version
                                     \b""", re.VERBOSE)
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
            (an index allows to do that efficiently).

        """
        if outputFile is None:
            outputFile = constants.APT

        self.reset()
        airports = []
        eof = False
        index = self.file.tell() # start index for this airport header
        code, payload = self._readRecord()

        while not eof:
            if code in (1, 16, 17): # Land airport, seaplane base or heliport
                icao, type_, name, elev = self._processAirportHeader(code,
                                                                     payload)
                eof, nextIndex, code, payload, avgLat, avgLon, runways, \
                    parkings = self._readAirportData(calcCoords=True)
                # This should be better than sorting the list once complete
                # from an algorithmic point of view, however the difference is
                # hardly measurable with apt.dat 2013.10, build 20131335,
                # containing 34074 airports (the sort() taking about 0.04 s).
                bisect.insort_right(airports,
                                    (icao, type_.value, name, elev, avgLat,
                                     avgLon, index))
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
            # 25 seconds for 34074 airprts).
            for icao, type_, name, elev, avgLat, avgLon, index in airports:
                f.write(
                    '\0'.join([icao, name, str(type_),
                               avgLat.precisionRepr(), avgLon.precisionRepr(),
                               repr(index)])
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
                         readParkings=False):
        runways = []
        avgLat, avgLon = None, None
        # Will give the coordinates of the centroid of all runway ends +
        # helipads of the airport (each runway has a sort of “double weight”
        # because of its two ends, contrary to a helipad).
        latSum, lonSum = misc.DecimalCoord(0.0), misc.DecimalCoord(0.0)
        parkings = {}
        eof = False

        while True:
            index = self.file.tell()
            code, payload = self._readRecord()

            if code in (1, 16, 17): # Land airport, seaplane base or heliport
                break
            elif code in (None, 99):    # None: EOF; 99: X-Plane's convention
                eof = True
                break
            else:
                if calcCoords or readRunways:
                    isRwyRecord, latSum0, lonSum0 = \
                        self._processPotentialRunwayRow(code, payload, runways)
                    if isRwyRecord:
                        latSum += latSum0
                        lonSum += lonSum0

                if readParkings:
                    self._processPotentialParkingRow(code, payload, parkings)

        if calcCoords:
            n = len(runways)
            if n > 0:
                avgLat, avgLon = latSum / n, lonSum / n

        if readRunways:
            runways.sort(key=lambda runway: runway.name)

        if readParkings:
            for parkList in parkings.values():
                parkList.sort(key=parking.Parking.fullNameSortKey)

        return (eof, index, code, payload, avgLat, avgLon, runways, parkings)

    def _processPotentialRunwayRow(self, code, payload, runways):
        """Read runway information from (code, payload) if applicable.

        'runways' should behave like a list and is *modified in-place*,
        the runways found being appended.

        Return a tuple of the form (isRwyRecord, latSum, lonSum) where:
          - 'isRwyRecord' is a boolean indicating whether 'code' is
            recognized as a runway code;
          - 'latSum' (resp. 'lonSum') is the sum of the latitudes (resp.
            longitudes) of the runway ends defined by (code, payload)
            (i.e., typically two opposite runway ends for one “physical
            runway”, but a helipad also counts as one runway end). This
            can be used as a basis for computing the “centroid” of an
            airport, so to speak.

        This method is a no-op if 'code' doesn't correspond to an
        apt.dat runway (helipads counting as runways in this context).

        """
        isRwyRecord = True

        if code == 10:  # Runway or taxiway from the APT810 spec (old)
            e = payload.split()
            # 'xxx' would indicate a taxiway
            if len(e) >= 3 and e[2] != 'xxx':
                # “Latitude/longitude [...] of runway or
                # taxiway segment center” according to the APT810 spec
                lat, lon, rwys = self._processV810Runway(e)
                latSum = lat*2 # These coordinates count for the two
                lonSum = lon*2 # opposite runway ends.
            else:
                isRwyRecord = False
        elif code == 100:
            lat1, lon1, lat2, lon2, rwys = self.processLandRunway(
                payload)
            latSum = lat1 + lat2
            lonSum = lon1 + lon2
        elif code == 101:
            lat1, lon1, lat2, lon2, rwys = self.processWaterRunway(
                payload)
            latSum = lat1 + lat2
            lonSum = lon1 + lon2
        elif code == 102:
            latSum, lonSum, rwys = self.processHelipad(payload)
        else:
            isRwyRecord = False

        if isRwyRecord:
            runways.extend(rwys)
        else:
            latSum = lonSum = None # no runway found

        return (isRwyRecord, latSum, lonSum)

    _v810Helipad_cre = re.compile(r"(?P<name>H(?P<number>\d+))x$")

    def processV810Runway(self, e):
        if len(e) < 14:
            raise UnableToParseAptDat(
                self.lineNb,
                _("not enough fields in record: {!r}").format(
                    self.line))

        lat = self._readLatitude(e[0])
        lon = self._readLongitude(e[1])
        name = e[2]

        mo = self._v810Helipad_cre.match(name) # Helipad?
        if mo:
            rwy = Runway(mo.group("name"), RunwayType.helipad)
            runways = (rwy,)
        else:
            try:
                surfaceCode = int(e[9])
            except ValueError as e:
                raise UnableToParseAptDat(
                    self.lineNb,
                    _("invalid runway surface code: {code!r} (line: {line!r})")
                    .format(code=e[9], line=self.line))

            if surfaceCode == 13:
                rwyType = RunwayType.waterRunway
            else:
                rwyType = RunwayType.landRunway

            if name.endswith('x'): # rwy with no L, R, C, S... suffix
                name = name[:-1]

            otherRwy = self.otherRunway(name)
            if otherRwy is not None:
                # Two runways, differing in heading by 180°
                runways = (Runway(name, rwyType), Runway(otherRwy, rwyType))
            else:
                # Should not happen if apt.dat conforms to the v810 spec
                runways = (Runway(name, rwyType))

        return (lat, lon, runways)

    def otherRunway(self, rwy):
        if not rwy.startswith('H'):
            prefix = self.computeRwyHeading(rwy)
            suffix = self.changeRwyLeftRight(rwy)
            return prefix + suffix
        else:
            return None

    def computeRwyHeading(self, rwy):
        number = self.getRwyHeading(rwy)
        if 18 < number <= 36:
            other = number - 18
        elif 0 < number <= 18:
            other = number + 18
        else:
            raise UnableToParseAptDat(
                self.lineNb,
                _("unexpected runway name: {rwy!r} "
                  "(line: {line!r})").format(rwy=rwy, line=self.line))

        return "{:02d}".format(other)

    _rwyNum_cre = re.compile(r"(?P<num>\d+)")

    def getRwyHeading(self, rwy):
        mo = self._rwyNum_cre.match(rwy)
        if not mo:
            raise UnableToParseAptDat(
                self.lineNb,
                _("runway name not starting with digits: {rwy!r} "
                  "(line: {line!r})").format(rwy=rwy, line=self.line))

        return int(mo.group("num"))

    def changeRwyLeftRight(self, rwy):
        suffix = ''
        if rwy.endswith('L'):
            suffix = 'R'
        elif rwy.endswith('R'):
            suffix = 'L'
        elif rwy.endswith('C'):
            suffix = 'C'
        return suffix

    def processLandRunway(self, payload):
        """Process a runway record with code 100."""
        e = payload.split()
        lat1 = self._readLatitude(e[8])
        lon1 = self._readLongitude(e[9])
        lat2 = self._readLatitude(e[17])
        lon2 = self._readLongitude(e[18])
        rwys = (Runway(e[7], RunwayType.landRunway),
                Runway(e[16], RunwayType.landRunway))

        return (lat1, lon1, lat2, lon2, rwys)

    def processWaterRunway(self, payload):
        """Process a runway record with code 101."""
        e = payload.split()
        lat1 = self._readLatitude(e[3])
        lon1 = self._readLongitude(e[4])
        lat2 = self._readLatitude(e[6])
        lon2 = self._readLongitude(e[7])
        rwys = (Runway(e[2], RunwayType.waterRunway),
                Runway(e[5], RunwayType.waterRunway))

        return (lat1, lon1, lat2, lon2, rwys)

    def processHelipad(self, payload):
        """Process a “runway” record with code 102 (i.e., a helipad)."""
        e = payload.split()
        lat = self._readLatitude(e[1])
        lon = self._readLongitude(e[2])
        rwys = (Runway(e[0], RunwayType.helipad),)

        return (lat, lon, rwys)

    def readAirportDataUsingIndex(self, icao, index):
        """Read detailed airport data from apt.dat using an index.

        Return a tuple of the form (found, data) where:
          - 'found' is a boolean indicating whether airport data for
            the specified 'icao' was found at 'index';
          - 'data' is an Airport instance if the data was found,
            otherwise None.

        """
        logger.debug("{meth}(): entered method".format(
            meth=self.readAirportDataUsingIndex.__qualname__))
        self.file.seek(index)
        logger.debug("{meth}(): after the seek()".format(
            meth=self.readAirportDataUsingIndex.__qualname__))

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
            eof, nextIndex, code, payload, avgLat, avgLon, runways, parkings = \
                 self._readAirportData(calcCoords=True, readRunways=True,
                                       readParkings=True)
            airport = Airport(icao, name, type_, avgLat, avgLon, elev, index,
                              runways, parkings)
            return (True, airport)
        else:
            return (False, None)


class AptDatDigest:
    """Class for managing apt digest files."""

    # Magic number for reliable identification of FFGo's apt file format
    FORMAT_MAGIC_NB = 7856251374982125

    @classmethod
    def header(cls, aptDatSize, formatVersion=1):
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
            if formatVersion != 1:
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
                    indexInAptDat = int(l[5])
                except Exception as e: # could be refined a little bit...
                    raise UnableToParseAptDigest() from e

                airports[icao] = AirportStub(icao, name, type_, lat, lon,
                                             indexInAptDat)

        return (aptDatSize, airports)
