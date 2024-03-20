# magfield.py --- Access data about the Earth's magnetic field
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import subprocess
import datetime


class error(Exception):
    pass

class MagVarUnavailable(error):
    def __init__(self, message):
        self.message = message


class EarthMagneticField:
    def __init__(self, config):
        self.config = config
        self._checkGeographicLibMagneticField()
        # Just check this works. Other parts of the program will fetch the
        # description just in time in case GeographicLib has been updated while
        # FFGo is running.
        self.getBackendDescription()

    def getBackendDescription(self):
        return self._runMagneticField(justGetVersion=True).strip()

    @classmethod
    def _utcDayString(cls):
        """Return today's UTC date in the form 'YYYY-MM-DD'."""
        # Current date and time expressed in UTC
        now = datetime.datetime.now(datetime.timezone.utc)

        return now.strftime("%Y-%m-%d")

    def _checkGeographicLibMagneticField(self):
        """Check that 'MagneticField' from GeographicLib works fine.

        Raise MagVarUnavailable if not.

        """
        # KSFO at 0 meters above the ellipsoid modelling the Earth
        self._runMagneticField(
            "{} 37.61777 -122.37526 0\n".format(self._utcDayString()))

    def _runMagneticField(self, input_=None, justGetVersion=False):
        executable = self.config.MagneticField_bin.get() or "MagneticField"
        args = [executable]

        if justGetVersion:
            stdin = subprocess.DEVNULL
            args.append("--version")
        else:
            stdin = subprocess.PIPE

        try:
            with subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL,
                                  universal_newlines=True) as proc:
                if justGetVersion:
                    out = proc.stdout.read()
                else:
                    out, err = proc.communicate(input_)
        except OSError as e:
            raise MagVarUnavailable(
                _("unable to find or execute '{exec}' ({errMsg})").format(
                    exec=executable, errMsg=e)) from e

        ok = False
        if proc.returncode or not out:
            if out:
                if proc.returncode > 0:
                    problem = _(
                        "non-zero exit status: {rc}; maybe you need to "
                        "install the magnetic datasets used by GeographicLib. "
                        "On Debian, 'geographiclib-get-magnetic' from the "
                        "geographiclib-tools package may prove convenient for "
                        "this.").format(rc=proc.returncode)
                else:
                    assert proc.returncode < 0, proc.returncode
                    problem = _("killed by signal {}").format(
                        -proc.returncode)
            else:
                problem = _("empty output for the test run")
        else:
            if justGetVersion:
                res = out
                ok = True
            else:
                while out.endswith('\n'):
                    out = out[:-1]
                try:
                    # List comprehensions are fast. This can be useful in case
                    # we process many lines at once.
                    res = [ float(line.split()[0])
                            for line in out.split('\n') ]
                except ValueError as e:
                    try:
                        # Slower version of the same loop, that allows to
                        # access the line that triggered the exception
                        for line in out.split('\n'):
                            decl = line.split()[0]
                            float(decl)
                    except ValueError:
                        problem = _(
                            "returned magnetic declination is not a float: "
                            "{0!r} [complete output: {1!r}]").format(decl,
                                                                     line)
                    else:
                        assert False, \
                            "We should have caught an exception here!"
                else:
                    ok = True

        if ok:
            return res
        else:
            # Don't add "from e" here, as there isn't always an exception...
            raise MagVarUnavailable(
                _("'{exec}' doesn't seem to work properly ({pb})").format(
                    exec=executable, pb=problem))

    def decl(self, lat, lon):
        """Return an estimate of the magnetic variation at the given point.

        The result is the declination (direction of the horizontal
        component of the magnetic field measured clockwise from north)
        in degrees, as a float. It is given for altitude 0 above the
        ellipsoid modelling the Earth, and for now (the result would
        probably be different years earlier or later, as the Earth's
        magnetic field varies over time).

        """
        return self.batchDecl( ((lat, lon),) )[0]

    def batchDecl(self, inputIterable):
        l = []
        # GeographicLib versions 1.39 (released 2014-11-11) and later interpret
        # the string 'now' as the current UTC date. Emulate this for users of
        # older versions.
        today = self._utcDayString()

        for lat, lon in inputIterable:
            try:
                lat = lat.floatRepr()
            except AttributeError:
                lat = str(lat)

            try:
                lon = lon.floatRepr()
            except AttributeError:
                lon = str(lon)

            # date, lat, lon, altitude
            l.append(' '.join((today, lat, lon, "0")))

        if l:
            l.append('')        # to obtain a final newline
            text = '\n'.join(l)
            return self._runMagneticField(input_=text)
        else:
            return []

