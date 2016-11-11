# -*- coding: utf-8 -*-

# json_report.py --- Read FlightGear's JSON report obtained with --json-report
#
# Copyright (c) 2016, Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import subprocess
import json

# This import requires the translation system [_() function] to be in
# place.
from ..exceptions import FFGoException


class error(FFGoException):
    """Base class for exceptions in the json_report module."""
    ExceptionShortDescription = _("Error caught in the json_report module")

class UnableToRunFlightGearDashDashJSONReport(error):
    """Exception raised when we cannot run 'fgfs --json-report'."""
    ExceptionShortDescription = _("Unable to run 'fgfs --json-report'")

class ErrorRunningFlightGearDashDashJSONReport(error):
    """Exception raised when running 'fgfs --json-report' returns an error."""
    ExceptionShortDescription = _("Error when running 'fgfs --json-report'")

class ErrorProcessingFlightGearDashDashJSONReportOutput(error):
    """
    Exception raised when the output of 'fgfs --json-report' can't be processed."""
    ExceptionShortDescription = _(
        "Error trying to process the output of 'fgfs --json-report'")


def getFlightGearJSONReport(FG_bin, FG_working_dir, args):
    """
    Return a dictionary corresponding to the output of 'fgfs ... --json-report'"""
    kwargs = {}
    if FG_working_dir:
        kwargs["cwd"] = FG_working_dir

    try:
        output = subprocess.check_output(
            [FG_bin] + list(args) + ["--json-report"],
            stderr=subprocess.DEVNULL,
            universal_newlines=False, # only way to control the encoding
            **kwargs)
    except OSError as e:
        raise UnableToRunFlightGearDashDashJSONReport(str(e)) from e
    except subprocess.CalledProcessError as e:
        raise ErrorRunningFlightGearDashDashJSONReport(str(e)) from e

    try:
        # The report is always encoded in UTF-8 (intentionally).
        res = json.loads(output.decode("utf-8"))
    # json.JSONDecodeError was only added in Python 3.5.
    except Exception as e:
        raise ErrorProcessingFlightGearDashDashJSONReportOutput(str(e))

    return res
