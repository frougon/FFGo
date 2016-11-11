# airport.py --- Handle FlightGear airport data (including runways)
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import enum
import locale
import textwrap
import itertools

from ..misc import normalizeHeading


def setupTranslationHelper(config):
    global pgettext, ngettext, npgettext
    from .. import misc

    translationHelper = misc.TranslationHelper(config)
    pgettext = translationHelper.pgettext
    ngettext = translationHelper.ngettext
    npgettext = translationHelper.npgettext

def setupEarthMagneticFieldProvider(provider):
    global magField
    magField = provider


class error(Exception):
    pass


@enum.unique
class AirportType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    landAirport = 1
    seaplaneBase = 16
    heliport = 17

    def capitalizedName(self):
        d = {
            AirportType.landAirport: _("Land airport"),
            AirportType.seaplaneBase: _("Seaplane base"),
            AirportType.heliport: _("Heliport")
        }
        return d[self]


class Airport:
    """Class for representing airport data."""

    def __init__(self, icao, name, type, lat, lon, elevation, airportIndex,
                 landRunways, waterRunways, helipads, parkings):
        """Initialize an Airport instance.

        'airportIndex' should be a tuple (aptDatIndex, byteOffset,
        lineNb) where 'airportIndex' is an index (in some
        externally-defined list) of the apt.dat file this airport data
        comes from, 'byteOffset' points to the start of the first line
        defining the airport in said apt.dat file, and 'lineNb' is the
        corresponding line number (starting from 1).

        """
        self._attrs = ("icao", "name", "type", "lat", "lon", "elevation",
                       "airportIndex", "landRunways", "waterRunways",
                       "helipads", "parkings")
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return "{} ({})".format(self.name, self.icao)

    def runways(self):
        return itertools.chain(self.landRunways, self.waterRunways,
                               self.helipads)

    def tooltipText(self):
        d = {}
        for rwy in self.runways():
            if rwy.type not in d:
                d[rwy.type] = []

            d[rwy.type].append(rwy.name)

        rl = []         # one element per runway type
        for rwyType in sorted(d.keys(), key=lambda x: x.value):
            runwayTypeName = rwyType.capitalizedName(len(d[rwyType]))

            s = _("{rwyType}: {runways}").format(
                rwyType=runwayTypeName,
                runways=", ".join(sorted(d[rwyType])))
            rl.append(
                textwrap.fill(s, width=40, subsequent_indent='  '))

        l = [self.type.capitalizedName(),
              _("Latitude: {latitude}").format(latitude=self.lat),
              _("Longitude: {longitude}").format(longitude=self.lon),
              _("Elevation: {elev_feet} ft ({elev_meters} m)").format(
                  elev_feet=locale.format("%d", round(self.elevation)),
                  elev_meters=locale.format("%.01f", self.elevation*0.3048))]

        if magField is not None:
            magVar = locale.format("%.01f", magField.decl(self.lat, self.lon))
            l.append(_("Magnetic variation: {}°").format(magVar))

        return '\n'.join(l + rl)


