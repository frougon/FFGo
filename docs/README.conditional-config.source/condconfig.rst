.. meta::
   :description: User documentation for FFGo's conditional configuration
                 feature
   :keywords: FFGo, condition, conditional, configuration, CondConfigParser


==================================
Conditional configuration for FFGo
==================================

Introduction
------------

FFGo uses `CondConfigParser`_, which opens up new possibilities regarding
what can be done with the configuration file. Specifically, the word
“configuration” in this document normally refers to the part of FFGo's
configuration file that is displayed in the main window, which you can use
to pass specific options to the FlightGear executable (typically,
:program:`fgfs`).

.. _CondConfigParser: http://frougon.net/projects/CondConfigParser/
.. _CondConfigParser Manual: http://frougon.net/projects/CondConfigParser/doc/

Notes:

  - If you actually look at FFGo's configuration file,
    :file:`{USER_DATA_DIR}/config` (where :file:`{USER_DATA_DIR}` is
    :file:`{$HOME}/.ffgo` on Unix, :file:`{%APPDATA%}/FFGo` on Windows), this
    corresponds to the part following the special marker line containing
    ``INTERNAL OPTIONS ABOVE. EDIT CAREFULLY!`` (which is an implementation
    detail and might change in the future).

  - The following description is somewhat informal, written with FFGo
    users in mind. For those who want more details, including a formal
    grammar specification of the configuration format, the reference
    document is the `CondConfigParser Manual`_.


Structure of the configuration in the simplest case
---------------------------------------------------

In the simplest case, the configuration is a sequence of lines with optional
comments. A :index:`comment <single: comments>` is started on a given line
with the ``#`` character and ends at the end of the line. Except where special
syntax described below is used, every non-blank line, after comment removal,
is passed as a single argument to :program:`fgfs`, preserving the order used
in the configuration.

Example::

  #--enable-auto-coordination

  --disable-hud-3d
  --callsign=H-ELLO

In this example, the ``--enable-auto-coordination`` option is not passed to
the FlightGear executable because it is commented out with the ``#``
character. The two remaining non-blank lines will be passed as two arguments
to :program:`fgfs`. They will be added after the options automatically set
by FFGo, such as :samp:`--aircraft={...}`, :samp:`--airport={...}`,
:samp:`--fg-scenery={...}`, etc.

Comments don't necessarily start at the beginning of a line. For instance,
a configuration such as::

  --prop:/instrumentation/nav/frequencies/selected-mhz=109.70 # OEJ
  --prop:/instrumentation/nav/radials/selected-deg=66
  --dme=nav1
  --adf2=413 # KÜHTAI (KTI)

will cause 4 options to be passed to :program:`fgfs`, namely::

  --prop:/instrumentation/nav/frequencies/selected-mhz=109.70
  --prop:/instrumentation/nav/radials/selected-deg=66
  --dme=nav1
  --adf2=413

The comments, as well as spaces preceding the ``#`` comment char, are
ignored. Similarly, spaces at the beginning of option lines are ignored,
but not spaces in the "middle" of an option. Thus, a line such as::

  --aircraft=A weird aircraft name

would be passed as a single argument to :program:`fgfs`, including the spaces
inside.

(and in case you find yourself in such a situation that you actually *need* to
include spaces at the beginning or end of an :program:`fgfs` argument, this is
possible; each of them must simply be preceded by a backslash, as explained
later in this document)

.. index::
   single: variable
   single: section; conditional

Variables and conditional sections
----------------------------------

.. index::
   single: section; default
   single: section; unconditional
   single: raw configuration line; default
   single: configuration line; default raw

The piece of configuration we have described in the previous paragraphs
defines arguments that are always passed to the FlightGear executable,
:program:`fgfs`, regardless of any condition. For this reason, it is called
the *default, unconditional section* in `CondConfigParser`_-speak; and the
lines contained within that section are called the *default raw
configuration lines*. However, you may want to have certain options passed
to :program:`fgfs` only in specific circumstances, such as starting at a
specific airport, using a specific aircraft, flying a helicopter, etc. This
is where CondConfigParser's variables and conditional sections come in
handy.

