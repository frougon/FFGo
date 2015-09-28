# -*- coding: utf-8 -*-

# exceptions.py --- Exception support for FFGo
#
# Copyright (c) 2015, Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

"""Exception support for FFGo.

Note: importing this module requires the translation system
      [_() function] to be in place.

"""

from .constants import PROGNAME


class FFGoException(Exception):
    """Base class for exceptions in FFGo."""
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        return self.completeMessage()

    def __repr__(self):
        return "{0}.{1}({2!r})".format(__name__, type(self).__name__,
                                       self.message)

    def completeMessage(self):
        if self.message:
            return "{0}: {1}".format(self.ExceptionShortDescription,
                                     self.message)
        else:
            return self.ExceptionShortDescription

    ExceptionShortDescription = _("{prg} generic exception").format(
        prg=PROGNAME)
