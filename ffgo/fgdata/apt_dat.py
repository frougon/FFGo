# apt_dat.py --- Parse X-Plane/FlightGear's apt.dat file
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

from .. import constants
from ..constants import PROGNAME
from .. import misc
from ..logging import logger
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


class AptDat:
    def __init__(self, path):
        self.path = os.path.abspath(path)

    def open(self, mode="rt", encoding="latin_1", errors="replace"):
        logger.info("Opening '{}' for reading".format(self.path))
        if self.path.endswith(".gz"):
            self.file = gzip.open(self.path, mode=mode, encoding=encoding,
                                  errors=errors)
        else:
            self.file = open(self.path, mode=mode, encoding=encoding,
                             errors=errors)

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
        while True:
            self.lineNb += 1
            line = self.file.readline()
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
        line = self._readline()
        if not line:
            raise UnableToParseAptDat(
                self.lineNb,
                _("EOF reached while looking for the first non-empty line"))
        if len(line) != 1:     # should be either 'I' (“PC”) or 'A' (“MAC”)
            raise UnableToParseAptDat(
                self.lineNb,
                _("first non-empty line should contain exactly one character"))

        line = self._readline()
        if not line:
            raise UnableToParseAptDat(
                self.lineNb,
                _("EOF reached while looking for the version of the format"))

        mo = self._formatLine_cre.match(line)
        if not mo:
            raise UnableToParseAptDat(
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
        self.file.seek(self.endOfHeader, 0)
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

    def readParkingForIcao(self, icao):
        self.reset()
        res = {}
        finished = False

        while not finished:
            code, rest = self._readRecord()

            if code is None:    # EOF
                break
            elif code in (1, 16, 17): # Land airport, seaplane base or heliport
                l = rest.split(None, maxsplit=4)
                if len(l) < 5:
                    raise UnableToParseAptDat(
                        self.lineNb,
                        _("not enough fields in record: {!r}").format(
                            self.line))

                if l[3].upper() != icao:
                    continue

                while not finished:
                    code, rest = self._readRecord()

                    if code is None: # EOF
                        finished = True
                        break
                    elif code == 15: # Startup location (v850, deprecated)
                        l = rest.split(None, maxsplit=3)
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

                        if "" not in res:
                            res[""] = []

                        res[""].append(p) # flight type unknown for these parks
                    elif code == 1300:    # Airport location (v1000, deprecates
                                          # code 15
                        l = rest.split(None, maxsplit=5)
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

                        if locType not in res:
                            res[locType] = []

                        res[locType].append(p)
                    elif code in (1, 16, 17):
                        finished = True

        for parkList in res.values():
            parkList.sort(key=parking.Parking.fullNameSortKey)

        return res
