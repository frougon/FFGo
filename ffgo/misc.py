# misc.py --- Miscellaneous utility functions
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import sys
import platform
import enum
import gettext
import locale
import textwrap
import traceback

from .constants import PROGNAME


def pythonVersionString():
    if sys.version_info[3] == "final":
        compl = ""
    else:
        compl = " " + sys.version_info[3]

    return "{major}.{minor}.{micro}{compl}".format(
        major=sys.version_info[0],
        minor=sys.version_info[1],
        micro=sys.version_info[2],
        compl=compl)


def executableFileName(base):
    """Return the platform-dependent name of an executable."""
    if platform.system() == "Windows":
        return base + ".exe"
    else:
        return base


def isDescendantWidget(maybeParent, widget):
    """Return True if 'widget' is 'maybeParent' or a descendant of it.

    Widget parenthood is tested for Tk in this function.

    """
    if widget is maybeParent:
        return True
    else:
        return any(( isDescendantWidget(w, widget)
                     for w in maybeParent.winfo_children() ))


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


def normalizeHeading(azimuth):
    # x % y always has the sign of y
    a = round(azimuth % 360.0)

    return a if a else 360


class DecimalCoord(float):
    def __str__(self):
        # 8 decimal places, as recommended for latitudes and longitudes in
        # the apt.dat v1000 spec
        return locale.format("%.08f", self)

    def __repr__(self):
        return "{}.{}({!r})".format(__name__, type(self).__name__, float(self))

    def floatRepr(self):
        return repr(float(self))

    def precisionRepr(self):
        # Used when passing --lat or --lon options to make sure we don't
        # lose any precision because of the __str__() above. 10 should
        # be largely enough, otherwise there is nothing magical about
        # this value.
        return "{:.010f}".format(self)

    def __add__(self, other):
        if self.__class__ is other.__class__:
            return DecimalCoord(float(self) + float(other))
        else:
            return NotImplemented

    def __sub__(self, other):
        if self.__class__ is other.__class__:
            return DecimalCoord(float(self) - float(other))
        else:
            return NotImplemented

    def __mul__(self, other):
        for klass in (int, float):
            if isinstance(other, klass):
                return DecimalCoord(float(self) * float(other))
        else:
            return NotImplemented

    def __truediv__(self, other):
        for klass in (int, float):
            if isinstance(other, klass):
                return DecimalCoord(float(self) / float(other))
        else:
            return NotImplemented


# Similar to processPosition() in src/Airports/dynamicloader.cxx of the
# FlightGear source code (version 3.7)
def mixedToDecimalCoords(s):
    """Convert from e.g., 'W122 22.994' to -122.38323333333334 (float).

    The source format is used in FlightGear groundnet files. The first
    number represents degrees and must be an integer. The second number
    is written as a decimal number and represents minutes of angle.

    """
    if not s:
        raise ValueError(_("empty coordinate string"))

    if s[0] in "NE":
        sign = 1
    elif s[0] in "SW":
        sign = -1
    else:
        raise ValueError(_("unexpected first character in mixed-style "
                           "coordinate string: {char!r}").format(char=s[0]))

    degree = int(s[1:s.index(' ', 1)])
    minutes = float(s[s.index(' ', 1) + 1:])

    return DecimalCoord(sign * (degree + minutes/60.0))


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


# **********************************************************************
# *               Context-sensitive translation support                *
# **********************************************************************

