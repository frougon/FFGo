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

    def _checkGeographicLibMagneticField(self):
        """Check that 'MagneticField' from GeographicLib works fine.

        Raise MagVarUnavailable if not.

        """
        # KSFO at 0 meters above the ellipsoid modelling the Earth
        self._runMagneticField("now", "37.61777", "-122.37526", "0")

    def _runMagneticField(self, date=None, lat=None, lon=None, altitude=None,
                          justGetVersion=False):
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
                    out, err = proc.communicate(
                        ' '.join((date, lat, lon, altitude)))
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
                decl = out.split()[0]
                try:
                    res = float(decl)
                except ValueError as e:
                    problem = _(
                        "first return value is not a float: {0!r} "
                        "[complete output: {1!r}]").format(decl, out)
                else:
                    ok = True

        if ok:
            return res
        else:
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
        try:
            lat = lat.floatRepr()
        except AttributeError:
            lat = str(lat)

        try:
            lon = lon.floatRepr()
        except AttributeError:
            lon = str(lon)

        return self._runMagneticField("now", lat, lon, "0")
