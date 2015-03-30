# Makefile to generate the .mo l10n files from their .po sources
# (tested with GNU Make)
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

LANGUAGES := de en es fr it ja nl pl
MO_FILES := $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.mo)

all: $(MO_FILES)

$(MO_FILES): %.mo: %.po
	msgfmt -o '$@' '$<'

clean:
	rm -f $(MO_FILES)

.PHONY: all clean
