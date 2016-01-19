# common_transl.py --- “Large” translated strings used in several places
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

from .constants import PROGNAME


def geodCalcMethodTooltipText(geodCalc):
    """Return a tooltip text for a choice between geodetic calculation methods.

    'geodCalc' should be a GeodCalc instance. In a tooltip, the returned
    string should be used with 'autowrap=True'.

    """
    if geodCalc.karneyMethodAvailable():
        geographicLibHint = ""
    else:
        geographicLibHint = "\n\n" + _(
            "In order to be able to use it here, you need to have "
            "installed GeographicLib's implementation for the Python "
            "installation you are using to run {prg}.").format(prg=PROGNAME)

    text = _(
        "Method used to compute distance, initial and final bearings "
        "for the shortest path between two airports (“inverse geodetic "
        "problem”). "
        "Vincenty's method is faster than Karney's one, but there are "
        "some particular cases in which Vincenty's algorithm can't do "
        "the computation. Karney's method should handle all possible "
        "cases.{complement}").format(complement=geographicLibHint)

    return text


magneticFieldTooltipText = _(
    "You may want to install GeographicLib's MagneticField program in "
    "order to see magnetic bearings.")
