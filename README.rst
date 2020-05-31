===============================================================================
FFGo
===============================================================================
A powerful graphical launcher for FlightGear
-------------------------------------------------------------------------------

This software is a fork of the excellent `FGo!`_ program written by
Robert “erobo” Leda, see HISTORY in the ``docs/README/README_en`` file
for details. It is a graphical launcher for `FlightGear`_, *i.e.,* a
program whose purpose is to allow easy assembling and running of an
``fgfs`` command line.

.. _FGo!: https://sites.google.com/site/erobosprojects/flightgear/add-ons/fgo
.. _FlightGear: https://www.flightgear.org/
.. _Python: https://www.python.org/
.. _CondConfigParser: http://frougon.net/projects/CondConfigParser/

FFGo is written in `Python`_ 3 and is based on `CondConfigParser`_,
which allows many interesting things as shown at:

  http://frougon.net/projects/FFGo/doc/README-conditional-config/


Screenshots
-----------

Screenshots are available from the `FFGo screenshots gallery page
<http://frougon.net/projects/FFGo/gallery/>`_.

.. _end-of-intro:

Home page
---------

FFGo's home page is located at:

  http://frougon.net/projects/FFGo/

(it was on people.via.ecp.fr before April 30, 2016)


Requirements
------------

FFGo requires the following software:

  - Operating system:

      * works on Unix-like systems (including GNU/Linux);
      * works on Windows;
      * should also work on MacOS X, but no one has reported about this
        so far.

  - `FlightGear`_;
  - `Python`_ 3.4 or later;
  - `Tkinter`_ (part of the Python standard library; often known as
    ``python3-tk`` or ``python-tk`` in Linux package managers); very old
    versions that don't have the Ttk widget set are not supported
    starting from FFGo 1.8.0 (Tk 8.5 should be recent enough);
  - `CondConfigParser`_.

In addition to these mandatory dependencies, FFGo will take advantage of
the following software if installed:

  - `Pillow`_ (a PIL fork that supports Python 3); the corresponding
    `Debian`_ package is ``python3-pil.imagetk``;
  - `GeographicLib`_\'s ``MagneticField`` program, distributed with the
    GeographicLib C++ library. In Debian, this program is part of the
    ``geographiclib-tools`` package, but requires specific dataset files
    to be installed in order to work properly (the
    ``geographiclib-get-magnetic`` script may be helpful to get them
    installed);
  - `GeographicLib`_\'s implementation for Python 3 (present in Debian
    testing and unstable under the name ``python3-geographiclib`` at the
    time of this writing).

If some of these optional components are not installed, or if for some
reason FFGo can't find them, some features will be disabled or work in
degraded mode. For instance, aircraft thumbnails won't be displayed if
the Pillow library isn't installed for the Python interpreter used to
run FFGo.

.. _Tkinter: https://docs.python.org/3/library/tkinter.html
.. _Pillow: https://python-pillow.org/
.. _GeographicLib: https://geographiclib.sourceforge.io/

Note:

  The home pages of FFGo's dependencies indicated here are current at
  the time of this writing (January 2016), but might change over time.


Download
--------

The best place to download FFGo from is the `FFGo page on PyPI`_.
Specifically, tarballs for any version are available in the `download
area`_ (also packages in `wheel format`_ since FFGo 1.12.6).
Alternatively, FFGo tarballs and wheel files can be downloaded `from
Florent Rougon's home page <http://frougon.net/projects/FFGo/dist/>`_,
but since that site is served over plain http (not https), you should
get them from PyPI unless you know what you are doing.

.. _FFGo page on PyPI: https://pypi.org/project/FFGo/
.. _download area: https://pypi.org/project/FFGo/#files
.. _wheel format: https://www.python.org/dev/peps/pep-0427/


Git repository
--------------

FFGo is maintained in a `Git repository
<https://github.com/frougon/FFGo>`_ that can be cloned with::

  git clone https://github.com/frougon/FFGo.git


Debian packages
---------------

If you use Debian_, the first thing to do is, as usual, to check whether
there is an ``ffgo`` package in Debian proper. If not (which is the case
at the time of this writing), you can still install FFGo and its
dependencies with a simple::

  apt-get install ffgo

or

::

  aptitude install ffgo