class AirportStub:
    """Low-memory class for representing limited airport data.

    This class mostly holds airport metadata present in the apt digest
    file. More precisely, the criterion is: if some attribute must be
    looked up quickly for a large number of airports, it should be in
    this class. When data is accessed on user demand, e.g., for one
    airport at a time, and waiting one tenth of a second for it isn't a
    problem, then such data more likely belongs to the Airport class.
    This is because AirportStub instances are created and held into
    memory for *all* airports listed in apt.dat.gz, as long as FFGo is
    running, whereas Airport instances are created on-demand.

    The use of the __slots__ special class attribute, given
    the large number of airports loaded on startup (34074 in my test),
    allows one to save about 6 MBytes of memory on Linux (amd64, with
    Python 3.4.3), which is 9 % of the resident memory used by FFGo
    (M_RESIDENT, abbreviated “RES” in htop) with an AirportStub class
    derived from Airport or a standalone AirportStub class defined
    without __slots__.

    Note: omitting the __str__() and __repr__() method definitions in
          this class does not bring any measureable memory saving.

    """

    __slots__ = ("icao", "name", "type", "lat", "lon", "nbLandRunways",
                "nbWaterRunways", "nbHelipads", "minRwyLength", "maxRwyLength",
                 "airportIndex", "datesOfUse", "useCountForShow")

    def __init__(self, icao, name, type, lat, lon, nbLandRunways,
                 nbWaterRunways, nbHelipads, minRwyLength, maxRwyLength,
                 airportIndex, datesOfUse=None, useCountForShow=0):
        """Initialize an AirportStub instance.

        'airportIndex' should be a tuple (aptDatIndex, byteOffset,
        lineNb) where 'airportIndex' is an index (in some
        externally-defined list) of the apt.dat file this airport data
        comes from, 'byteOffset' points to the start of the first line
        defining the airport in said apt.dat file, and 'lineNb' is the
        corresponding line number (starting from 1).

        The AirportStatsManager class maintains a count of the number of
        days during which the airport has been visited at least once, in
        a customizable period (cf. Config.airportStatsShowPeriod). This
        count is available as the 'useCountForShow' of this class. The
        initial default value 0 will be overridden by
        AirportStatsManager.load() if the file where the underlying
        dates are stored between FFGo runs is present.

        """
        for attr in self.__slots__:
            setattr(self, attr, locals()[attr])

        if datesOfUse is None:
            # Dates at which the airport has been visited (subject to
            # expiry; cf. the 'stats_manager' module). Will be
            # overridden by AirportStatsManager.load() if the file where
            # these dates are normally stored between FFGo runs is
            # present.
            self.datesOfUse = [] # effective default value

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self.__slots__ ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return "{} ({})".format(self.name, self.icao)


@enum.unique
class SurfaceType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    asphalt = 1
    concrete = 2
    turfOrGrass = 3
    dirt = 4
    gravel = 5
    dryLakebed = 12
    water = 13
    snowOrIce = 14
    transparent = 15

    def __str__(self):
        d = {
            SurfaceType.asphalt: pgettext("surface type", "asphalt"),
            SurfaceType.concrete: pgettext("surface type", "concrete"),
            SurfaceType.turfOrGrass: pgettext("surface type",
                                                      "turf or grass"),
            SurfaceType.dirt: pgettext("surface type", "dirt"),
            SurfaceType.gravel: pgettext("surface type", "gravel"),
            SurfaceType.dryLakebed: pgettext("surface type", "dry lake bed"),
            SurfaceType.water: pgettext("surface type", "water"),
            SurfaceType.snowOrIce: pgettext("surface type", "snow or ice"),
            SurfaceType.transparent: pgettext("surface type", "transparent")
        }
        return d[self]


@enum.unique
class V810SurfaceType(enum.Enum):
    # Codes used in apt.dat (v810 spec)
    asphalt = 1
    concrete = 2
    turfOrGrass = 3
    dirt = 4
    gravel = 5
    asphaltHelipad = 6
    concreteHelipad = 7
    turfHelipad = 8
    dirtHelipad = 9
    asphaltTaxiway = 10
    concreteTaxiway = 11
    dryLakebed = 12
    water = 13

    def __str__(self):
        # The obsolete codes should not be visible to users → don't
        # mark the corresonding strings as translatable.
        d = {
            V810SurfaceType.asphalt: str(SurfaceType.asphalt),
            V810SurfaceType.concrete: str(SurfaceType.concrete),
            V810SurfaceType.turfOrGrass: str(SurfaceType.turfOrGrass),
            V810SurfaceType.dirt: str(SurfaceType.dirt),
            V810SurfaceType.gravel: str(SurfaceType.gravel),
            V810SurfaceType.asphaltHelipad: "asphalt helipad",
            V810SurfaceType.concreteHelipad: "concrete helipad",
            V810SurfaceType.turfHelipad: "turf helipad",
            V810SurfaceType.dirtHelipad: "dirt helipad",
            V810SurfaceType.asphaltTaxiway: "asphalt taxiway",
            V810SurfaceType.concreteTaxiway: "concrete taxiway",
            V810SurfaceType.dryLakebed: str(SurfaceType.dryLakebed),
            V810SurfaceType.water: str(SurfaceType.water),
        }
        return d[self]

    def isWaterRunway(self):
        return (self is V810SurfaceType.water)

    def isHelipad(self):
        return (self in (V810SurfaceType.asphaltHelipad,
                         V810SurfaceType.concreteHelipad,
                         V810SurfaceType.turfHelipad,
                         V810SurfaceType.dirtHelipad))

    def isTaxiway(self):
        return (self in (V810SurfaceType.asphaltTaxiway,
                         V810SurfaceType.concreteTaxiway))

    def v1000Equivalent(self):
        """Map v810 surface types to v1000 surface types."""
        mapping = {6: SurfaceType.asphalt,
                   7: SurfaceType.concrete,
                   8: SurfaceType.turf,
                   9: SurfaceType.dirt,
                   10: SurfaceType.asphalt,
                   11: SurfaceType.concrete}

        if self.value in range(1, 6) or self.value in (12, 13):
            res = SurfaceType(self.value) # same as in the v1000 spec
        elif self.value in mapping:
            res = mapping[self.value]
        else:
            raise ValueError(
                _("invalid v810 surface code: {0!r}").format(self.value))

        return res


