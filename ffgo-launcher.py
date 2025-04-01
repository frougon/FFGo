#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# ffgo-launcher.py --- Script to launch FFGo from its unpacked source
# Copyright (c) 2015-2025, Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import os
import sys

srcPath = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, srcPath)

import ffgo.main
ffgo.main.main()
