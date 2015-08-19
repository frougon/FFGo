# misc.py --- Miscellaneous utility functions
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import io
import pkg_resources
from .constants import PYPKG_NAME


# ****************************************************************************
# Thin abstraction layer on top of pkg_resources in case one needs to use a
# different API (pkgutil...) one day. It also makes the resulting code easier
# to read by automatically passing the PYPKG_NAME argument.
# ****************************************************************************

def resourceExists(path):
    return pkg_resources.resource_exists(PYPKG_NAME, path)

def resourcelistDir(path):
    return pkg_resources.resource_listdir(PYPKG_NAME, path)

def resourceIsDir(path):
    return pkg_resources.resource_isdir(PYPKG_NAME, path)

def binaryResourceStream(path):
    # The returned stream is always in binary mode (yields bytes, not
    # strings). It is a context manager (supports the 'with' statement).
    return pkg_resources.resource_stream(PYPKG_NAME, path)

def textResourceStream(path, encoding='utf-8'):
    # The return value is a context manager (supports the 'with' statement)
    return io.TextIOWrapper(pkg_resources.resource_stream(PYPKG_NAME, path),
                            encoding=encoding)

def textResourceString(path, encoding='utf-8'):
    with textResourceStream(path, encoding=encoding) as f:
        s = f.read()

    return s

def resourceFilename(path):
    return pkg_resources.resource_filename(PYPKG_NAME, path)
