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
