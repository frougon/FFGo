# Makefile for generating localization files (the .pot file from the Python
# sources, the .po files from the .pot file and the .mo files from their .po
# sources). Tested on Linux with GNU Make.
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

define POT_COPYRIGHT
Copyright (C) 2010-2015  Robert Leda
Copyright (C) 2014-2015  Florent Rougon
endef
MSGID_BUGS_ADDRESS := f.rougon@free.fr

PYTHON := python3
LANGUAGES := de en es fr it ja nl pl
MO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.mo)
PO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.po)
include Makefile.py-functions # Define variables containing Python 3 code

all: $(MO_FILES)

$(MO_FILES): %.mo: %.po
	msgfmt -o '$@' '$<'

# Used in the recipe for the messages.po files (using Make variable expansion,
# as in $(var), doesn't handle newlines correctly when expanded inside a
# recipe)
export check_and_replace_po_metadata

$(PO_FILES): %.po: messages.pot
	msgmerge --update --backup=none '$@' '$<'
	$(PYTHON) -c "$$check_and_replace_po_metadata" '$@'

# Used in the recipe for messages.pot (using Make variable expansion, as in
# $(var), doesn't handle newlines correctly when expanded inside a recipe)
export replace_pot_metadata

PY_FILES := ../../ffgo $(shell find ../../src -type f -name '*.py')
# File paths relative to the package root directory (containing the ffgo script)
REL_PY_FILES := ffgo $(shell cd ../.. && find src -type f -name '*.py')

messages.pot: $(PY_FILES)
	xgettext --directory=../.. --language=Python --from-code=UTF-8 \
                 --msgid-bugs-address='$(MSGID_BUGS_ADDRESS)' \
                 --output=- $(REL_PY_FILES) | \
          $(PYTHON) -c "$$replace_pot_metadata" > '$@'
        # Set 'Project-Id-Version' metadata
	$(PYTHON) -c "$$check_and_replace_po_metadata" '$@'

# Convenience phony targets
update-pot: messages.pot
update-po: $(PO_FILES)
update-mo: $(MO_FILES)

clean:
	rm -f $(MO_FILES) messages.pot

.PHONY: all clean update-pot update-po update-mo
