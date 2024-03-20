# stats_manager.py --- Collect, store and reload usage statistics (such as
#                      “recent” dates when each plane or airport has been used)
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import abc
import datetime
import gzip
import json

from . import constants
from .logging import logger
# This import requires the translation system [_() function] to be in
# place.
from .exceptions import FFGoException


class error(FFGoException):
    """Base class for exceptions in the stats_manager module."""
    ExceptionShortDescription = _("Error caught in the stats_manager module")

class NoSuchItem(error):
    # No translation, as this exception should not be raised directly
    ExceptionShortDescription = "No such item"

class NoSuchAircraft(NoSuchItem):
    ExceptionShortDescription = _("No such aircraft")

    def __init__(self, aircraftName, aircraftDir):
        message = _("'{aircraftName}' in '{aircraftDir}'").format(
            aircraftName=aircraftName, aircraftDir=aircraftDir)
        NoSuchItem.__init__(self, message, mayCapitalizeMsg=False)

        self.aircraftName = aircraftName
        self.aircraftDir = aircraftDir

    def __repr__(self):
        return "{}.{}({!r}, {!r})".format(__name__, type(self).__name__,
                                          self.aircraftName, self.aircraftDir)

class NoSuchAirport(NoSuchItem):
    ExceptionShortDescription = _("No such airport")

    def __init__(self, icao):
        # Simply use the ICAO code as the exception 'message' attribute
        NoSuchItem.__init__(self, icao, mayCapitalizeMsg=False)
        self.icao = icao        # for aesthetics and clarity


