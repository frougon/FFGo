# misc.py --- Miscellaneous utility functions
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import sys
import enum


def pythonVersionString():
    return "{major}.{minor}.{micro} {releaseLevel}".format(
        major=sys.version_info[0],
        minor=sys.version_info[1],
        micro=sys.version_info[2],
        releaseLevel=sys.version_info[3])


# Based on an example from the 'enum' documentation
class OrderedEnum(enum.Enum):
    """Base class for enumerations whose members can be ordered.

    Contrary to enum.IntEnum, this class maintains normal enum.Enum
    invariants, such as members not being comparable to members of other
    enumerations (nor of any other class, actually).

    """
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.value == other.value
        return NotImplemented

    def __ne__(self, other):
        if self.__class__ is other.__class__:
            return self.value != other.value
        return NotImplemented


# ****************************************************************************
# Thin abstraction layer offering an API similar to that of pkg_resources. By
# changing the functions below, it would be trivial to switch to pkg_resources
# should the need arise (remove _localPath() and use the pkg_resources
# functions in the most straightforward way).
# ****************************************************************************

def _localPath(path):
    return os.path.join(*([os.path.dirname(__file__)] + path.split('/')))

def resourceExists(path):
    return os.path.exists(_localPath(path))

def resourcelistDir(path):
    return os.listdir(_localPath(path))

def resourceIsDir(path):
    return os.path.isdir(_localPath(path))

def binaryResourceStream(path):
    # The returned stream is always in binary mode (yields bytes, not
    # strings). It is a context manager (supports the 'with' statement).
    return open(_localPath(path), mode="rb")

def textResourceStream(path, encoding='utf-8'):
    # The return value is a context manager (supports the 'with' statement).
    return open(_localPath(path), mode="r", encoding=encoding)

def textResourceString(path, encoding='utf-8'):
    with textResourceStream(path, encoding=encoding) as f:
        s = f.read()

    return s

def resourceFilename(path):
    return _localPath(path)
