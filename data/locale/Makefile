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

include ../../shared.mk # Define LANGUAGES
include Makefile.py-functions # Define variables containing Python 3 code
PYTHON := python3
MO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/FFGo.mo)
PO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/FFGo.po)

default: $(MO_FILES)

$(MO_FILES): %.mo: %.po
	msgfmt -o '$@' '$<'

# Used in the recipe for the FFGo.po files (using Make variable expansion,
# as in $(var), doesn't handle newlines correctly when expanded inside a
# recipe)
export check_and_replace_po_metadata

$(PO_FILES): %.po: FFGo.pot
	msgmerge --update --backup=none '$@' '$<'
	$(PYTHON) -c "$$check_and_replace_po_metadata" '$@'

# Used in the recipe for FFGo.pot (using Make variable expansion, as in
# $(var), doesn't handle newlines correctly when expanded inside a recipe)
export replace_pot_metadata

# File paths relative to the package root directory (containing the ffgo script)
REL_PY_FILES := ffgo $(shell cd ../.. && find src -type f -name '*.py')

# The target could be FFGo.pot, with dependencies on the source files
# (similar to REL_PY_FILES, but with ../../ prepended). However, this would
# cause the PO files to be updated too often (e.g., after a user cloned the
# repo and ran 'make', the PO files would be updated if there were new
# translatable strings, and he would end up with locally-modified files).
update-pot:
	xgettext --directory=../.. --language=Python --from-code=UTF-8 \
                 --msgid-bugs-address='$(MSGID_BUGS_ADDRESS)' \
                 --output=- $(REL_PY_FILES) | \
          $(PYTHON) -c "$$replace_pot_metadata" >FFGo.pot
        # Set 'Project-Id-Version' metadata
	$(PYTHON) -c "$$check_and_replace_po_metadata" FFGo.pot

# Convenience phony targets
update-po: $(PO_FILES)
update-mo: $(MO_FILES)

clean:
	rm -f $(MO_FILES) FFGo.pot

.PHONY: default clean update-pot update-po update-mo
