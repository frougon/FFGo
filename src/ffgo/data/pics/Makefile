# Makefile to generate images from their source
# (tested with GNU Make)
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

default: thumbnail-no-Pillow.gif thumbnail-not-avail.png

thumbnail-no-Pillow.gif: thumbnail-no-Pillow.svg
	rsvg-convert --width=171 --height=128 --format=png \
                     --output=thumbnail-no-Pillow.png '$<' && \
        convert thumbnail-no-Pillow.png '$@' && \
        rm thumbnail-no-Pillow.png

thumbnail-not-avail.png: thumbnail-not-avail.xcf
	convert -background transparent -flatten '$<' '$@'

clean:
	rm -f thumbnail-no-Pillow.png thumbnail-no-Pillow.gif

.PHONY: default clean
