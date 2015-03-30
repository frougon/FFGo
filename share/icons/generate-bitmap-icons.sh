#! /bin/sh
#
# generate-bitmap-icons.sh -- Generate */fgo.png in various sizes from
#                             scalable/fgo.svg.
# Run this script from its containing directory.
#
# Copyright (C) 2015  Florent Rougon
# License: DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE version 2, dated
#          December 2004

for size in 16 24 32 48 64 128 256; do
    dir="${size}x${size}"
    mkdir -p "$dir" && \
    rsvg-convert --width="$size" --keep-aspect-ratio --format=png \
                 --output="$dir/fgo.png" scalable/fgo.svg
done