etc., depending on your package manager of choice. For this to work, you
need to:

  - add the following lines to your ``/etc/apt/sources.list`` (given for
    Debian *unstable* here)::

      deb http://frougon.net/debian-ffgo unstable main
      deb-src http://frougon.net/debian-ffgo unstable main

    Packages for Debian *stable* are also available. If this is what you
    need, just replace *unstable* with *buster*, or whatever is the
    codename of the current Debian *stable* release, in these
    ``sources.list`` lines.

  - install `Florent Rougon's OpenPGP key`_ into the ``apt`` keyring (be
    sure to verify that this is the same key as served `by Github
    <https://github.com/frougon.gpg>`_ over https, after adding a
    trailing newline to the latter). This is necessary to allow ``apt``
    to authenticate the packages (if you don't do this, the installation
    should still be possible, but with warnings and, of course, reduced
    security).

    .. _Florent Rougon's OpenPGP key: http://frougon.net/keys.html

    In order to do this, you should first get the key using the above
    link, and save it to a file. Let's assume you have the key in file
    ``/tmp/OpenPGP-key.asc``. To add it to the ``apt`` keyring, you can
    run the following command as root::

      apt-key add /tmp/OpenPGP-key.asc

    Once this is done, there is no need to keep the ``OpenPGP-key.asc``
    file around anymore.

After these two steps, don't forget to run::

  apt-get update

(or ``aptitude update``, etc.), otherwise the package manager won't find
the packages available from the newly-added repository.

Notes:

  - The ``ffgo`` package recommends ``python3-pil.imagetk``. This
    package is available in Debian_. If you don't install it, FFGo will
    still work but you won't be able to see the aircraft thumbnails.

  - The ``deb-src`` line in ``/etc/apt/sources.list`` is useful if you
    want to be able to run::

      apt-get source ffgo

    or similar for its dependencies available from the repository given
    above (currently and for the foreseeable future, only
    CondConfigParser_). Otherwise, you may safely omit that line.

.. _Debian: https://www.debian.org/


Installation
------------

The detailed installation guide for FFGo is in the ``docs/INSTALL``
directory in any release tarball or zip file. In short:

  - If you are using Debian_, please see above.

  - FFGo may be run without installation, provided that all software
    requirements are installed.

  - Otherwise, FFGo can be installed in the standard way for Python
    packages, i.e. with::

      pip install FFGo

    If you have never used `pip`_ before, or if you need more details,
    read the guide in ``docs/INSTALL`` before running this command, and
    **don't invoke it as the superuser** unless you *really* know what
    you are doing!

    Besides FFGo, you may want to also install `Pillow`_ in order to see
    the aircraft thumbnails in FFGo. The presence of Pillow is detected
    at run time, therefore it doesn't matter if Pillow is installed
    before or after FFGo. Similarly, if you want to see magnetic
    variation and magnetic headings in addition to true headings, you'll
    need to install GeographicLib's ``MagneticField`` program. Finally,
    `GeographicLib`_\'s Python implementation is used for some geodetic
    calculations if installed for the Python interpreter used to run
    FFGo. Most computations can normally be done without this module,
    but it may be necessary in some particular cases (computation of
    distance and bearings for the shortest path between nearly antipodal
    points).

.. _pip: https://pypi.org/project/pip/

You may also find the installation instructions from `FFGo's page on the
FlightGear wiki`_ helpful. If you have a problem, you can always ask in
FFGo's thread on the FlightGear forum (see below in `Getting help,
discussing`_).

.. _FFGo's page on the FlightGear wiki: http://wiki.flightgear.org/FFGo


Running
-------

- If you've installed FFGo using a ready-made package (Linux or BSD
  distribution, etc.), just run ``ffgo`` from the command line, or
  choose FFGo in your desktop menu, etc.

- If you chose to run FFGo without installing it:

  From your file manager, you may click on the ``ffgo-launcher.py`` file
  in the top-level directory obtained after unpacking a release tarball
  or zip file. Alternatively, you can run it from a terminal with a
  command such as ``./ffgo-launcher.py`` or ``python3
  ffgo-launcher.py``. Just make sure you are running
  ``ffgo-launcher.py`` with the `Python`_ interpreter for which you
  installed the dependencies.

- Otherwise, if you installed FFGo with `pip`_:

  pip should have installed an ``ffgo`` executable in the directory it
  normally installs scripts into. This directory may be a ``Scripts``
  subdirectory of your Python installation, or a ``bin`` subdirectory of
  the virtual environment if you ran pip in a venv, etc. It depends on
  how you ran pip (inside or outside a venv, etc.). More details are
  given in ``docs/INSTALL``, and if this is not enough, please refer to
  the `pip`_ documentation.

  Note for Windows users:

    On Windows, `pip`_ will install an ``ffgo-noconsole.exe`` executable
    along with ``ffgo.exe`` (typically in ``C:\PythonXY\Scripts`` for a
    Python installation with version X.Y). The difference between these
    two files is that ``ffgo.exe`` opens a Windows terminal (“console”)
    containing all FFGo messages, while ``ffgo-noconsole.exe`` doesn't.

In any case, it is suggested that you skim through the documentation
available from the Help menu after you start FFGo. This will direct you
to the important first-time settings, hopefully give you useful tips,
etc.


Documentation
-------------

- Apart from this text (which corresponds to ``README.rst`` in a release
  tarball or zip file), FFGo's documentation can be found in the
  ``docs`` top-level directory after unpacking a release tarball or zip
  file. Once FFGo is installed, users should start by reading
  ``docs/README/README_<language code>`` (the language code is ``en``
  for English; this text is also accessible from FFGo's *Help* menu). In
  a second time, ``docs/README.conditional-config`` (`available online
  <http://frougon.net/projects/FFGo/doc/README-conditional-config/>`_)
  explains how to use the full power of the configuration system used by
  FFGo.

  If you got FFGo from the `Git repository`_ instead of a release tarball,
  part of the documentation is in source form only (written for
  `Sphinx`_). There is a special section in ``docs/INSTALL`` which
  explains how to build it in this situation [#]_. In any case, this
  documentation (for the latest FFGo release) is always `available online
  <http://frougon.net/projects/FFGo/doc/README-conditional-config/>`_.

  .. _Sphinx: https://www.sphinx-doc.org/

  .. [#] Basically, it boils down to installing a recent enough `Sphinx`_
         and running ``make doc`` from the top-level directory.

- There is also some `FFGo documentation on the FlightGear wiki`_, in
  particular screenshots illustrating most features, and maybe more
  practically-oriented installation instructions than those from
  ``docs/INSTALL/INSTALL_en`` (at the time of this writing).

  .. _FFGo documentation on the FlightGear wiki: http://wiki.flightgear.org/FFGo


Getting help, discussing
------------------------

At the time of this writing, there is a thread dedicated to FFGo on the
`FlightGear forum`_ at the following address:

  https://forum.flightgear.org/viewtopic.php?f=18&t=27054

.. _FlightGear forum: https://forum.flightgear.org/

This is where most discussions about FFGo take place. If you have a
question or a problem related to FFGo, this is a good place to ask.


Bugs
----

If you think you have found a bug, you can `file an issue on GitHub
<https://github.com/frougon/FFGo/issues>`_. If you are not sure that
what you are seeing is actually a bug, I suggest to discuss it instead
in the `FFGo forum thread`_. In either case, be very precise telling:

  - your operating system;

  - the versions of FFGo and its dependencies (Python, CondConfigParser,
    FlightGear... also Pillow and GeographicLib if you have them
    installed);

  - how you installed FFGo (with `pip`_, or a distribution package,
    or...);

  - the exact contents of the FFGo log file, which is
    ``~/.ffgo/Logs/FFGo.log`` on every operating system except Windows,
    and ``%APPDATA%/FFGo/Logs/FFGo.log`` on Windows.

    Note for Windows users:

      Since Windows seems to hide the ``%APPDATA%`` folder nowadays,
      Windows users may have to use their favorite search engine in
      order to find how to access this folder on their computer (hint:
      maybe
      `<http://www.blogtechnika.com/what-is-application-data-folder-in-windows-7/>`_,
      `<https://www.youtube.com/watch?v=Xa0H8lND9Qs>`_
      and
      `<https://docs.microsoft.com/en-us/windows/uwp/design/app-settings/store-and-retrieve-app-data>`_
      can be helpful);

  - step-by-step instructions describing what you did to trigger the bug.

The FFGo log file normally contains the versions of all major
dependencies of FFGo, therefore the second instruction above should be a
no-brainer if you carried out the fourth one correctly. These versions
should also be available using Help → About in FFGo.

.. _FFGo forum thread: https://forum.flightgear.org/viewtopic.php?f=18&t=27054


License
-------

FFGo is distributed under the terms of the `WTFPL`_ version 2, dated
December 2004.

.. _WTFPL: http://wtfpl.net/


.. 
  # Local Variables:
  # coding: utf-8
  # fill-column: 72
  # End:
