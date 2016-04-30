#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2015, 2016  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

from setuptools import setup, find_packages
import sys
import os
import subprocess
import traceback

setuptools_pkg = "FFGo"
pypkg_name = "ffgo"
here = os.path.abspath(os.path.dirname(__file__))

namespace = {}
version_file = os.path.join(here, pypkg_name, "version.py")
with open(version_file, "r", encoding="utf-8") as f:
    exec(f.read(), namespace)
version = namespace["__version__"]


def do_setup():
    with open("README.rst", "r", encoding="utf-8") as f:
        long_description = f.read()

    setup(
        name=setuptools_pkg,
        version=version,
        description="A powerful graphical launcher for the FlightGear "
                    "flight simulator",
        long_description=long_description,
        url="http://frougon.net/projects/{}/".format(setuptools_pkg),
        license='WTFPLv2',

        author="Robert Leda, Florent Rougon",
        author_email=\
         'https://sites.google.com/site/erobosprojects/flightgear/add-ons/fgo, '
         'f.rougon@free.fr',
        maintainer="Florent Rougon (fork author)",
        maintainer_email='f.rougon@free.fr',

        # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Intended Audience :: End Users/Desktop',
            'License :: DFSG approved',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Topic :: Games/Entertainment :: Simulation',
        ],
        keywords=\
            'FlightGear flightgear flight simulator launcher FFGo FGo!',
        packages=[pypkg_name],
        include_package_data=True,
        # Files to exclude from installation
        exclude_package_data = { '':
                                 ['*/COPYING.txt', '*.po', '*.pot',
                                  '*.xcf', '*/thumbnail-no-Pillow.svg',
                                  '*/Makefile', '*/Makefile.py-functions'] },

        install_requires=['CondConfigParser'],
        extras_require = {'images':  ['Pillow'], 'geo': ['geographiclib']},
        entry_points={'console_scripts': ['ffgo = ffgo.main:main'],
                      'gui_scripts': ['ffgo-noconsole = ffgo.main:main']},
        # We need real files and directories for gettext l10n files, but
        # pkg_resources.resource_filename() doesn't work if the package is
        # imported from a zip file ("resource_filename() only supported for
        # .egg, not .zip"). As a consequence:
        #   - this project can't be "zip safe" without ugly hacks;
        #   - the pkg_resources module doesn't bring any value here; we can
        #     happily use __file__ to find our resources, and avoid depending
        #     on pkg_resources to spare our beloved users the hassle of
        #     installing one more dependency.
        zip_safe=False
)


if __name__ == "__main__": do_setup()
