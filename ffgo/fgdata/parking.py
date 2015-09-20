# parking.py --- Handle FlightGear parking data
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import re
from xml.etree import ElementTree

from ..constants import PROGNAME
from .. import misc
from ..logging import logger


class error(Exception):
    pass


# cf. FGAirportDynamicsXMLLoader::startParking() in
# src/Airports/dynamicloader.cxx of the FlightGear source code (version 3.7)
class Parking:
    """Class for parsing and representing FlightGear parking data."""

    def __init__(self, index=0, type='', name='', number='',
                 lat=None, lon=None, heading=0.0, radius=1.0,
                 airlineCodes=(), pushBackRoute=0):
        self._attrs = ("index", "name", "number", "type", "lat", "lon",
                       "heading", "radius", "airlineCodes", "pushBackRoute")
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
    def _setAttr(cls, d, parkingElt, attr, conv=None):
        if conv is None:
            conv = lambda x: x

        val = parkingElt.get(attr)
        if val is not None:
            try:
                d[attr] = conv(val)
            except ValueError as e:
                raise error(_(
                    "invalid value for the {attr!r} attribute: {val!r}").format(
                        attr=attr, val=val)) from e

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
        for attr, conv in (("index", int),
                           ("type", None),
                           ("name", None),
                           ("number", None),
                           ("lat", misc.mixedToDecimalCoords),
                           ("lon", misc.mixedToDecimalCoords),
                           ("heading", float),
                           ("radius", cls._convRadius),
                           ("airlineCodes", cls._splitAirlineCodes),
                           ("pushBackRoute", int)):
            cls._setAttr(attrs, parkingElt, attr, conv)

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


def readGroundnetFile(xmlFilePath):
    """Read parking positions from XML file."""
    logger.info("Reading parking positions from '{}'".format(xmlFilePath))
    res = {}

    tree = ElementTree.parse(xmlFilePath)
    root = tree.getroot()

    for eltName in ('parkingList', 'parkinglist'):
        parking_list = root.find(eltName)
        if parking_list is not None:
            break
    else:
        return res

    parkings = {}

    for pElt in parking_list.iterfind('Parking'):
        try:
            p = Parking.fromElement(pElt)
        except error as e:
            logger.error(_("while parsing '{file}': {errmsg}").format(
                file=xmlFilePath, errmsg=e))
            message = _('Error parsing a groundnet file')
            detail = _("In '{file}': {errmsg}.").format(
                file=xmlFilePath, errmsg=e)
            showerror(_('{prg}').format(prg=PROGNAME), message, detail=detail)
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

    return res
