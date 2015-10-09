# aircraft.py --- Represent FlightGear aircraft data
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os


class Aircraft:
    """Simple class for holding aircraft metadata.

    Could contain things such as the aircraft “radius”, etc.
    """

    def __init__(self, name, dir_):
        self._attrs = ("name", "dir")
        self.name = name
        # Don't resolve symlinks, so that aircraft paths are effectively shown
        # under the components of Config.FG_aircraft as entered by the user.
        self.dir = os.path.abspath(dir_)

        # Good for displaying to the user
        self.setFile = os.path.join(self.dir, "{}-set.xml".format(self.name))
        # The following should be better to decide whether two -set.xml files
        # refer to the same aircraft or not. We intentionally:
        #   - don't resolve symlinks in the last path component (the basename);
        #   - treat as distinct two set files differing only in the last
        #     component, even if (via symlink) they point to the same file.
        #     This is because this can change the aircraft name, and an
        #     aircraft might behave differently depending on its name...
        self._realSetFile = os.path.join(os.path.realpath(self.dir),
                                         "{}-set.xml".format(self.name))

    def __repr__(self):
        argString = ", ".join([ "{}={!r}".format(attr, getattr(self, attr))
                                for attr in self._attrs ])

        return "{}.{}({})".format(__name__, type(self).__name__, argString)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        # Any instance is different from None, otherwise compare the -set.xml
        # files.
        return other is not None and self._realSetFile == other._realSetFile

    def __hash__(self):
        return hash(self._realSetFile)
