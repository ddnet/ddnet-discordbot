#!/bin/bash
DIR=data/map-testing
$DIR/../tools/render_map/render_map $DIR/maps/$1 --size 1280
mv $DIR/maps/$1.png $DIR/thumbnails/${1::-4}.png
