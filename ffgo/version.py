# -*- coding: utf-8 -*-

# version.py --- Version information for FFGo
#
# Copyright (c) 2015-2020  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.


import collections

_VersionInfo = collections.namedtuple(
    "VersionInfo", ("major", "minor", "micro", "releasesuffix"))

class VersionInfo(_VersionInfo):
    def __str__(self):
        res = ".".join( ( str(elt) for elt in self[:3] ) )
        if self.releasesuffix:
            res += self.releasesuffix
        return res

    def __repr__(self):
        return "{0}.{1}".format(__name__, _VersionInfo.__repr__(self))

version_info = VersionInfo(1, 12, 7, "")
__version__ = str(version_info)

del collections
