# Makefile to prepare the FFGo directory tree after a "git clone" operation
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

include shared.mk
DOC_FORMATS := html

default: icons update-mo

icons:
	$(MAKE) -C share/icons

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

dist: default doc
	git archive --format=tar --prefix=$(PROGNAME)-$(version)/ \
          -o dist/$(PROGNAME)-$(version).tar master

	tmpdir=$$(mktemp --tmpdir --directory \
                         tmp.$(PROGNAME)-tarball.XXXXXXXXXXXXXXX) && \
          mkdir -p $(addprefix "$$tmpdir"/$(PROGNAME)-$(version)/,share/icons/ \
            docs/README.conditional-config \
            $(foreach lang,$(LANGUAGES),data/locale/$(lang)/LC_MESSAGES)) && \
          cp -a docs/README.conditional-config.source/_build/html \
            "$$tmpdir"/$(PROGNAME)-$(version)/docs/README.conditional-config/en && \
          cp -at "$$tmpdir"/$(PROGNAME)-$(version)/share/icons \
            $(foreach size,$(PROG_ICON_SIZES),share/icons/$(size)x$(size)) && \
          for lang in $(LANGUAGES); do \
            cp -t "$$tmpdir"/$(PROGNAME)-$(version)/data/locale/$$lang/LC_MESSAGES \
               data/locale/$$lang/LC_MESSAGES/messages.mo; \
          done && \
          \
          tar --file=dist/$(PROGNAME)-$(version).tar -C "$$tmpdir" --append \
          $(addprefix $(PROGNAME)-$(version)/,docs/README.conditional-config \
            $(foreach \
             size,$(PROG_ICON_SIZES),share/icons/$(size)x$(size)/ffgo.png) \
            $(foreach \
             lang,$(LANGUAGES),data/locale/$(lang)/LC_MESSAGES/messages.mo)) && \
          gzip -9 --force dist/$(PROGNAME)-$(version).tar && \
          \
          rm -rf "$$tmpdir"

clean:
	$(MAKE) -C share/icons clean && \
          $(MAKE) -C data/locale clean && \
          $(MAKE) -C docs/README.conditional-config.source clean

.PHONY: default icons update-pot update-po update-mo doc dist clean
