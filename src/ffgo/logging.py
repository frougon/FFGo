# logging.py --- Logging infrastructure for FFGo
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

from . import misc


class LogLevel(misc.OrderedEnum):
    debug, info, notice, warning, error, critical = range(6)

# List containing the above log levels as strings in increasing priority order
allLogLevels = [member.name for member in LogLevel]
allLogLevels.sort(key=lambda n: LogLevel[n].value)


def _logFuncFactory(level):
    def logFunc(self, *args, **kwargs):
        self.log(LogLevel[level], True, *args, **kwargs)

    def logFunc_noPrefix(self, *args, **kwargs):
        self.log(LogLevel[level], False, *args, **kwargs)

    return (logFunc, logFunc_noPrefix)


class Logger:
    def __init__(self, logLevel=LogLevel.notice, logFile=None):
        self.logLevel = logLevel
        self.logFile = logFile

    def open(self, *args, **kwargs):
        self.logFile = open(*args, **kwargs)
        return self.logFile

    def log(self, level, prefix, *args, **kwargs):
        if prefix and level >= LogLevel.warning and args:
            args = [level.name.upper() + ": " + args[0]] + list(args[1:])

        if level >= self.logLevel:
            print(*args, **kwargs)

        if self.logFile is not None:
            kwargs["file"] = self.logFile
            print(*args, **kwargs)

    # Don't overload log() with too many tests or too much indirection for
    # little use
    def logToFile(self, *args, **kwargs):
        kwargs["file"] = self.logFile
        print(*args, **kwargs)

    debug, debugNP = _logFuncFactory("debug")
    info, infoNP = _logFuncFactory("info")
    notice, noticeNP = _logFuncFactory("notice")
    warning, warningNP = _logFuncFactory("warning")
    error, errorNP = _logFuncFactory("error")
    critical, criticalNP = _logFuncFactory("critical")


# One instance used throughout the application
logger = Logger()