Suppose for instance that you often fly around Amsterdam Schiphol airport
(EHAM) and you want to have the COM1 and COM2 frequencies automatically set up
when you start FlightGear there. Of course, you can set :samp:`--com1={...}`
and :samp:`--com2={...}` in the default, unconditional section as we did
above. However, this method won't work as soon as you'll want to do the same
for several airports using different frequencies. In order to solve this
problem, you can use conditional sections like this::

  [ airport == "EHAM" ]
  --com1=121.975
  --com2=119.225

With such a section, the ``--com1`` and ``--com2`` options will only be passed
to :program:`fgfs` if the selected airport in FFGo is EHAM. The important
thing to note is that conditional sections must come *after* the default,
unconditional section. This is because a given conditional section ends at the
beginning of the next one (or at the end of the file, whichever comes first).
A blank line does not end any section, conditional or not. Therefore, a
complete configuration with two conditional sections could look like this::

  --callsign=H-ELLO
  --disable-hud-3d
  #--enable-auto-coordination
  #--log-class=input
  #--log-level=info

  # Uncomment these three lines to start at this specific location
  #--lat=50.8938820754
  #--lon=4.4689847385
  #--heading=63

  [ airport == "EHAM" ]
  --com1=121.975
  --com2=119.225

  [ airport == "EHRD" ]
  --com1=122.750
  --com2=127.025

.. index::
   single: variable; external

This example uses one external variable: ``airport``. It is said to be
*external* because it is not defined in this configuration, but
automatically set by FFGo when it interprets the configuration to compute
the argument list for the :program:`fgfs` command. The complete list of
external variables that `CondConfigParser`_ obtains from FFGo is, at the
time of this writing: ``aircraft``, ``aircraftDir``, ``airport``,
``parking``, ``runway``, ``carrier`` and ``scenarios``.

While external variables get their values from user selections in the FFGo
graphical user interface (GUI), other variables must be explicitely defined
at the beginning of the configuration, that is, before the default,
unconditional section. This is done in a special section delimited by
braces, like this::

  { var1 = value1
    var2 = value2
    ...
  }

As an example where using such a variable is convenient, let's consider
the following configuration::

  { custom_start_pos = "heli-H7" } # Only one variable defined here

  [ custom_start_pos == "parking" and airport == "EDDK" ]
  --lat=50.8768259714
  --lon=7.1222074126
  --heading=49

  [ custom_start_pos == "heli-H7" and airport == "EDDM" ] # helipad H7 at EDDM
  --lat=48.3595136857
  --lon=11.8043934004
  --heading=270

  [ custom_start_pos == "TFFJ-app" ] # Approach for TFFJ
  # Can override the option set from the GUI, see MERGED_OPTIONS below
  --airport=TFFJ
  --offset-distance=4.5
  --offset-azimuth=120
  --altitude=2500
  --heading=130
  --vc=120

