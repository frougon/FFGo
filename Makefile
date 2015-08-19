# Makefile to prepare the FFGo directory tree after a "git clone" operation
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

DOC_FORMATS := html

default: icons update-mo

icons:
	$(MAKE) -C share/icons
	$(MAKE) -C ffgo/data/pics

update-pot:
	$(MAKE) -C ffgo/data/locale update-pot
update-po:
	$(MAKE) -C ffgo/data/locale update-po
update-mo:
	$(MAKE) -C ffgo/data/locale update-mo

doc:
	$(MAKE) -C docs/README.conditional-config.source $(DOC_FORMATS)

clean:
	$(MAKE) -C share/icons clean && \
          $(MAKE) -C ffgo/data/locale clean && \
          $(MAKE) -C ffgo/data/pics clean && \
          $(MAKE) -C docs/README.conditional-config.source clean

.PHONY: default icons update-pot update-po update-mo doc clean
