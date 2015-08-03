# Makefile to generate */ffgo.png in various sizes from scalable/ffgo.svg
# (tested with GNU Make)
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

include ../../shared.mk # Define PROG_ICON_SIZES

define CONVERT_RULE =
$(1)x$(1)/ffgo.png: scalable/ffgo.svg
	mkdir -p '$(1)x$(1)' && \
          rsvg-convert --width='$(1)' --keep-aspect-ratio --format=png \
                 --output='$$@' '$$<'
endef

PNG_FILES := $(foreach size,$(PROG_ICON_SIZES),$(size)x$(size)/ffgo.png)

all: $(PNG_FILES)

# This line writes the conversion rule (target, prerequisite and recipe)
# for each size in $(PROG_ICON_SIZES).
$(foreach size,$(PROG_ICON_SIZES),$(eval $(call CONVERT_RULE,$(size))))

clean:
	rm -f $(PNG_FILES)

.PHONY: all clean
