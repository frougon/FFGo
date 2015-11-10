# airport.py --- Handle FlightGear airport data (including runways)
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import enum


class error(Exception):
    pass


@enum.unique
class AirportType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    landAirport = 1
    seaplaneBase = 16
    heliport = 17

airportTypeStr = {
    AirportType.landAirport: _("Land airport"),
    AirportType.seaplaneBase: _("Seaplane base"),
    AirportType.heliport: _("Heliport") }


class Airport:
    """Class for representing airport data."""

    def __init__(self, icao, name, type, lat, lon, elevation, indexInAptDat,
                 runways, parkings):
        self._attrs = ("icao", "name", "type", "lat", "lon", "elevation",
                       "indexInAptDat", "runways", "parkings")
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return "{} ({})".format(self.name, self.icao)


class AirportStub:
    """Low-memory class for representing limited airport data.

    This class can hold airport metadata present in the apt digest file,
    but no more. The use of the __slots__ special class attribute, given
    the large number of airports loaded on startup (34074 in my test),
    allows one to save about 6 MBytes of memory on Linux (amd64, with
    Python 3.4.3), which is 9 % of the resident memory used by FFGo
    (M_RESIDENT, abbreviated “RES” in htop) with an AirportStub class
    derived from Airport or a standalone AirportStub class defined
    without __slots__.

    Note: omitting the __str__() and __repr__() method definitions in
          this class does not bring any measureable memory saving.

    """

    __slots__ = ("icao", "name", "type", "lat", "lon", "indexInAptDat")

    def __init__(self, icao, name, type, lat, lon, indexInAptDat):
        for attr in self.__slots__:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self.__slots__ ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return "{} ({})".format(self.name, self.icao)


@enum.unique
class RunwayType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    landRunway = 100
    waterRunway = 101
    helipad = 102

def runwayTypeStr(rwyType, num):
    # XXX Plurals could be handled with ngettext, but for this we probably need
    # to have access to the GNUTranslations instance or something like that.
    if num > 1:
        d = {RunwayType.landRunway: _("Land runways"),
             RunwayType.waterRunway: _("Water runways"),
             RunwayType.helipad: _("Helipads")}
    else:
        d = {RunwayType.landRunway: _("Land runway"),
             RunwayType.waterRunway: _("Water runway"),
             RunwayType.helipad: _("Helipad")}

    return d[rwyType]


class Runway:
    """Class for representing runway data."""

    def __init__(self, name, type):
        self._attrs = ("name", "type")
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return self.name
