# parking.py --- Handle FlightGear parking data
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import re
import enum
from xml.etree import ElementTree
import locale
import textwrap

from ..constants import PROGNAME
from .. import misc
from ..misc import normalizeHeading
from ..logging import logger


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
class ParkingSource(enum.Enum):
    """Indicate where parking metadata comes from."""
    groundnet, apt_dat = range(2)


# cf. FGAirportDynamicsXMLLoader::startParking() in
# src/Airports/dynamicloader.cxx of the FlightGear source code (version 3.7)
class Parking:
    """Class for parsing and representing FlightGear parking data."""

    def __init__(self, index=0, type='', name='', number='',
                 lat=None, lon=None, heading=0.0, radius=1.0,
                 airlineCodes=(), pushBackRoute=0,
                 source=ParkingSource.groundnet):
        self._attrs = ("index", "name", "number", "type", "lat", "lon",
                       "heading", "radius", "airlineCodes", "pushBackRoute",
                       "source")
        for attr in self._attrs:
            setattr(self, attr, locals()[attr])

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def fullName(self):
        return self.name + self.number

    def __str__(self):
        return self.fullName()

    @classmethod
    def _setAttr(cls, d, parkingElt, attr, conv=None, condition=None):
        if conv is None:
            conv = lambda x: x

        val = parkingElt.get(attr)
        if val is not None:
            try:
                converted = conv(val)
            except ValueError as e:
                raise error(_(
                    "invalid value for the {attr!r} attribute: {val!r}").format(
                        attr=attr, val=val)) from e
            else:
                if condition is None or condition(converted):
                    d[attr] = converted

    @classmethod
    def _convRadius(cls, radiusStr):
        try:
            i = radiusStr.index('M')
        except ValueError:
            i = len(radiusStr)

        return float(radiusStr[:i])

    @classmethod
    def _splitAirlineCodes(cls, airlineCodes):
        l = [ s.strip() for s in airlineCodes.split(',') ]
        airlines = set()

        # Don't include empty names and duplicates that are in 'l'
        for s in l:
            if s:
                airlines.add(s)

        return sorted(airlines)

    @classmethod
    def fromElement(cls, parkingElt):
        attrs = {}

        # Some parking positions have no 'number' attribute
        for attr, conv, condition in (
                ("index", int, None),
                ("type", None, None),
                ("name", None, None),
                ("number", None, None),
                ("lat", misc.mixedToDecimalCoords, None),
                ("lon", misc.mixedToDecimalCoords, None),
                ("heading", float, None),
                ("radius", cls._convRadius, None),
                ("airlineCodes", cls._splitAirlineCodes, None),
                ("pushBackRoute", int, lambda n: (n > 0))):
            cls._setAttr(attrs, parkingElt, attr, conv, condition)

        return cls(**attrs)

    _fullNameSort_cre = re.compile(r"(\d+|[^\d]+)")

    def fullNameSortKey(self):
        # For a parking fullName() such as "A30B.25def50", this function
        # returns ['A', 30, 'B.', 25, 'def', 50]. This is designed to correctly
        # sort Parking elements with a 'name' attribute such as "A9" or "A10"
        # and an empty or non-existent 'number' attribute.
        l = []

        for mo in self._fullNameSort_cre.finditer(self.fullName()):
            s = mo.group(0)
            l.append(int(s) if s[0].isdigit() else s)

        # int and str cannot be compared, so make sure the list always starts
        # with a string.
        if l and isinstance(l[0], int):
            l.insert(0, "")

        return l

    def tooltipText(self):
        """Prepare the tooltip for an airport parking position."""
        l = []

        if abs(self.radius - round(self.radius)) < 0.01:
            radiusStr = locale.format("%d", round(self.radius))
        else:
            radiusStr = locale.format("%.02f", self.radius)
        l.append(
            pgettext('parking position', 'Radius: {} m').format(radiusStr))

        if self.airlineCodes:
            s = pgettext('parking position', 'Airlines: {}').format(
                ', '.join(self.airlineCodes))
            l.append(textwrap.fill(s, width=50, subsequent_indent='  '))

        l.append(pgettext('parking position', 'Latitude: {}').format(self.lat))
        l.append(pgettext('parking position', 'Longitude: {}').format(self.lon))

        trueHeading = normalizeHeading(self.heading) # rounding
        if magField is not None:
            # Computation using the heading *before* it is rounded
            magHeading = normalizeHeading(
                self.heading - magField.decl(self.lat, self.lon))
            s = pgettext('parking position',
                         "Magnetic heading: {mag} (true: {true})").format(
                mag=magHeading, true=trueHeading)
        else:
            s = pgettext('parking position', "True heading: {}").format(
                trueHeading)
        l.append(s)

        return '\n'.join(l)


def readGroundnetFile(xmlFilePath):
    """Read parking positions from XML file."""
    logger.info("Reading parking positions from '{}'".format(xmlFilePath))
    res = {}
    exceptions = []             # list of problems found in the groundnet file

    tree = ElementTree.parse(xmlFilePath)
    root = tree.getroot()

    for eltName in ('parkingList', 'parkinglist'):
        parking_list = root.find(eltName)
        if parking_list is not None:
            break
    else:
        return (res, exceptions)

    parkings = {}

    for pElt in parking_list.iterfind('Parking'):
        try:
            p = Parking.fromElement(pElt)
        except error as e:
            logger.error(_("while parsing '{file}': {errmsg}").format(
                file=xmlFilePath, errmsg=e))
            exceptions.append(e)
            continue

        if not str(p):
            logger.warning(_("'{file}': empty parking name (index='{idx}')")
                           .format(file=xmlFilePath, idx=p.index))
        elif str(p) in parkings:
            logger.warning(
                _("'{file}': duplicate parking name '{parkName}' "
                  "(index='{idxDup}'); keeping the first found only "
                  "(index='{idx1}')").format(
                      file=xmlFilePath, parkName=p, idxDup=p.index,
                      idx1=parkings[str(p)].index))
        else:
            parkings[str(p)] = p

    for p in parkings.values():
        if not p.type in res:
            res[p.type] = []

        # We have already removed the eventual duplicates
        res[p.type].append(p)

    for parkList in res.values():
        # Sort parking names properly (A1 < A2 < ... A9 < A10, even if the
        # number is part of the 'name' attribute). Also handles weird stuff
        # such as A10BCD9ef.12, using the integral and non-integral parts
        # as successive sort keys.
        parkList.sort(key=Parking.fullNameSortKey)

    return (res, exceptions)
