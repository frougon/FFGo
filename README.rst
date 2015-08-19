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
  - `CondConfigParser`_.
  - `Pillow`_ (a PIL fork that supports Python 3) [#]_;

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


Installation
------------

The detailed installation guide for FFGo is in the ``docs/INSTALL``
directory in any release tarball or zip file. In short:

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
