# Makefile to prepare the FGo! directory tree after a "git clone" operation
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

DOC_FORMATS := html

all: icons l10n_files

icons:
	$(MAKE) -C share/icons

l10n_files:
	$(MAKE) -C data/locale

update-pot:
	$(MAKE) -C data/locale update-pot
update-po:
	$(MAKE) -C data/locale update-po
update-mo:
	$(MAKE) -C data/locale update-mo

doc:
	$(MAKE) -C docs/README.conditional-config.source $(DOC_FORMATS)


version := $(shell PYTHONPATH="src:$$PYTHONPATH" python -c \
                   'from version import __version__; print(__version__)')
dist: doc
	git archive --format=tar -o dist/fgo-$(version).tar master
	mkdir -p docs/README.conditional-config
	cp -a docs/README.conditional-config.source/_build/html \
          docs/README.conditional-config/en
	tar --append --file=dist/fgo-$(version).tar \
          docs/README.conditional-config
	gzip -9 --force dist/fgo-$(version).tar

clean:
	$(MAKE) -C share/icons clean && \
          $(MAKE) -C data/locale clean && \
          $(MAKE) -C docs/README.conditional-config.source clean

.PHONY: all icons l10n_files update-pot update-po update-mo doc dist clean
