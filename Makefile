# Makefile to prepare the FGo! directory tree after a "git clone" operation
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

all: icons l10n_files

icons:
	$(MAKE) -C share/icons

l10n_files:
	$(MAKE) -C data/locale

clean:
	$(MAKE) -C share/icons clean && \
          $(MAKE) -C data/locale clean

.PHONY: all icons l10n_files clean
