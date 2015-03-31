# Makefile to generate */fgo.png in various sizes from scalable/fgo.svg
# (tested with GNU Make)
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

SIZES := 16 24 32 48 64 128 256

define CONVERT_RULE =
$(1)x$(1)/fgo.png: scalable/fgo.svg
	mkdir -p '$(1)x$(1)' && \
          rsvg-convert --width='$(1)' --keep-aspect-ratio --format=png \
                 --output='$$@' '$$<'
endef

PNG_FILES := $(foreach size,$(SIZES),$(size)x$(size)/fgo.png)

all: $(PNG_FILES)

# This line writes the conversion rule (target, prerequisite and recipe)
# for each size in $(SIZES).
$(foreach size,$(SIZES),$(eval $(call CONVERT_RULE,$(size))))

clean:
	rm -f $(PNG_FILES)

.PHONY: all clean
