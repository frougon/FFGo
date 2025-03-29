# -*- coding: utf-8 -*-

# json_report.py --- Read FlightGear's JSON report obtained with --json-report
#
# Copyright (c) 2016-2025, Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <https://www.wtfpl.net/>.

import subprocess
import json

# This import requires the translation system [_() function] to be in
# place.
from ..exceptions import FFGoException
from ..logging import logger


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

class UnableToParseOutputOfFlightGearDashDashJSONReport(
        ErrorProcessingFlightGearDashDashJSONReportOutput):
    """Exception raised when we cannot parse the output 'fgfs --json-report'."""
    ExceptionShortDescription = _(
        "Unable to parse the output of 'fgfs --json-report'")


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

    return normalize(res)


def normalize(report):
    """Handle changes in the output format of 'fgfs --json-report'.

    This handles changes brought by FlightGear commit f282911a0[1].

    [1] https://gitlab.com/flightgear/flightgear/-/commit/f282911a0d29274f3de3182cd70aa994ec78ad9f

    """

    try:
        meta = report["meta"]
    except KeyError:
        raise UnableToParseOutputOfFlightGearDashDashJSONReport(
            "no 'meta' key found")

    try:
        formatMajorVersion = meta["format major version"]
    except KeyError:
        try:
            formatMajorVersion = meta["formatMajorVersion"]
        except KeyError:
            raise UnableToParseOutputOfFlightGearDashDashJSONReport(
                "found neither 'meta/format major version' nor "
                "'meta/formatMajorVersion'")

    if formatMajorVersion == 2:
        return report
    elif formatMajorVersion != 1:
        raise UnableToParseOutputOfFlightGearDashDashJSONReport(
                "unsupported format major version: {}".format(
                    formatMajorVersion))
    else:
        # Convert from format major version 1 to 2
        return convertFromFormatMajorVersion1(report)


# Data for converting from format major version 1 to format major version 2
sectionRenamings = (
    ("meta", "meta"),
    ("general", "general"),
    ("config", "config"),
    ("navigation data", "navData"),
)

subsectionRenamings = {
    "meta": (("type", "type"),
             ("format major version", "formatMajorVersion"),
             ("format minor version", "formatMinorVersion")),
    "general": (("name", "name"),
                ("version", "version"),
                ("build date", "buildDate"),
                ("build type", "buildType")),
    "config": (("FG_ROOT", "fgRoot"),
               ("FG_HOME", "fgHome"),
               ("scenery paths", "sceneryPaths"),
               ("aircraft paths", "aircraftPaths"),
               ("TerraSync directory", "terrasyncPath"),
               ("download directory", "downloadPath"),
               ("autosave file", "autosavePath")),
    "navigation data": (("apt.dat files", "aptDatPaths"),
                        ("fix.dat files", "fixDatPaths"),
                        ("nav.dat files", "navDatPaths")),
}

def convertFromFormatMajorVersion1(oldReport):
    """Convert a FlightGear JSON report from format major version 1 to 2.

    The subsections introduced in version 2 will be absent; everything
    else should be accessible as in a genuine “version 2 report”.

    Return the report in version 2 format (a dict).

    Note: mutable types from 'oldReport' are reused directly (not
          copied).

    """
    res = {}

    for oldSectionName, newSectionName in sectionRenamings:
        oldSection = oldReport[oldSectionName]
        newSection = {}

        for oldSubName, newSubName in subsectionRenamings[oldSectionName]:
            try:
                newSection[newSubName] = oldSection[oldSubName]
            except KeyError:
                logger.notice("This FlightGear version doesn't have "
                              "'{sec}/{subsec}' in its --json-report output."
                              .format(sec=oldSectionName, subsec=oldSubName))

        res[newSectionName] = newSection

    return res
