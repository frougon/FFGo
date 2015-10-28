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
.. _FlightGear: http://www.flightgear.org/
.. _Python: https://www.python.org/
.. _CondConfigParser: http://people.via.ecp.fr/~flo/projects/CondConfigParser/

FFGo is written in `Python`_ 3 and is based on `CondConfigParser`_,
which allows many interesting things as shown at:

  http://people.via.ecp.fr/~flo/projects/FFGo/doc/README-conditional-config/


Screenshots
-----------

Screenshots are available from the `FFGo home page
<http://people.via.ecp.fr/~flo/projects/FFGo/>`_.

.. _end-of-intro:

Home page
---------

FFGo's home page is located at:

  http://people.via.ecp.fr/~flo/projects/FFGo/


Requirements
------------

FFGo relies on the following software:

  - Operating system:

      * GNU/Linux surely works, as should any Unix-like system;
      * Windows should work, please report;
      * MacOS X should also work, except maybe for MacOS-specific Tcl/Tk
        bugs as explained at
        `<https://www.python.org/download/mac/tcltk/>`_. Please report.

  - `FlightGear`_;
  - `Python`_ 3.4 or later;
  - `Tkinter`_ (part of the Python standard library; often known as
    ``python3-tk`` or ``python-tk`` in Linux package managers);
  - `CondConfigParser`_;
  - `Pillow`_ (a PIL fork that supports Python 3) [#]_; the
    corresponding Debian package is ``python3-pil.imagetk``.

.. [#] This library is not mandatory to run FFGo, but aircraft thumbnails
       won't be displayed without it.

.. _Tkinter: https://docs.python.org/3/library/tkinter.html
.. _Pillow: http://python-pillow.github.io/

Note:

  The home pages of FFGo's dependencies indicated here are current at
  the time of this writing (August 2015) but might change over time.


Download
--------

Release tarballs or zip files can be downloaded from:

  http://people.via.ecp.fr/~flo/projects/FFGo/dist/


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

etc. depending on your package manager of choice. For this to work, you
only need to add the following lines to your ``/etc/apt/sources.list``
(given for Debian *unstable* here)::

  deb http://people.via.ecp.fr/~flo/debian-ffgo unstable main
  deb-src http://people.via.ecp.fr/~flo/debian-ffgo unstable main

Packages for Debian *stable* are also available. If this is what you
need, just replace *unstable* with *jessie*, or whatever is the
codename of the current Debian *stable* release, in these
``sources.list`` lines.

Don't forget to run::

  apt-get update

(or ``aptitude update``, etc.) after adding the two lines, otherwise the
package manager won't find the packages available from the newly-added
repository.

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
    before or after FFGo.

.. _pip: https://pypi.python.org/pypi/pip


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
  the virtual environment if you ran it in a venv, etc. It depends on
  how you ran pip (inside or outside a venv, etc.). More details are
  given in ``docs/INSTALL``, and if this is not enough, please refer to
  the `pip`_ documentation.

In any case, it is suggested that you skim through the available help
from the Help menu after you start FFGo. This will direct you to the
important first-time settings, hopefully give you useful tips, etc.


Documentation
-------------

Apart from this text (which corresponds to ``README.rst`` in a release
tarball or zip file), FFGo's documentation can be found in the ``docs``
top-level directory after unpacking a release tarball or zip file. Once
FFGo is installed, users should start by reading ``docs/README/README_en``
(``en`` being for the English version; this text is also accessible from
FFGo's *Help* menu). In a second time,
``docs/README.conditional-config`` (`available online
<http://people.via.ecp.fr/~flo/projects/FFGo/doc/README-conditional-config/>`_)
explains how to use the full power of the configuration system used by
FFGo.

If you got FFGo from the `Git repository`_ instead of a release tarball,
part of the documentation is in source form only (written for
`Sphinx`_). There is a special section in ``docs/INSTALL`` which
explains how to build it in this situation [#]_. In any case, this
documentation (for the latest FFGo release) is always `available online
<http://people.via.ecp.fr/~flo/projects/FFGo/doc/README-conditional-config/>`_.

.. _Sphinx: http://sphinx-doc.org/

.. [#] Basically, it boils down to installing a recent enough `Sphinx`_
       and running ``make doc`` from the top-level directory.


Getting help, discussing
------------------------

At the time of this writing, there is a thread dedicated to FFGo on the
FlightGear forum at the following address:

  http://forum.flightgear.org/viewtopic.php?f=18&t=27054


Bugs
----

If you think you have found a bug, you can `file an issue on GitHub
<https://github.com/frougon/FFGo/issues>`_. If you are not sure that
what you are seeing is actually a bug, I suggest to discuss it instead
in the `FFGo forum thread`_. In either case, be very precise telling:

  - your operating system;

  - the versions of FFGo and its dependencies (Python, CondConfigParser,
    FlightGear... also Pillow if the problem is image-related);

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
      `<http://windows.microsoft.com/en-us/windows-8/what-appdata-folder>`_
      can be helpful);

  - step-by-step instructions describing what you did to trigger the bug.

The FFGo log file normally contains the versions of all major
dependencies of FFGo, therefore the second instruction above should be a
no-brainer if you carried out the fourth one correctly. These versions
should also be available using Help → About in FFGo.

.. _FFGo forum thread: http://forum.flightgear.org/viewtopic.php?f=18&t=27054


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