@enum.unique
class ShoulderSurfaceType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    none = 0
    asphalt = 1
    concrete = 2

    def __str__(self):
        d = {
            ShoulderSurfaceType.none:
              pgettext("runway/helipad shoulder surface type", "none"),
            ShoulderSurfaceType.asphalt:
              pgettext("runway/helipad shoulder surface type", "asphalt"),
            ShoulderSurfaceType.concrete:
              pgettext("runway/helipad shoulder surface type", "concrete")
        }
        return d[self]


@enum.unique
class RunwayType(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    landRunway = 100
    waterRunway = 101
    helipad = 102

    def capitalizedName(self, num):
        d = {RunwayType.landRunway:
               ngettext("Land runway", "Land runways", num),
             RunwayType.waterRunway:
               ngettext("Water runway", "Water runways", num),
             RunwayType.helipad:
               ngettext("Helipad", "Helipads", num)
        }
        return d[self]


@enum.unique
class RunwayMarkings(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    none = 0
    visual = 1
    nonPrecisionApproach = 2
    precisionApproach = 3
    ukStyleNonPrecisionApproach = 4
    ukStylePrecisionApproach = 5

    def __str__(self):
        d = {
            RunwayMarkings.none:
              pgettext("runway markings", "none"),
            RunwayMarkings.visual:
              pgettext("runway markings", "visual"),
            RunwayMarkings.nonPrecisionApproach:
              pgettext("runway markings", "non-precision approach"),
            RunwayMarkings.precisionApproach:
              pgettext("runway markings", "precision approach"),
            RunwayMarkings.ukStyleNonPrecisionApproach:
              pgettext("runway markings", "UK-style non-precision approach"),
            RunwayMarkings.ukStylePrecisionApproach:
              pgettext("runway markings", "UK-style precision approach")
        }
        return d[self]


class RunwayBase:
    """Base class for specific classes representing runway data."""

    def __init__(self, name, lat, lon, type):
        self._attrs = ["name", "lat", "lon", "type"]
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return "{} ({})".format(self.name, self.type)

    def formatLength(self, val):
        return locale.format("%d", round(val))

    def _addLatitude(self, l):
        if self.lat is not None:
            l.append(_("Latitude: {}").format(self.lat))

    def _addLongitude(self, l):
        if self.lon is not None:
            l.append(_("Longitude: {}").format(self.lon))

    def _addHeading(self, l):
        if self.heading is not None:
            trueHeading = normalizeHeading(self.heading) # rounding

            if (magField is not None and self.lat is not None and
                self.lon is not None):
                # Computation using the heading *before* it is rounded
                magHeading = normalizeHeading(
                    self.heading - magField.decl(self.lat, self.lon))
                s = pgettext("runway/helipad",
                             "Magnetic heading: {mag} (true: {true})").format(
                    mag=magHeading, true=trueHeading)
            else:
                s = pgettext("runway/helipad",
                             "True heading: {}").format(trueHeading)

            l.append(s)

    def _addLength(self, l):
        if self.length is not None:
            length_ft = self.length / 0.3048
            l.append(_("Length: {0} m ({1} ft)").format(
                self.formatLength(self.length),
                self.formatLength(length_ft)))

    def _addWidth(self, l):
        if self.width is not None:
            width_ft = self.width / 0.3048
            l.append(_("Width: {0} m ({1} ft)").format(
                self.formatLength(self.width),
                self.formatLength(width_ft)))

    def _addSurfaceType(self, l):
        if self.surfaceType is not None:
            l.append(_("Surface type: {}").format(self.surfaceType))

    def _addShoulderSurfaceType(self, l):
        if self.shoulderSurfaceType is not None:
            l.append(_("Shoulder surface type: {}").format(
                self.shoulderSurfaceType))

    def _addRunwayMarkings(self, l):
        if self.runwayMarkings is not None:
            l.append(_("Runway markings: {}").format(self.runwayMarkings))

    def _addSmoothness(self, l):
        if self.smoothness is not None:
            l.append(_("Smoothness: {}").format(
                locale.format("%.02f", self.smoothness)))


class LandRunway(RunwayBase):
    """Class for representing land runway data."""

    def __init__(self, name, latitude, longitude, heading, length, width,
                 surfaceType, shoulderSurfaceType, runwayMarkings, smoothness):
        RunwayBase.__init__(self, name, latitude, longitude,
                            RunwayType.landRunway)
        specificAttrs = ["heading", "length", "width", "surfaceType",
                         "shoulderSurfaceType", "runwayMarkings", "smoothness"]
        for attr in specificAttrs:
            setattr(self, attr, locals()[attr])
        self._attrs = self._attrs + specificAttrs

    def tooltipText(self):
        l = [str(self.type.capitalizedName(1))]

        self._addLatitude(l)
        self._addLongitude(l)
        self._addHeading(l)
        self._addLength(l)
        self._addWidth(l)
        self._addSurfaceType(l)
        self._addShoulderSurfaceType(l)
        self._addRunwayMarkings(l)
        self._addSmoothness(l)

        return '\n'.join(l)


@enum.unique
class PerimeterBuoys(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    no = 0
    yes = 1

    def __str__(self):
        d = {
            PerimeterBuoys.no: _("no"),
            PerimeterBuoys.yes: _("yes")
        }
        return d[self]


class WaterRunway(RunwayBase):
    """Class for representing water runway data."""

    def __init__(self, name, latitude, longitude, heading, length, width,
                 perimeterBuoys):
        RunwayBase.__init__(self, name, latitude, longitude,
                            RunwayType.waterRunway)
        specificAttrs = ["heading", "length", "width", "perimeterBuoys"]
        for attr in specificAttrs:
            setattr(self, attr, locals()[attr])
        self._attrs = self._attrs + specificAttrs

    def tooltipText(self):
        l = [str(self.type.capitalizedName(1))]

        self._addLatitude(l)
        self._addLongitude(l)
        self._addHeading(l)
        self._addLength(l)
        self._addWidth(l)

        if self.perimeterBuoys is not None:
            l.append(_("Perimeter buoys: {}").format(self.perimeterBuoys))

        return '\n'.join(l)


@enum.unique
class HelipadEdgeLighting(enum.Enum):
    # Codes used in apt.dat (v1000 spec)
    no = 0
    yes = 1

    def __str__(self):
        d = {
            HelipadEdgeLighting.no: _("no"),
            HelipadEdgeLighting.yes: _("yes")
        }
        return d[self]


class Helipad(RunwayBase):
    """Class for representing helipad data."""

    def __init__(self, name, latitude, longitude, heading, length, width,
                 surfaceType, shoulderSurfaceType, runwayMarkings, smoothness,
                 edgeLighting):
        RunwayBase.__init__(self, name, latitude, longitude, RunwayType.helipad)
        specificAttrs = [
            "heading", "length", "width", "surfaceType",
            "shoulderSurfaceType", "runwayMarkings", "smoothness",
            "edgeLighting"]
        for attr in specificAttrs:
            setattr(self, attr, locals()[attr])
        self._attrs = self._attrs + specificAttrs

    def tooltipText(self):
        l = [str(self.type.capitalizedName(1))]

        self._addLatitude(l)
        self._addLongitude(l)
        self._addHeading(l)
        self._addLength(l)
        self._addWidth(l)
        self._addSurfaceType(l)
        self._addShoulderSurfaceType(l)
        self._addRunwayMarkings(l)
        self._addSmoothness(l)

        if self.edgeLighting is not None:
            l.append(_("Edge lighting: {}").format(self.edgeLighting))

        return '\n'.join(l)
