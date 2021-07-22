#!/usr/bin/env python2
from __future__ import print_function

import sys
import json
import shutil
import zipfile
from collections import defaultdict
from io import BytesIO

import msgpack
import requests
from diskcache import Cache

# This script has to run in py2 due to ddnet-scripts/servers/scripts/players.py
def convert(ppack, cache):
    data = {}

    with open(ppack, "rb") as pack:
        unpacker = msgpack.Unpacker(pack, use_list=False, raw=True)
        unpacker.skip()                         # Server types: `(type, ...)`
        data['maps'] = unpacker.unpack()        # Maps: `{type: ((map, points, finishers), ...), ...}`
        unpacker.skip()                         # Total points: `points`
        data['points'] = unpacker.unpack()      # Points: `((player, points), ...)`
        unpacker.skip()                         # Weekly points: `((player, points), ...)`
        unpacker.skip()                         # Monthly points: `((player, points), ...)`
        data['teamrank'] = unpacker.unpack()    # Team rank points: `((player, points), ...)`
        data['rank'] = unpacker.unpack()        # Solo rank points: `((player, points), ...)`
        unpacker.skip()                         # Servers: `{type: (points, ((player, points), ...)), ...}`

    if not data:
        print("Empty or invalid msgpack")
        sys.exit(2)

    with zipfile.ZipFile(cache, 'r') as zf:
        zf.extractall()

    out = {
        'players': defaultdict(dict),
        'finishes': defaultdict(lambda: defaultdict(int)),
        'maps': {
            map_: [server, points, finishers, []]
            for server, maps in data['maps'].items()
            for map_, points, finishers in maps
        }
    }

    for type_ in ('points', 'teamrank', 'rank'):
        rank = 0
        skips = 1
        prev_points = 0
        for player, points in data[type_]:
            if points != prev_points:
                prev_points = points
                rank += skips
                skips = 1
            else:
                skips += 1

            out['players'][player][type_] = (points, rank)

    with Cache('players-cache') as cache:
        for player, _ in data['points']:
            try:
                maps, countries = cache[player]
            except KeyError:
                continue

            for map_, (_, rank, _, timestamp, time) in maps.items():
                if 1 <= rank <= 10:  # there are invalid rank 0s for some reason
                    out['maps'][map_][3].append((player, rank, time))

                points = out['maps'][map_][1]
                if points > 0 and not isinstance(timestamp, str):  # if timestamp is a string, the rank is corrupt
                    out['finishes'][player][str(timestamp.date())] += points

            # '', 'AUS', 'BRA', 'CAN', 'CHL', 'CHN', 'FRA', 'GER', 'GER2', 'IRN', 'KSA', 'RUS', 'USA', 'ZAF'
            if countries:
                eu_countries = (b'', b'FRA', b'GER', b'GER2')  # '' = OLD (GER)
                eu_finishes = sum(countries.pop(c, 0) for c in eu_countries)
                if eu_finishes:
                    countries[b'EUR'] = eu_finishes

                # sort alphabetically to get consistent results
                out['players'][player]['country'] = max(sorted(countries.items()), key=lambda c: c[1])[0]

    shutil.rmtree('players-cache')

    with open('players-file.json', 'w') as f:
        json.dump(out, f)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: {} <players-msgpack> <players-cache>".format(sys.argv[0]))
        sys.exit(1)

    convert(sys.argv[1], sys.argv[2])
