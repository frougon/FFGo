# Makefile to prepare the FFGo directory tree after a "git clone" operation
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

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
SIZES := 16 24 32 48 64 128 256
LANGUAGES := de en es fr it ja nl pl

dist: default doc
	git archive --format=tar --prefix=FFGo-$(version)/ \
          -o dist/FFGo-$(version).tar master

	tmpdir=$$(mktemp --tmpdir --directory \
                         tmp.FFGo-tarball.XXXXXXXXXXXXXXX) && \
          mkdir -p $(addprefix "$$tmpdir"/FFGo-$(version)/,share/icons/ \
              docs/README.conditional-config \
              $(foreach lang,$(LANGUAGES),data/locale/$(lang)/LC_MESSAGES)) && \
          cp -a docs/README.conditional-config.source/_build/html \
                "$$tmpdir"/FFGo-$(version)/docs/README.conditional-config/en && \
          cp -at "$$tmpdir"/FFGo-$(version)/share/icons \
             $(foreach size,$(SIZES),share/icons/$(size)x$(size)) && \
          for lang in $(LANGUAGES); do \
            cp -t "$$tmpdir"/FFGo-$(version)/data/locale/$$lang/LC_MESSAGES \
                  data/locale/$$lang/LC_MESSAGES/messages.mo; \
          done && \
          \
          tar --file=dist/FFGo-$(version).tar -C "$$tmpdir" --append \
          $(addprefix FFGo-$(version)/,docs/README.conditional-config \
            $(foreach size,$(SIZES),share/icons/$(size)x$(size)/ffgo.png) \
            $(foreach lang,$(LANGUAGES),data/locale/$(lang)/LC_MESSAGES/messages.mo)) && \
          gzip -9 --force dist/FFGo-$(version).tar && \
          \
          rm -rf "$$tmpdir"

clean:
	$(MAKE) -C share/icons clean && \
          $(MAKE) -C data/locale clean && \
          $(MAKE) -C docs/README.conditional-config.source clean

.PHONY: default icons update-pot update-po update-mo doc dist clean