class StatsManagerBase(metaclass=abc.ABCMeta):
    """Abstract base class for managing usage statistics.

    The most recent dates of use of each “item” (where items can be
    airports, aircraft or anything else) are stored in json.gz format
    under constants.STATS_DIR. This class manages expiry of such data
    after a customizable period. It can also compute and update the
    number of times each item has been used during a chosen period,
    defined as the last 'n' days until today, where 'n' is a
    customizable integer.

    When stored in json.gz format (cf. self.saveFile) as well as in
    memory ('item.datesOfUse' where 'item' can be for instance an
    AirportStub or Aircraft instance), dates are stored in the form of
    their proleptic Gregorian ordinal. For any given date, this is an
    integer defined this way: January 1 of year 1 is mapped to the
    integer 1, January 2 of year 1 to 2, and so on (cf. doc of the
    Python 'datetime' module).

    Note: only integral numbers of days are supported in this scheme.


    Quick description of the JSON file formats with examples
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Sample airports.json.gz obtained with '--save-stats-in-pretty-form':

      {
          "airports": {
              "EDDF": [
                  736004
              ],
              "LFPO": [
                  736001,
                  736003,
                  736004
              ],
              "LOWI": [
                  736003
              ]
          },
          "format version": 1
      }

    This means that, during the expiry period, the EDDF airport was
    visited only once: on February 10, 2016 (as can be seen with
    datetime.date.fromordinal(736004)). Same for LOWI but the day
    before, on February 9, 2016. As for LFPO, it has been visited three
    times during the period not subject to expiry: on Feb 7, 9 and 10,
    2016). The list of dates (proleptic Gregorian ordinals) is always
    maintained in chronological order.

    This is very similar for aircrafts.json.gz:

      {
          "aircrafts": {
              "707\u0000/mm/flightgear-data/fgaddon/Aircraft/707": [
                  736004
              ],
              "ZLT-NT\u0000/mm/flightgear-data/fgaddon/Aircraft/ZLT-NT": [
                  736004
              ],
              "c172p\u0000/home/flo/flightgear/src/fgdata/Aircraft/c172p": [
                  736003
              ],
              "c172p\u0000/mm/flightgear-data/aircraft-misc/c172p": [
                  735998,
                  736000,
                  736003,
                  736004
              ],
              "ec130b4\u0000/mm/flightgear-data/aircraft-misc/ec130": [
                  736003
              ],
          },
          "format version": 1
      }

    The format is the same as for airports.json.gz, except for two
    things:
      - the main object is found under the "aircrafts" key in the
        top-level object, instead of "airports" ('self.subject' in this
        class);
      - the JSON key used to identify an aircraft is composed of the
        aircraft name and directory, separated with the character whose
        Unicode code point is 0 (\u0000).

    """

    def __init__(self, config, subject, showPeriodVar, expiryPeriodVar,
                 saveFile):
        for attr in ("config", "subject", "showPeriodVar", "expiryPeriodVar",
                     "saveFile"):
            setattr(self, attr, locals()[attr])

        # It may be that FFGo is not always run with the same airports (from
        # apt.dat files) or aircraft installed. It would be a pity to lose
        # statistic data about airports or aircraft just because they are
        # temporarily unavailable, for instance because the user (re)moved one
        # of his aircraft paths. To circumvent this problem, items loaded from
        # the json.gz file (self.saveFile) that can't be used in the
        # current state (for instance aircraft not available under the
        # configured aircraft paths anymore) are stored in this
        # dictionary. This way, the save() method will be able to store
        # them back in self.saveFile when it is called.
        self.unusedItems = {}
        # FFGo command line parameters
        self.cmdLineParams = config.cmdLineParams

    @abc.abstractmethod
    def jsonKeyToItemId(self, key):
        """
        Convert a key suitable for JSON format into something for getItem().

        The JSON format can represent “objects” that look much like
        Python dictionaries, able to store key/value pairs, but the keys
        in these objects are limited to the string type. This method
        takes an item key as used in self.saveFile and returns a Python
        object suitable for use by getItem().

        For instance, if the items managed by a concrete class derived
        from this one are airports, the ICAO code can be
        conveniently used for both JSON keys and getItem()'s argument.
        For aircraft, it's a bit more tricky because we identify an
        aircraft in FFGo by a tuple (aircraftName, aircraftDir).
        Therefore, the JSON key for an aircraft has to unambiguously
        represent such a tuple in string form. A simple and robust way
        is to join() 'aircraftName' and 'aircraftDir' with the
        character whose ord() value is 0).

        """
        raise NotImplementedError

    @abc.abstractmethod
    def getItem(self, itemId):
        """Return the item (aircraft, airport...) identified by 'itemId'.

        'itemId' should be a Python object that can be conveniently used
        to retrieve high-level data about a chosen item.

        In the case of airports, 'itemId' can be simply the ICAO code
        for a given airport. This method could then return the
        corresponding AirportStub instance.

        In the case of aircraft, one way that would make sense given
        FFGo's architecture would be to use a tuple of the form
        (aircraftName, aircraftDir) for 'itemId'. This method could then
        return the corresponding Aircraft instance.

        Note: unless this docstring somehow became outdated, the
              examples given here are exactly was is implemented in the
              concrete classes AirportStatsManager and
              AircraftStatsManager derived from this abstract class.

        """
        raise NotImplementedError

    @abc.abstractmethod
    def items(self):
        """Iterator returning (JSON-key, High-level-object) pairs.

        For instance, this method can be a generator yielding all pairs
        containing the JSON key used in self.saveFile for a given
        aircraft along with the corresponding Aircraft instance.

        See the concrete classes below for some... concrete examples.

        """
        raise NotImplementedError

    def loadTree(self, topLevel):
        """Load in memory the Python object obtained from self.saveFile.

        'topLevel' should be the Python dictionary representing the full
        contents of self.saveFile after JSON parsing (and of course gzip
        decompression). This method loads it into memory, updating the
        relevant high-level Python objects obtained via getItem() (e.g.,
        AirportStub or Aircraft instances).

        """
        try:
            version = topLevel["format version"]
        except KeyError:
            raise InvalidFormat(self.saveFile, _(
                "no top-level pair with name 'format version'"))

        if version != 1:
            raise InvalidFormat(
                self.saveFile,
                _("unknown format version: {ver}").format(ver=version))

        try:
            tree = topLevel[self.subject]
        except KeyError:
            raise InvalidFormat(self.saveFile, _(
                "no top-level pair with name '{subject}'").format(
                    subject=self.subject))

        for jsonKey, datesOfUse in tree.items():
            itemId = self.jsonKeyToItemId(jsonKey)
            try:
                # Get the Airport or Aircraft instance
                item = self.getItem(itemId)
            except NoSuchItem:
                # Maybe the user is experimenting with smaller or less apt.dat
                # files (e.g., removal of a scenery path that had apt.dat
                # files), or has temporarily removed one of his aircraft paths.
                # Keep his data in 'self.unusedItems' so that it can be saved
                # to 'self.saveFile'.
                self.unusedItems[jsonKey] = datesOfUse
            else:
                item.datesOfUse = datesOfUse
                today = datetime.date.today().toordinal()
                showPeriod = self.showPeriodVar.get()
                # Number of times the item was used in the last 'showPeriod'
                # days
                item.useCountForShow = len(
                    [ date for date in datesOfUse
                      if today - date < showPeriod ])

    def load(self):
        """Load 'self.saveFile' into memory, if it exists.

        If 'self.saveFile' doesn't exist, just log a message stating
        this. Otherwise:
          - update the high-level Python objects obtained via getItem()
            (e.g., AirportStub or Aircraft instances) to contain the
            dates read from 'self.saveFile' [item.datesOfUse];
          - at the same time, compute the “use count for show” of each
            item based on the value of 'self.showPeriodVar'
            [item.useCountForShow].

        """
        if os.path.isfile(self.saveFile):
            logger.info(
                "Opening {subject} stats file for reading: '{file}'".format(
                    subject=self.subject, file=self.saveFile))

            with gzip.open(self.saveFile, mode="rt", encoding="utf-8") as gzfile:
                tree = json.load(gzfile)

            self.loadTree(tree)
        else:
            logger.info("No {subject} stats file found at '{file}', not "
                        "loading anything".format(
                            subject=self.subject, file=self.saveFile))

    def _treeToSaveMaybeAddItem(self, d, jsonKey, datesOfUse, today,
                                expiryDays):
        d[jsonKey] = [ date for date in datesOfUse
                       if today - date < expiryDays ]
        if not d[jsonKey]:
            del d[jsonKey]

    def treeToSave(self):
        """Return a Python dictionary ready to be written to self.saveFile.

        For each item (e.g., aircraft, airport...), discard all entries
        that are older than the number of days stored in
        self.expiryPeriodVar.

        """
        today = datetime.date.today().toordinal()
        expiryDays = self.expiryPeriodVar.get()
        d = {}

        for jsonKey, item in self.items():
            self._treeToSaveMaybeAddItem(d, jsonKey, item.datesOfUse, today,
                                         expiryDays)

        for jsonKey, datesOfUse in self.unusedItems.items():
            if jsonKey not in d:
                self._treeToSaveMaybeAddItem(d, jsonKey, datesOfUse, today,
                                             expiryDays)

        return {"format version": 1, # version number of the file format
                self.subject: d}

    def save(self):
        """Save in-memory statistics to self.saveFile.

        The result is stored in gzip-compressed JSON format (.json.gz).
        By default, the uncompressed text is as compact as possible. If
        self.cmdLineParams.save_stats_in_pretty_form is true, a more
        human-friendly form is used, with spaces and newlines to
        separate the various syntactic elements. Both forms can be
        loaded the same way.

        """
        tree = self.treeToSave()

        logger.info(
            "Opening {subject} stats file for writing: '{file}'".format(
                subject=self.subject, file=self.saveFile))

        kwargs = {}
        if self.cmdLineParams.save_stats_in_pretty_form:
            kwargs["sort_keys"] = True
            # Causes a suitable default for 'separators' to be chosen
            kwargs["indent"] = 4
        else:
            # Select the most compact JSON representation possible
            kwargs["separators"] = (',', ':')

        with gzip.open(self.saveFile, mode="wt", encoding="utf-8") as gzfile:
            json.dump(tree, gzfile, ensure_ascii=False, check_circular=False,
                      **kwargs)

    def recordAsUsedToday(self, itemId):
        """Record that the item identified by 'itemId' has been used today.

        This is only done in memory, in the appropriate high-level
        Python objects (e.g., AirportStub or Aircraft instances). It
        will be eventually lost unless save() or something equivalent is
        called. If this method is called several times for the same
        'itemId' on the same day, only the first call adds the day
        number to the item's 'datesOfUse' attribute.

        Also update the item's 'useCountForShow' attribute (based on the
        number of days given by self.showPeriodVar) in case the current
        day changed since the last time this count was updated.

        """
        today = datetime.date.today().toordinal()
        item = self.getItem(itemId)
        dates = item.datesOfUse

        if not dates or dates[-1] != today:
            # The list of dates naturally remains sorted from oldest to
            # most recent.
            dates.append(today)

        showPeriod = self.showPeriodVar.get()
        item.useCountForShow = len([ date for date in dates
                                     if today - date < showPeriod ])