This type of configuration allows one to easily customize the start position
(latitude, longitude, altitude and heading), as well as the initial speed of
the aircraft, or anything else that can be set from the :program:`fgfs`
command line [#]_. Which set of options is selected depends on the
:index:`predicates <single: predicate>` (the conditions between square
brackets), and therefore in this example on the selected airport and the
value given to the ``custom_start_pos`` variable at the beginning of the
configuration.

.. [#] Use :guilabel:`Help` → :guilabel:`Show available fgfs options` in
       FFGo to see the full option list or, equivalently, run
       ``fgfs --help --verbose`` from a terminal.

So, if you want to start at the defined parking position at EDDK, select
EDDK in the FFGo GUI and make sure you have::

  custom_start_pos = "parking"

in the brace-delimited section for variable assignments at the beginning of
the config. Similarly, you can easily start on the H7 helipad at EDDM by
choosing EDDM in the FFGo GUI and setting ``custom_start_pos`` to the string
``"heli-H7"``. The third conditional section in this example allows you to
easily practice landings at TFFJ by setting ``custom_start_pos`` to
``"TFFJ-app"`` (for aircraft models that support in-air startup).

Finally, if you don't want any of these options to be used, just set
``custom_start_pos`` to a value that doesn't satisfy any of the predicates,
for instance the empty string ``""``, or something like ``"-parking"``
(convenient if you often switch between the "parking" setting and the
default FFGo behavior—the one obtained without any specific configuration).

Note:

  These custom parking positions defined by latitude, longitude and heading
  are not very useful in airports where the scenery already has well-defined
  parking lots that can be directly selected in the FFGo GUI. Now that FFGo
  can read startup locations from ``apt.dat`` files, many airports offer
  startup locations that can be directly selected from the FFGo GUI, which
  makes this particular type of configuration less often needed than it used
  to be.

Another example, assuming you have installed the `ATCChatter add-on
<https://sourceforge.net/p/flightgear/fgaddon/HEAD/tree/trunk/Addons/ATCChatter/>`_,
could be the following::

  { enableATCChatter = True }

  [ enableATCChatter ]
  --config=/your/path/to/ATCChatter/config.xml
  --prop:string:/addons/ATCChatter/path=/your/path/to/ATCChatter
  --prop:float:/sim/sound/chatter/volume=0.6 # between 0.0 and 1.0

By changing the ``enableATCChatter = True`` into
``enableATCChatter = False``, you can easily decide whether to include
these three lines (the ``--config=...`` line and the two ``--prop:...``
lines) in your ``fgfs`` command line.


Advanced expressions
--------------------

.. index:: ! predicate

In the previous section, we have seen how to define and use variables and
conditional sections in the configuration read by FFGo (via
`CondConfigParser`_). As we have explained, each such section starts with a
condition, called a *predicate*, enclosed in square brackets (``[`` and
``]``). But what constitutes a valid predicate? Similarly, when writing a
variable assignment, what constitutes a valid right-hand side? The answer
given here will be kept slightly approximate in order to remain short and
relatively easy to understand. If you want the full details, please refer to
the `CondConfigParser Manual`_.

.. index::
   single: variable; external

Before diving into a somewhat verbose description, let's give a sample
configuration with a few conditional sections. This example makes use of
two external variables (``airport`` and ``aircraft``) that `CondConfigParser`_
obtains from FFGo. The other three variables used in the predicates
(``custom_start_pos``, ``instruments`` and ``condConfigParser_testing``) are
defined in the brace-delimited section for variable assignments at the
beginning of the configuration.

::

  { custom_start_pos = "" # You can use "parking", "manual", or anything else...
    instruments = "LOWI"
    # The corresponding section (see below) will be applied if this variable
    # is set to True.
    condConfigParser_testing = False }

  [ custom_start_pos == "parking" and airport == "LKPR" ]
  --lat=50.10427155972259
  --lon=14.26571160265325
  --heading=40

  [ custom_start_pos == "parking" and airport == "EIDW" and
    aircraft == "707" ] # I want to use a specific parking position for the 707
  --lat=53.4299148608
  --lon=-6.2488343207
  --heading=009

  [ instruments == "LFRS" or ((not instruments) and airport == "LFRS") or
    custom_start_pos == "LFRS-app" ] # Nantes Atlantique
  --nav1=29:109.9

  [ custom_start_pos == "LOWI-appW" ] # Approch from the west
  --fix=KTI08
  --altitude=13000
  --heading=137
  --vc=120

  [ instruments == "LOWI" or ((not instruments) and airport == "LOWI") or
    custom_start_pos in ["LOWI-appW", "LOWI-appE"] ]
  --prop:/instrumentation/nav/frequencies/selected-mhz=109.70 # OEJ
  #--prop:/instrumentation/nav/frequencies/standby-mhz=
  --prop:/instrumentation/nav/radials/selected-deg=66
  --dme=nav1
  --adf2=413 # KÜHTAI (KTI)

  [ instruments == "IFR tutorial" ]
  --prop:/instrumentation/comm/frequencies/selected-mhz=118.625
  --prop:/instrumentation/comm/frequencies/standby-mhz=910.00 # FGCom self-test
  #--prop:/instrumentation/comm[1]/frequencies/selected-mhz=
  #--prop:/instrumentation/comm[1]/frequencies/standby-mhz=
  --prop:/instrumentation/nav/frequencies/selected-mhz=114.1
  #--prop:/instrumentation/nav/frequencies/standby-mhz=
  --prop:/instrumentation/nav/radials/selected-deg=9
  --prop:/instrumentation/nav[1]/frequencies/selected-mhz=116.8
  --prop:/instrumentation/nav[1]/frequencies/standby-mhz=116.0
  --prop:/instrumentation/nav[1]/radials/selected-deg=114

  --dme=nav1

  [ condConfigParser_testing ]
  whatever argument(s) you want to pass to fgfs

.. index::
   single: expression; syntactic rules
   single: expression; orTest
   single: boolean; literal
   single: string
   single: list

The syntactic rules for expressions used in variable assignments and
predicates are deliberately close to those governing expressions in
Python, but there are less data types available than in Python and, to
this date, no functions, classes, etc. The syntactic element used for
the right-hand side of variable assignments is the same as for
predicates, after removal of the enclosing square brackets. In
`CondConfigParser`_'s grammar, it is called an *orTest* and is composed of
variable references and literals of one of these basic types:

  - boolean (``True`` or ``False``);
  - string, delimited by double quotes (``"``);
  - list, delimited by square brackets (``[`` and ``]``), the elements
    inside a list being separated by commas.

.. index::
   single: variable reference

A *variable reference* is a variable name used in an expression. For
instance::

  { heli1 = "ec130b4"
    other_heli = "uh1"
    my_helis = [heli1, "ec135p2", other_heli, "bo105"] }

In this example, two variables are assigned string literals and the
third variable (``my_helis``) is assigned a list defined using two string
literals (``"ec135p2"`` and ``"bo105"``) and two variable references
(``heli1`` and ``other_heli``).

.. index::
   single: variable name

A *variable name* is a sequence of ASCII letters, digits or underscore:

  - that is delimited by word boundaries (according to the Python re
    module);
  - that is not a keyword (``or``, ``and``, ``not``, ``in``, ``True``, ``False``).

Lists can be of arbitrary length, may contain any expression, including
other lists, and their nesting level is not limited by `CondConfigParser`_.

There is no integer nor float type in CondConfigParser, as it has not
seemed to be very useful for FFGo so far, however this might change in
the future.

So, what is allowed to go into the right-hand side of a variable
assignment or inside the predicate of a conditional section? Answer: any
number of the aforementioned basic type literals or variable references,
combined with the following operators and parentheses:

.. index::
   pair: boolean; operators

======================     =============================
Operator                   Meaning
======================     =============================
``==``, ``!=``, ``in``     equality and membership tests
``not``                    logical “not”
``and``                    logical “and”
``or``                     logical “or”
======================     =============================

(operators listed in decreasing order of precedence; those on the same
line have equal priority)

The ``in`` operator can be used to test:

  - whether a character (string of length 1) is part of a string;
  - whether an arbitrary object is equal to an element of a list.

(the objects need not be written literally: they can be specified via
variable references or even expressions)

Example:

  As a consequence of the preceding rules, the expression inside the
  predicate used in the above example::

    instruments == "LOWI" or ((not instruments) and airport == "LOWI") or
    custom_start_pos in ["LOWI-appW", "LOWI-appE"]

  is equivalent to::

    instruments == "LOWI" or (not instruments) and airport == "LOWI" or
    custom_start_pos in ["LOWI-appW", "LOWI-appE"]

  This is because ``and`` has a higher priority than ``or`` and ``==`` a
  higher priority than both of them. Since ``not`` has a higher priority
  than ``and``, it is also equivalent to the following expression,
  although I would advise against using it, because it will probably
  feel ambiguous to people not knowing the precise precedence rules::

    instruments == "LOWI" or not instruments and airport == "LOWI" or
    custom_start_pos in ["LOWI-appW", "LOWI-appE"]

The precedence rules between operators should be quite familiar to
Python programmers. When in doubt, you can always use parentheses.
Similarly, the way expressions are interpreted in boolean context tries
to mimic Python's behavior (example: a string or list is considered true
if, and only if, it is not empty).

Note:

  The ``and`` and ``or`` boolean operators are short circuit and return the
  last evaluated expression, as in Python.

.. index:: MHTG, Tegucigalpa, Toncontin, Honduras

A useful example of what can be done with lists could be the following::

  { custom_start_pos = "parking"    # "parking" or "manual" or ...
    instruments = ""                # "IFR tutorial" or "LOWI" or ...
    # Lists to be completed according to your needs
    gate_class = aircraft in ["777-200ER", "A320neo", "A330-203"]
    ga_class = aircraft in \
      ["c172p", "SenecaII", "Cub", "dr400-dauphin", "dhc6", "Dragonfly"]
  }

  # Toncontin Intl (Tegucigalpa, Honduras)
  [ custom_start_pos == "parking" and airport == "MHTG" and gate_class ]
  --lat=14.06054
  --lon=-87.21878
  --heading=288

  [ custom_start_pos == "parking" and airport == "MHTG" and ga_class ]
  --lat=14.05552
  --lon=-87.21387
  --heading=265

  [ instruments == "MHTG" or (not instruments) and airport == "MHTG" or
    custom_start_pos == "MHTG-app" ]
  --nav1=122:112.3 # Toncontin (TNT)

This simple configuration defines two different parking positions for
the Toncontin Intl airport, one for aircraft that take their passengers
via jet bridges (of class “gate”), the other for usually smaller
aircraft (“general aviation”, abbreviated “ga”). It also automatically
sets up the NAV1 frequency to 112.3 MHz and the radial to 122, which is
useful for the RNAV (RNP) approach of runway 02 (a particularly
interesting one!).

For FFGo to know which aircraft belongs to which class, we have defined
the two variables, ``gate_class`` and ``ga_class``, as booleans using
membership tests. Of course, you have to add the aircraft you fly to
the appropriate list if you want to use this feature. When you want to
start on a runway or on a parking position selected from the popup list
of FFGo's interface at the same airport, just replace ``"parking"`` with
something else (e.g., ``"-parking"``) on the first line, where the
``custom_start_pos`` variable is defined.

.. index:: helicopter

Another useful example to help fly helicopters as well as planes could
be the following::

  { custom_start_pos = "parking"  # can be changed to "heli-H5" for instance
    # Define a boolean variable ('heli_class') indicating whether the
    # selected aircraft is a helicopter. The list of helicopters given here
    # is incomplete, of course.
    heli_class = aircraft in \
      ["alouette2", "alouette2F", "Alouette-III_sc", "bo105",
       "ec130b4", "ec135p2", "M-XE", "s55", "s76c", "uh1", "uh60",
       "rah-66"] }

  [ heli_class ]
  # I need smaller throttle increments for helicopters than for planes
  # (this property is used by my mouse wheel binding, which controls the
  # throttle).
  --prop:/frougon/initial-mouse-wheel-throttle-step=0.004
  # You can conditionally load a specific joystick file here if you
  # wrap the contents like this:
  #
  #   <?xml version="1.0"?>
  #   <PropertyList><input><joysticks><js-named>
  #     <name>Logitech Attack 3</name>
  #
  #     [...]
  #
  #   </js-named></joysticks></input></PropertyList>
  --config=/some/file/of/yours/with/this/structure.xml

  [ not heli_class ]
  # Uncomment this if you want auto-coordination enabled for everything
  # but helicopters.
  # --enable-auto-coordination

  # Define a starting position for EBBR when using anything but a helicopter
  [ custom_start_pos == "parking" and airport == "EBBR" and not heli_class ]
  --lat=50.89939819021788
  --lon=4.487598394661401
  --heading=340

  # Predefined starting position at helipad H1 of EBBR
  [ airport == "EBBR" and
    (custom_start_pos == "heli-H1" or
     heli_class and custom_start_pos == "parking") ] # H1
  --lat=50.8975296235
  --lon=4.4906784598
  --heading=115

  # Predefined starting position at helipad H5 of EBBR. This one
  # requires specifically setting 'custom_start_pos' to "heli-H5";
  # The generic "parking" setting will select H1 if using a helicopter,
  # not H5.
  [ custom_start_pos == "heli-H5" and airport == "EBBR" ] # H5
  --lat=50.8938820754
  --lon=4.4689847385
  --heading=63

Finally, to give you an idea of what the syntax allows, here is a valid
configuration using the possibilities presented above. Of course, it is
very convoluted and completely artificial!

::

  { a = ["def", "ghi"]
    # The expression for 'b' contains 3 variables, 2 of which are external.
    # Its evaluation will return a nested list.
    b = [True, "jkl", aircraft, a, airport]
    c = parking == "XYZ0" and "ufo" in b
    d = (parking == "XYZ0") and ("ufo" in b) # same thing
    e = c == d # e will always evaluate to True

    foobar = True
    baz = [aircraft, "strange\tstring\nwith \
                      many escape sequences",
           ["list", "inside", "a", "list"]] or not ["bla"]
    zod = \
    [True, "you", "may", "reference", baz, "from here"] and \
    (a or b)
    blabla = zod # ["pouet"]   ← just a comment
  }

  --common-options
  --another-one     # with a comment
  # Option starting with a '[' followed by a space (the '[' at the
  # beginning of a line must be escaped)
  \[ spaces at the end of the line need escaping like this: \ # easy!
  --normal-option=value

  [ foobar and (airport == "KSFO" or
                (scenarios == ["nimitz_demo",
                               "clemenceau_demo",
                               "balloon_demo"]
                 or "wingman_demo" in scenarios
                 and aircraft != "777-200ER"))
  ]
  --lon=5.12358614
  # blabla
  --lat=40.1654116

  [ not e ]
  --oh no!


.. index::
   single: command line; assembling

Assembling the fgfs command line
--------------------------------

As we have seen, the configuration read by FFGo consists in an optional
section containing variable assignments followed by a possibly-empty
default, unconditional section, itself followed by zero or more conditional
sections. Let's explain how the various arguments (sometimes called
*options*) specified in these get assembled into an :program:`fgfs` command.

The rules used by default are pretty simple. The :program:`fgfs` program is
passed the following arguments in this order:

  - arguments derived from user settings in the FFGo graphical user
    interface (e.g., :samp:`--fg-root={...}`, :samp:`--fg-aircraft={...}`,
    :samp:`--fg-scenery={...}`, :samp:`--aircraft={...}`,
    :samp:`--airport={...}`, etc.);

  - arguments from the default, unconditional section;

  - arguments from each conditional section whose predicate is true
    (i.e., the sections that are said to be *applicable*).

For instance, let's consider the following configuration::

  { custom_start_pos = "parking" }

  #--enable-auto-coordination

  --callsign=H-ELLO
  --disable-hud-3d

  [ airport == "LFPO" ]
  --com1=118.700

  [ airport == "LFPO" and custom_start_pos == "parking" ]
  --lon=2.372079
  --lat=48.7275
  --heading=345

  [ airport == "LFPG" ]
  --com1=119.250
  --com2=121.800

  [ airport == "LFPG" and custom_start_pos == "parking" ]
  --lat=49.0075192
  --lon=2.5793183
  --heading=220

Assuming the selected airport in the FFGo user interface is LFPG, then the
:program:`fgfs` command issued by FFGo when the user clicks on the
:guilabel:`Run FG` button will be::

  fgfs <basic options> --callsign=H-ELLO \
                       --disable-hud-3d \
                       --com1=119.250 \
                       --com2=121.800 \
                       --lat=49.0075192 \
                       --lon=2.5793183 \
                       --heading=220

where :samp:`{<basic options>}` is a placeholder for the options
automatically added based on the settings in the FFGo user interface, as
mentioned above (:samp:`--aircraft={...}`, :samp:`--airport={...}`, etc.).

.. index::
   pair: redundant; options

Right, this is all nice and clean, but what happens when several applicable
sections declare the same or redundant :program:`fgfs` options? In some
cases, such as with ``--ai-scenario``, it can be useful to provide an option
several times. In other cases (e.g., with ``--airport``, ``--lat``...), it
doesn't make sense. Therefore, there is no “one size fits all” solution that
can automatically do the right thing here. But there is a mechanism in place
that can allow you, for some options explicitly listed in your
configuration, to have FFGo apply a “last occurence wins” policy.

.. index:: MERGED_OPTIONS

In order to use this mechanism, you must list one or more prefixes in a
special variable called ``MERGED_OPTIONS``. Let's illustrate this with a
simple example::

  { MERGED_OPTIONS = ["--airport=", "--aircraft=", "--parking-id=",
                      "--runway=", "--carrier=", "--parkpos=",
                      "--com1=", "--com2="] }

Now, suppose that, after filtering out all non-applicable sections, the
list of :program:`fgfs` arguments would be::

  --airport=LFPO --aircraft=777-200ER --com1=121.975 --com1=122.750
  --aircraft=c172p --aircraft=ec130b4 --nav1=57:110.55 --airport=LFML
  --disable-hud-3d --nav1=66:109.70

We have here three elements of ``MERGED_OPTIONS`` that are a prefix of at
least one of the arguments: ``--airport=``, ``--aircraft=`` and ``--com1=``.
For each of these prefixes, the corresponding arguments will be
automatically merged using the “last occurence wins” policy, resulting
in the following argument list::

  --airport=LFML --aircraft=ec130b4 --com1=122.750 --nav1=57:110.55
  --disable-hud-3d --nav1=66:109.70

(the two :samp:`--nav1={...}` options have not been merged because we didn't
include any corresponding prefix in ``MERGED_OPTIONS``)

As you can see, the first argument for a given prefix acts as a sort of
anchor: its position is kept (relatively to the other arguments), but
the “value” (what comes after the prefix) is replaced with the value of
the last argument that has the same prefix.

By default, ``MERGED_OPTIONS`` is empty, so this mechanism is not active
for any option. This is because there is no way to determine the “right”
default value that would work for present and future FlightGear
releases. As a consequence, it is up to you to ensure that your
configuration doesn't generate unwanted duplicate options—or at least,
if it does, make sure you are aware of the concerned options and what
consequences it has for FlightGear to have them passed several times on
the command line.


.. index::
   single: special characters
   single: escape sequences

Escaping rules for special characters
-------------------------------------

Generally speaking, you can split a configuration line without affecting
syntax by ending it with a backslash, as in many computer languages.
Some syntactic constructs don't need such precautions. In particular,
this is the case with grammar elements that start with an opening
bracket (``[``) or opening parenthesis (``(``). In these cases, newlines
don't matter: only the matching closing delimiter can terminate the
grammar element.

Escaping in raw configuration lines (fgfs arguments)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the previous sections of this document, we have introduced conditional
sections; if you remember well, these always start with an opening bracket
(``[``). This special character marks the beginning of a conditional
section's predicate, the end of which is marked by the matching closing
bracket (``]``). Then all following lines until either the end of the file
or the first opening bracket at the beginning of a line (after optional
spaces) belong to that conditional section: these are the lines containing
the :program:`fgfs` arguments. The opening bracket, if any, marks the start
of the next conditional section, and so on. But, what if you absolutely need
to pass :program:`fgfs` an argument that starts with an opening bracket (or
spaces, for that matter—same problem)?

Granted, this kind of situation sounds rather unusual. Nevertheless,
`CondConfigParser`_ provides a way to do such things, which should not be
much of a surprise to programmers. The technique used to solve the
problem is *backslash escaping*. This means that, in order to use a
special character (here, an opening bracket or a space) without
retaining its special meaning for the grammar in use, just as if it were
an ordinary character, you have to precede it with a backslash (``\``).
So, a conditional section passing :program:`fgfs` the argument
``[arg inside brackets]`` could look like this::

  [ variable == "foobar" ]
  \[arg inside brackets]
  --other-argument
  \[this is also allowed, for symmetry reasons\]

As the last line illustrates, ``\]`` is also accepted as an escape sequence
for ``]``. And if you need to pass :program:`fgfs` an argument containing a
backslash, you have to use the ``\\`` escape sequence, i.e., double every
backslash you want to include as a normal character. There are a few more
escape sequences that can be used in :program:`fgfs` arguments (called *raw
configuration lines* in `CondConfigParser`_-speak). The authoritative
documentation for these is in the FFGo code (currently:
:file:`ffgo/fgcmdbuilder.py:FGCommandBuilder.processRawConfigLines()`). For
information, here is the complete list at the time of this writing:

+-----------------------+-------------------+----------------------------------+
| Escape sequence       | Meaning           | Comments                         |
+=======================+===================+==================================+
| ``\\``                | ``\``             | produces a single backslash      |
+-----------------------+-------------------+----------------------------------+
| ``\[``                | ``[``             | useful at the beginning of a     |
|                       |                   | line to avoid confusion with the |
|                       |                   | start of a predicate             |
+-----------------------+-------------------+----------------------------------+
| ``\]``                | ``]``             | for symmetry with ``\[``         |
+-----------------------+-------------------+----------------------------------+
| ``\#``                | ``#``             | literal ``#`` character, doesn't |
|                       |                   | start a comment                  |
+-----------------------+-------------------+----------------------------------+
| ``\t``                | tab character     |                                  |
+-----------------------+-------------------+----------------------------------+
| ``\n``                | newline character | doesn't start a new option       |
+-----------------------+-------------------+----------------------------------+
| :samp:`\\{<space>}`   | space character   | useful to include a space at the |
|                       |                   | end of an option, which would be |
|                       |                   | ignored without the backslash    |
+-----------------------+-------------------+----------------------------------+
| :samp:`\\{<newline>}` | continuation line | makes as if the next line were   |
|                       |                   | really the continuation of the   |
|                       |                   | current line, with the           |
|                       |                   | :samp:`\\{<newline>}` escape     |
|                       |                   | sequence removed                 |
+-----------------------+-------------------+----------------------------------+

Yes, the last one means you can split a very long :program:`fgfs` option into
several lines if you want, like this::

  [ variable == "foobar" ]
  --this-is-a-very-very-very-very-very-very-very-very-very-very-very\
  -very-very-very-very-very-very-very-very-very-very-very-very-very\
  -very-very-very-long-option
  --normal-option

Escaping in string literals
^^^^^^^^^^^^^^^^^^^^^^^^^^^

String literals in `CondConfigParser`_ also support some kind of escaping
mechanism to allow for instance to write string literals containing
double quotes. Example::

  { abc = "bla \"waouuh\" bla" }

This short variable assignments section defines the variable ``abc`` as a
string containing three words separated by spaces, the second word being
enclosed in double quotes. At the time of this writing, the escape
sequences supported in CondConfigParser's string literals are:

=====================      ===================
Escape sequence            Meaning
=====================      ===================
``\\``                     ``\``
``\t``                     tab character
``\n``                     newline character
``\"``                     ``"``
:samp:`\\{<newline>}`      continuation line
=====================      ===================

For the definitive reference on these escape sequences, please consult
the `CondConfigParser Manual`_.


.. For Emacs:
   Local Variables:
   coding: utf-8
   fill-column: 76
   End:
