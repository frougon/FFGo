# fgcmdbuilder.py --- Prepare the fgfs argument list (“FlightGear command line”)
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import re
import functools
import operator
import condconfigparser

from .fgdata.fgversion import FlightGearVersion


class InvalidEscapeSequenceInOptionLine(Exception):
    """Exception raised when an option line contains an invalid escape sequence.

    This happens when the escape sequence is not recognized by FFGo.

    """
    def __init__(self, char):
        self.char = char

    def __str__(self):
        return _("invalid escape sequence in option line: \\{0}").format(
            self.char)

    def __repr__(self):
        return "{0}.{1}({2!r})".format(__name__, type(self).__name__,
                                       self.char)


class FGCommandBuilder:
    """Assemble fgfs arguments from the configuration and GUI settings.

    This class is used to build the list of arguments to pass to fgfs
    from the CondConfigParser-parsed configuration and the various
    settings offered by the GUI (selected aircraft, airport,
    scenarios...).

    """
    def __init__(self, app):
        self.app = app
        self.argList = None
        self.lastConfigParsingExc = None

    _rawCfgLineComment_cre = re.compile(r"[ \t]*#")

    def processRawConfigLines(self, rawConfigLines):
        r"""Handle backslash escape sequences and remove comments in fgfs opts.

        Comments start with '#' and end at the end of the line. Spaces
        and tabs right before a comment are ignored (except if a space
        is part of a \<space> escape sequence).

        Outside comments, the following escape sequences are recognized
        (the expansion of each escape sequence is given in the second
        column):

          \\          \ (produces a single backslash)
          \[          [ (useful at the beginning of a line to avoid
                         confusion with the start of a predicate)
          \]          ] (for symmetry with '\[')
          \#          # (literal '#' character, doesn't start a comment)
          \t          tab character
          \n          newline character (doesn't start a new option)
          \<space>    space character (useful to include a space at the
                      end of an option, which would be ignored without
                      the backslash)
          \<newline>  continuation line (i.e., make as if the next line
                      were really the continuation of the current line,
                      with the \<newline> escape sequence removed)

        """
        res = []                # list of strings: the output lines
        # After escape sequences processing: stores the characters forming each
        # output line as it is being constructed from one or more input lines
        # (continuation lines are started with a backslash at the end of the
        # previous input line)
        chars = []
        # i: input line number; j: column number in this line
        i = j = 0

        while i < len(rawConfigLines):
            if j >= len(rawConfigLines[i]):
                res.append(''.join(chars)) # finish the output line
                del chars[:]
                i += 1          # next input line
                j = 0
                continue

            mo = self._rawCfgLineComment_cre.match(
                rawConfigLines[i][j:])
            if mo:
                res.append(''.join(chars)) # finish the output line
                del chars[:]
                i += 1          # next input line
                j = 0
                continue

            c = rawConfigLines[i][j]

            if c == "\\":
                if j + 1 == len(rawConfigLines[i]): # end of input line
                    if i + 1 == len(rawConfigLines):
                        res.append(''.join(chars)) # finish the output line
                    else:
                        j = -1  # continuation line

                    i += 1      # next input line
                else:
                    j += 1      # next char of input line
                    c = rawConfigLines[i][j]

                    if c == "\\":
                        chars.append("\\")
                    elif c == "n":
                        chars.append("\n")
                    elif c == "t":
                        chars.append("\t")
                    elif c == '#':
                        chars.append('#')
                    elif c == ' ':
                        chars.append(' ')
                    elif c == '[':
                        chars.append('[')
                    elif c == ']':
                        chars.append(']')
                    else:
                        raise InvalidEscapeSequenceInOptionLine(c)
            elif c == '#':
                assert False, "Comment char # should have been handled " \
                    "earlier (by regexp)"
            else:
                chars.append(c)

            j += 1              # next input char

        return res

    def mergeFGOptions(self, mergedOptions, optionList):
        """Merge identical options in 'optionList'.

        Return a new list containing all options from 'optionList',
        except that the elements of 'optionList' that start with an
        element of 'mergedOptions' are merged together.

        More precisely, for a given element e (a string) of
        'mergedOptions', the first element of 'optionList' that starts
        with e is replaced by the last element of 'optionList' that
        starts with e and all other such elements of 'optionList' are
        omitted from the result. In other words, the last element of
        'optionList' that starts with e "wins", replaces the first one,
        and other occurrences are ignored.

        """
        d = {}
        l = []

        for opt in optionList:
            for prefix in mergedOptions:
                if opt.startswith(prefix):
                    if prefix not in d: # first time we encounter this prefix?
                        l.append( (False, prefix) )
                    d[prefix] = opt # overwrites previous ones
                    break
            else:
                l.append( (True, opt) )  # non-merged option

        # If isOpt is False, s is a prefix and d[s] the last element of
        # optionList starting with that prefix.
        return [ s if isOpt else d[s] for isOpt, s in l ]

    def getUIExposedOptions(self):
        options = []
        # --fg-aircraft may be split into several options, as for
        # --ai-scenario, but that doesn't seem to be necessary (tested with FG
        # 3.5, commit 2496bdecfad733bf69c58474939d4a831cc16d46).
        for opt, cfg in (('--fg-root=', self.app.config.FG_root.get()),
                         ('--fg-aircraft=',
                          self.app.config.FG_aircraft.get())):
            if cfg:
                options.append(opt + cfg)

        scenery_dirs = self.app.config.FG_scenery.get()
        if scenery_dirs and scenery_dirs != 'None':
            options.append('--fg-scenery=' + scenery_dirs)

        aircraftOpts = [('--aircraft=', self.app.config.aircraft.get())]

        aircraftDir = self.app.config.aircraftDir.get()
        if aircraftDir:
            # Not refreshing the version now: this method must be very fast, as
            # it is basically called after every change to the Options Window.
            FG_version = self.app.config.FG_version
            # The fgfs --aircraft-dir option has been fixed in FlightGear's
            # commit 7198dec355144fbb0eaccb39f0c241dd07ebaee0, between versions
            # 3.6 and 3.8.
            if FG_version is None or FG_version < FlightGearVersion([3, 8]):
                aircraftDir = os.path.realpath(aircraftDir)

            aircraftOpts.append(('--aircraft-dir=', aircraftDir))

        parkStatus, parkName, parkOpts = self.app.config.decodeParkingSetting(
            self.app.config.park.get())

        # Parking positions from apt.dat use --lat and --lon, so don't pass
        # --airport/--runway/--carrier in such a case.
        if parkStatus == "apt.dat":
            locationOpts = []
        elif self.app.config.carrier.get(): # carrier mode
            locationOpts = [('--carrier=', self.app.config.carrier.get())]
        else:
            locationOpts = [('--airport=', self.app.config.airport.get()),
                            ('--runway=', self.app.config.rwy.get())]

        for opt, cfg in aircraftOpts + locationOpts:
            if cfg:
                options.append(opt + cfg)

        if parkStatus != "invalid":
            # Add either --parkpos, or --lat/--lon/--heading or nothing.
            options.extend(parkOpts)

        if self.app.config.scenario.get() != '':
            for scenario in self.app.config.scenario.get().split():
                options.append('--ai-scenario=' + scenario)

        return options

    def update(self):
        """Update self.argList and self.lastConfigParsingExc."""
        t = self.app.options.get()
        options = self.getUIExposedOptions()

        try:
            condConfig = condconfigparser.RawConditionalConfig(
                t, extvars=("aircraft", "aircraftDir", "airport", "parking",
                            "runway", "carrier", "scenarios"))
            context = {"aircraft": self.app.config.aircraft.get(),
                       "aircraftDir": self.app.config.aircraftDir.get(),
                       "airport": self.app.config.airport.get(),
                       "parking": self.app.config.park.get(),
                       "runway": self.app.config.rwy.get(),
                       "carrier": self.app.config.carrier.get(),
                       "scenarios": self.app.config.scenario.get().split()}

            # configVars:
            #   external and non-external (assigned in the cfg file) variables
            #
            # rawConfigSections:
            #   list of lists of strings which are fgfs options. The first list
            #   corresponds to the "default", unconditional section of the
            #   config file; the other lists come from the conditional sections
            #   whose predicate is true according to 'context'.
            configVars, rawConfigSections = condConfig.eval(context)
            optionLineGroups = [ self.processRawConfigLines(lines) for lines in
                                 rawConfigSections ]
            # Concatenate all lists together
            additionalLines = functools.reduce(operator.add, optionLineGroups,
                                               [])
            options.extend(additionalLines)

            # Merge options starting with an element of MERGED_OPTIONS
            # The default for MERGED_OPTIONS is the empty list.
            mergedOptions = configVars.get("MERGED_OPTIONS", [])
            # Will be available for App._runFG()
            self.argList = self.mergeFGOptions(mergedOptions, options)
        except (condconfigparser.error, InvalidEscapeSequenceInOptionLine) as e:
            self.argList = None
            self.lastConfigParsingExc = e
        else:
            self.lastConfigParsingExc = None