class AirportStatsManager(StatsManagerBase):
    """Manage airport usage statistics."""

    def __init__(self, config):
        StatsManagerBase.__init__(
            self, config, "airports", config.airportStatsShowPeriod,
            config.airportStatsExpiryPeriod, constants.AIRPORTS_STATS_FILE)

    def jsonKeyToItemId(self, key):
        return key

    def getItem(self, itemId):  # itemId is an ICAO code in this case
        try:
            airport = self.config.airports[itemId]
        except KeyError:
            raise NoSuchAirport(itemId)

        return airport

    def items(self):
        return self.config.airports.items()


class AircraftStatsManager(StatsManagerBase):
    """Manage aircraft usage statistics."""

    def __init__(self, config):
        StatsManagerBase.__init__(
            self, config, "aircrafts", config.aircraftStatsShowPeriod,
            config.aircraftStatsExpiryPeriod, constants.AIRCRAFT_STATS_FILE)

    def jsonKeyToItemId(self, key):
        return key.split('\0')

    def getItem(self, itemId):
        acName, acDir = itemId  # aircraft name and directory
        try:
            candidates = self.config.aircraftDict[acName]
        except KeyError as e:
            raise NoSuchAircraft(acName, acDir) from e

        for aircraft in candidates:
            if aircraft.dir == acDir:
                return aircraft
        else:
            raise NoSuchAircraft(acName, acDir)

    def items(self):
        for aircraft in self.config.aircraftList:
            yield ((aircraft.name + '\0' + aircraft.dir),
                   aircraft)
