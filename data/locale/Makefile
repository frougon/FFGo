# Makefile for generating localization files (the .pot file from the Python
# sources, the .po files from the .pot file and the .mo files from their .po
# sources). Tested on Linux with GNU Make.
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

PROGNAME := FFGo
VERSION := $(shell PYTHONPATH="../../src:$$PYTHONPATH" python -c \
                   'from version import __version__; print(__version__)')
define POT_COPYRIGHT
Copyright (C) 2010-2015  Robert Leda
Copyright (C) 2014-2015  Florent Rougon
endef
MSGID_BUGS_ADDRESS := f.rougon@free.fr

PYTHON := python3
LANGUAGES := de en es fr it ja nl pl
MO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.mo)
PO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.po)

all: $(MO_FILES)

$(MO_FILES): %.mo: %.po
	msgfmt -o '$@' '$<'

$(PO_FILES): %.po: messages.pot
	msgmerge --update --backup=none '$@' '$<'

# Convenience phony targets
update-pot: messages.pot
update-po: $(PO_FILES)
update-mo: $(MO_FILES)

define replace_metadata
import sys, re, textwrap

while True:
    line = sys.stdin.readline()
    if re.match("^# *$$", line):
        break
    elif not line:
        sys.exit("gettext-generated header not found")

print(textwrap.indent(
      """LANGUAGE translations for $(PROGNAME) version $(VERSION).
$(POT_COPYRIGHT)
Copyright (C) YEARS  TRANSLATOR <EMAIL@ADDRESS>
This file is distributed under the same license as the $(PROGNAME) package.""",
      "# ") + "\n#")

sys.stdout.write(sys.stdin.read())
sys.exit(0)
endef

# Used in the recipe for messages.pot (using Make variable expansion, as in
# $(var), doesn't handle newlines correctly when expanded inside a recipe)
export replace_metadata

PY_FILES := ../../ffgo $(shell find ../../src -type f -name '*.py')
# File paths relative to the package root directory (containing the ffgo script)
REL_PY_FILES := ffgo $(shell cd ../.. && find src -type f -name '*.py')

messages.pot: $(PY_FILES)
	xgettext --directory=../.. --language=Python --from-code=UTF-8 \
                 --msgid-bugs-address='$(MSGID_BUGS_ADDRESS)' \
                 --output=- $(REL_PY_FILES) | \
          $(PYTHON) -c "$$replace_metadata" > '$@'

clean:
	rm -f $(MO_FILES) messages.pot

.PHONY: all clean update-pot update-po update-mo
