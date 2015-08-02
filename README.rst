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

.. figure:: screenshot1.png
   :target: http://people.via.ecp.fr/~flo/projects/FFGo/screenshots/screenshot1.png
   :alt: screenshot with the Command Window integrated into the main window

   Screenshot with the Command Window integrated into the main window

   In this first screenshot, the font size is a bit too large to let a
   descent amount of space available for the Command Window (at the
   bottom, in gray). But just as the Output Window, it can be detached
   from the main window: see the next screenshot.

.. figure:: screenshot2.png
   :target: http://people.via.ecp.fr/~flo/projects/FFGo/screenshots/screenshot2.png
   :alt: screenshot with the Command Window detached from the main window

   Screenshot with the Command Window detached from the main window


.. _end-of-intro:

Home page
---------

FFGo's home page is located at:

  http://people.via.ecp.fr/~flo/projects/FFGo/


Requirements
------------

FFGo relies on the following software:

  - Unix-like operating system (e.g, GNU/Linux; Windows and MacOS X
    untested, feedback welcome);
  - `FlightGear`_;
  - `Python`_ 3.4 or later;
  - `Tkinter`_ (often known as ``python3-tk`` or ``python-tk`` in Linux
    package managers);
  - `Pillow`_ (a PIL fork that supports Python 3) [#]_;
  - `CondConfigParser`_.

.. [#] This library is not mandatory to run FFGo, but aircraft thumbnails
       won't be displayed without it.

.. _Tkinter: https://docs.python.org/3/library/tkinter.html
.. _Pillow: http://python-pillow.github.io/

Note:

  The home pages of FFGo's dependencies indicated here are current at
  the time of this writing (August 2015) but might change over time.


Download
--------

Ready-to-use tarballs (once the dependencies are installed) can be
downloaded from:

  http://people.via.ecp.fr/~flo/projects/FFGo/dist/


Git repository
--------------

FFGo is maintained in a `Git repository
<https://github.com/frougon/FFGo>`_ that can be cloned with::

  git clone https://github.com/frougon/FFGo.git


Installation
------------

This program requires no installation, just unpack the archive anywhere
and make sure that all software requirements are met before the first
start. If you need help to install these dependencies, you may consult
the guide in ``docs/INSTALL``. You have to make sure the dependencies
are installed for the `Python`_ interpreter that you are going to use to
run FFGo.


Running
-------

From your file manager, you may click on the ``ffgo`` file in the
top-level directory obtained after unpacking a release tarball.
Alternatively, you can run it from a terminal with a command such as
``./ffgo`` or ``python3 ffgo``. Just make sure you are running ``ffgo``
with the `Python`_ interpreter for which you installed the dependencies.

Note:

  Future versions may provide more conventional packaging allowing
  installations and upgrades with `pip`_.

.. _pip: https://pypi.python.org/pypi/pip


Documentation
-------------

Apart from this text (which corresponds to ``README.rst`` in a release
tarball), FFGo's documentation can be found in the ``docs`` top-level
directory after unpacking a release tarball. Once FFGo installed, users
should start by reading ``docs/README`` (also accessible from FFGo's
*Help* menu). In a second time, ``docs/README.conditional-config``
(`available online
<http://people.via.ecp.fr/~flo/projects/FFGo/doc/README-conditional-config/>`_)
will teach them how to use the full power of the configuration system
used by FFGo.

If you got FFGo from the `Git repository`_ instead of a release tarball,
part of the documentation is in source form only (written for
`Sphinx`_). There is a special section in ``docs/INSTALL`` which
explains how to build it in this situation [#]_. In any case, this
documentation (for the latest FFGo release) is always `available online
<http://people.via.ecp.fr/~flo/projects/FFGo/doc/README-conditional-config/>`_.

.. _Sphinx: http://sphinx-doc.org/

.. [#] Basically, it boils down to installing a recent enough `Sphinx`_
       and running ``make doc`` from the top-level directory.

.. 
  # Local Variables:
  # coding: utf-8
  # fill-column: 72
  # End:
