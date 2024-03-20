# -*- coding: utf-8 -*-

# fgversion.py --- Represent FlightGear version information
#
# Copyright (c) 2015, 2016, Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import re
import subprocess

# This import requires the translation system [_() function] to be in
# place.
from ..exceptions import FFGoException


class error(FFGoException):
    """Base class for exceptions in the fgversion module."""
    ExceptionShortDescription = _("Error caught in the fgversion module")

class BadFGVersionUsage(error):
    """
    Exception raised when the fgversion module is used in an incorrect way."""
    ExceptionShortDescription = _("Invalid use of the fgversion module")

class UnableToParseFlightGearVersion(error):
    """Exception raised when we cannot parse the :program:`FlightGear` \
version string."""
    ExceptionShortDescription = _(
        "Unable to parse as a FlightGear version string")

class UnableToParseFlightGearVersionOutput(error):
    """Exception raised when we cannot parse the :program:`FlightGear` \
--version output."""
    ExceptionShortDescription = _(
        "Unable to parse the output of 'fgfs --version'")

class UnableToRunFlightGearDashDashVersion(error):
    """Exception raised when we cannot run 'fgfs --version'."""
    ExceptionShortDescription = _("Unable to run 'fgfs --version'")

class ErrorRunningFlightGearDashDashVersion(error):
    """Exception raised when running 'fgfs --version' returns an error."""
    ExceptionShortDescription = _("Error when running 'fgfs --version'")


# Adapted from pythondialog's DialogBackendVersion class, hence the
# Sphinx markup in docstrings.
class FlightGearVersion:
    """Class representing possible versions of :program:`FlightGear`.

    The purpose of this class is to make it easy to reliably compare
    between versions of :program:`FlightGear`. It encapsulates the
    specific details of the :program:`FlightGear` versioning scheme to
    allow eventual adaptations to changes in this scheme without
    affecting external code.

    The version is represented by two components in this class: the
    :dfn:`dotted part` and the :dfn:`rest`. For instance, in the
    ``'1.2'`` version string, the dotted part is ``[1, 2]`` and the rest
    is the empty string. However, in version ``'1.2-20130902'``, the
    dotted part is still ``[1, 2]``, but the rest is the string
    ``'-20130902'``.

    At the time of this writing, I haven't seen a :program:`FlightGear`
    version using a non-empty “rest” part, however leaving this support
    in place may prove handy the day the :program:`FlightGear`
    developers decide to add some suffix to the :program:`FlightGear`
    version. Of course, the version comparing methods may need some
    slight adaptation if this ever happens.

    Instances of this class can be created with the constructor by
    specifying the dotted part and the rest. Alternatively, an instance
    can be created from the corresponding version string (e.g.,
    ``'1.2-20130902'``) using the :meth:`fromstring` class method.
    Therefore, all of the following expressions are valid to create a
    FlightGearVersion instance::

      FlightGearVersion([1, 2])
      FlightGearVersion([1, 2], "-20130902")
      FlightGearVersion("1.2-20130902")
      FlightGearVersion.fromstring("1.2-20130902")

    If *v* is a :class:`FlightGearVersion` instance, then
    :samp:`str({v})` is a string representing the same version (for
    instance, ``"1.2-20130902"``).

    Two :class:`FlightGearVersion` instances can be compared with the
    usual comparison operators (``<``, ``<=``, ``==``, ``!=``, ``>=``,
    ``>``). The algorithm is designed so that the following order is
    respected (after instanciation with :meth:`fromstring`)::

      1.2 < 1.2-20130902 < 1.2-20130903 < 1.2.0 < 1.2.0-20130902

    among other cases. Actually, the *dotted parts* are the primary keys
    when comparing and *rest* strings act as secondary keys. *Dotted
    parts* are compared with the standard Python list comparison and
    *rest* strings using the standard Python string comparison.

    """
    _FlightGearVersion_cre = re.compile(r"""(?P<dotted> (\d+) (\.\d+)* )
                                            (?P<rest>.*)$""", re.VERBOSE)

    def __init__(self, dottedPartOrStr, rest=""):
        """Create a :class:`FlightGearVersion` instance.

        Please see the class docstring for details.

        """
        if isinstance(dottedPartOrStr, str):
            if rest:
                raise BadFGVersionUsage(
                    "non-empty 'rest' with 'dottedPartOrStr' as string: "
                    "{0!r}".format(rest))
            else:
                tmp = self.__class__.fromstring(dottedPartOrStr)
                dottedPartOrStr, rest = tmp.dottedPart, tmp.rest

        for elt in dottedPartOrStr:
            if not isinstance(elt, int):
                raise BadFGVersionUsage(
                    "when 'dottedPartOrStr' is not a string, it must "
                    "be a sequence (or iterable) of integers; however, "
                    "{0!r} is not an integer.".format(elt))

        self.dottedPart = list(dottedPartOrStr)
        self.rest = rest

    def __repr__(self):
        return "{0}.{1}({2!r}, rest={3!r})".format(
            __name__, self.__class__.__name__, self.dottedPart, self.rest)

    def __str__(self):
        return '.'.join(map(str, self.dottedPart)) + self.rest

    @classmethod
    def fromstring(cls, s):
        """Create a :class:`FlightGearVersion` instance from a \
:program:`FlightGear` version string.

        :param str s: a :program:`FlightGear` version string
        :return:
          a :class:`FlightGearVersion` instance representing the same
          string

        Notable exception:

          :exc:`UnableToParseFlightGearVersion`

          """
        mo = cls._FlightGearVersion_cre.match(s)
        if not mo:
            raise UnableToParseFlightGearVersion(s)
        dottedPart = [ int(x) for x in mo.group("dotted").split(".") ]
        rest = mo.group("rest")

        return cls(dottedPart, rest)

    def __lt__(self, other):
        return (self.dottedPart, self.rest) < (other.dottedPart, other.rest)

    def __le__(self, other):
        return (self.dottedPart, self.rest) <= (other.dottedPart, other.rest)

    def __eq__(self, other):
        return (self.dottedPart, self.rest) == (other.dottedPart, other.rest)

    # Python 3.2 has a decorator (functools.total_ordering) to automate this...
    def __ne__(self, other):
        return not (self == other)

    def __gt__(self, other):
        return not (self <= other)

    def __ge__(self, other):
        return not (self < other)

    def major(self):
        return self.dottedPart[0]

    def minor(self):
        return self.dottedPart[1]

    def micro(self):
        return self.dottedPart[2]


_FGVersionOutput_cre = re.compile(r"^FlightGear version: +(?P<version>.*)$",
                                  re.IGNORECASE | re.MULTILINE)

def getFlightGearVersion(FG_bin, FG_root, FG_working_dir):
    # FlightGear 2016.1.0 (from February 2016) can spawn an annoying popup
    # dialog when 'fgfs --version' is run, apparently meant to let the user
    # graphically choose the FG_ROOT path to use in the built-in Qt lancher.
    # Passing the --fg-root option seems to be enough to get --version to work
    # properly.
    FG_root_arg = "--fg-root=" + FG_root

    kwargs = {}
    if FG_working_dir:
        kwargs["cwd"] = FG_working_dir

    try:
        output = subprocess.check_output([FG_bin, FG_root_arg, "--version"],
                                         stderr=subprocess.STDOUT,
                                         universal_newlines=True,
                                         **kwargs)
    except OSError as e:
        raise UnableToRunFlightGearDashDashVersion(str(e)) from e
    except subprocess.CalledProcessError as e:
        raise ErrorRunningFlightGearDashDashVersion(str(e)) from e

    mo = _FGVersionOutput_cre.search(output)
    if not mo:
        raise UnableToParseFlightGearVersionOutput()

    return FlightGearVersion(mo.group("version"))