class TranslationHelper:
    """Class providing context-sensitive translations.

    At the time of this writing, GNU gettext supports this, but not the
    gettext module of the Python standard library.

    """
    def __init__(self, config):
        """Constructor for TranslationHelper instances.

        config -- a Config instance

        """
        from .constants import MESSAGES, LOCALE_DIR

        langCode = config.language.get()
        if not langCode:
            try:
                langCode = gettext.translation(
                    MESSAGES, LOCALE_DIR).info()['language']
            except OSError:
                # There is no translation for the current locale, use English
                langCode = "en"

        try:
            self.translator = gettext.translation(
                MESSAGES, LOCALE_DIR, languages=[langCode])
        except FileNotFoundError as e:
            moResource = "data/locale/{}/LC_MESSAGES/{}.mo".format(langCode,
                                                                   MESSAGES)
            if not resourceExists(moResource):
                msg = textwrap.dedent("""\
                Error: unable to initialize the translation system. Your
                installation is missing the file '{moFile}'. If you simply
                cloned or downloaded {prg}'s Git repository, it is quite normal
                that .mo files are missing (they must be generated from their
                .po sources). Please refer to {prg}'s installation guide:
                docs/INSTALL/INSTALL_en. It has specific instructions that
                must be followed for a successful installation from the Git
                repository.""").format(
                    moFile=resourceFilename(moResource), prg=PROGNAME)
                l = [traceback.format_exc(), textwrap.fill(msg, width=78)]
                print(*l, sep='\n', file=sys.stderr)
                sys.exit(1)
            else:
                raise

    def pgettext(self, context, msgid):
        s = "{}\x04{}".format(context, msgid)

        try:
            transl = self.translator._catalog[s]
        except KeyError:
            if self.translator._fallback:
                return self.translator._fallback.pgettext(context, msgid)
            else:
                return msgid

        return transl

    def ngettext(self, singular, plural, n):
        return self.translator.ngettext(singular, plural, n)

    def npgettext(self, context, singular, plural, n):
        s = "{}\x04{}".format(context, singular)
        pluralForm = self.translator.plural(n)

        try:
            transl = self.translator._catalog[(s, pluralForm)]
        except KeyError:
            if self._fallback:
                return self.translator._fallback.npgettext(
                    context, singular, plural, n)
            else:
                return (singular if n == 1 else plural)

        return transl

    def gettext_noop(self, msgid):
        return msgid

    def N_(self, msgid):        # short synonym of gettext_noop()
        return msgid

    def pgettext_noop(self, context, msgid):
        return msgid

    def npgettext_noop(self, context, singular, plural, n):
        return singular


class Observable:
    """Class to which observers can be attached.

    This class is similar to Tkinter variable classes such as StringVar
    and IntVar, but accepts arbitrary Python types and is easier to
    debug (exceptions raised in Tkinter variable observers are a pain to
    debug because the tracebacks don't go beyond the <variable>.set()
    calls---in other words, they don't cross the Tk barrier).
    Performance should also be better with this class, since it doesn't
    have to go through Python → Tk → Python layers. Of course, instances
    of this class can't be used directly with Tkinter widgets as Tkinter
    variables.

    Except for implicit type conversions done by Tkinter, the syntax
    used to manipulate a Tkinter StringVar or IntVar, and attach
    observers to it, can be used unchanged here. The biggest difference
    is that this class uses the values passed to set() as is instead of
    automatically converting them as done with Tkinter methods. The
    other difference is that callbacks written for this class can rely
    on particular arguments being passed, which are not necessarily the
    same for a Tkinter variable observer.

    Apart from these differences, the semantics should be very close to
    those provided by Tkinter variables. Most notably, a 'read' (resp.
    'write') observer is called whenever the observable's get() (resp.
    set()) method is called---whether the value is actually modified by
    set() calls is irrelevant.

    """

    def __init__(self, initValue=None):
        self.value = initValue
        self.readCallbacks = []
        self.writeCallbacks = []

    def get(self, runCallbacks=True):
        value = self.value

        if runCallbacks:
            for cb in self.readCallbacks:
                cb(value)

        return value

    def set(self, value, runCallbacks=True):
        self.value = value

        if runCallbacks:
            for cb in self.writeCallbacks:
                cb(value)

    def trace(self, accessType, callback):
        if accessType == "w":
            self.writeCallbacks.append(callback)
        elif accessType == "r":
            self.readCallbacks.append(callback)
        else:
            raise ValueError("invalid access type for trace(): {accessType}"
                             .format(accessType=accessType))


class ProgressFeedbackHandler:
    """Simple class to interface with widgets indicating progress of a task."""
    def __init__(self, text="", min=0.0, max=100.0, value=0.0):
        self.setMinMax(min, max)
        self.setTextAndValue(text, value)

    def setMin(self, value):
        self.min = float(value)
        self.amplitude = self.max - self.min

    def setMax(self, value):
        self.max = float(value)
        self.amplitude = self.max - self.min

    def setMinMax(self, min, max):
        self.min, self.max = float(min), float(max)
        self.amplitude = self.max - self.min

    def setText(self, text):
        self.text = text
        self.onUpdated()

    def setValue(self, value):
        self.value = float(value)
        self.onUpdated()

    def setTextAndValue(self, text, value):
        self.text = text
        self.value = float(value)
        self.onUpdated()

    def startPhase(self, text, min, max):
        self.text = text
        self.setMinMax(min, max)
        self.setValue(min)
        self.onUpdated()

    def forceUpdate(self):
        self.onUpdated()

    def onUpdated(self):
        """No-op. To be overridden by subclasses."""
        pass
