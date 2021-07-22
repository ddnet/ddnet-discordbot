#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO
from typing import List, Tuple
from urllib.parse import quote

import asyncpg
import msgpack
import requests
from colorthief import ColorThief
from PIL import Image

from utils.color import pack_rgb
from utils.text import normalize

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

BG_PATH = Path('data/assets/map_backgrounds/')

VALID_TILES = (
    'NPH_START',
    'NPC_START',
    'HIT_START',
    'EHOOK_START',
    'SUPER_START',
    'JETPACK_START',
    'WALLJUMP',
    'WEAPON_SHOTGUN',
    'WEAPON_GRENADE',
    'WEAPON_RIFLE',
    'POWERUP_NINJA'
)

BG_SIZE = (800, 500)

def get_tiles(packdir: Path, name: str) -> List[str]:
    pack = packdir / f"{name}.msgpack"

    with pack.open("rb") as p:
        unpacker = msgpack.Unpacker(p, use_list=False, raw=False)
        unpacker.skip()             # width
        unpacker.skip()             # height
        tiles = unpacker.unpack()   # tiles

    return [t for t in tiles if t in VALID_TILES]

def get_background(thumbdir: Path, name: str) -> int:
    thumb = thumbdir / f"{normalize(name)}.png"
    with thumb.open("rb") as t:
        img = Image.open(t).convert('RGBA').resize(BG_SIZE)
        img.save(BG_PATH / name)

        color = ColorThief(t).get_color(quality=1)
    return pack_rgb(color)

def get_data(relfile: Path, packdir: Path, thumbdir: Path) -> List[Tuple[str, datetime, str, List[str], str]]:
    out = []

    with relfile.open("r") as f:
        for line in f:
            line = line.rstrip()
            timestamp, _, details = line.split('\t')

            try:
                _, name, mappers = details.split('|')
            except ValueError:
                _, name = details.split('|')
                mappers = None

            # This is an attempt at making updates incremental
            if (BG_PATH / f"{name}.png").is_file():
                continue

            out.append((
                name,
                datetime.strptime(timestamp, '%Y-%m-%d %H:%M'),
                mappers,
                get_tiles(packdir, name),
                get_background(thumbdir, name)
            ))

    return out

async def update_database(data):
    con = await asyncpg.connect()
    async with con.transaction():
        query = """INSERT INTO stats_maps_static (name, timestamp, mappers, tiles, color)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (name) DO UPDATE
                   SET timestamp = $2, mappers = $3, tiles = $4, color = $5;
                """
        await con.executemany(query, data)

    await con.close()

    return f'stats_maps_static: INSERT {len(data)}'

def main(relfile, packdir, thumbdir):
    data = get_data(relfile, packdir, thumbdir)
    status = asyncio.run(update_database(data)) if data else 'Nothing to update'

    print(f'[{TIMESTAMP}] Successfully updated: {status}')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: {} <releases-file> <msgpack-dir> <thumbnail-dir>".format(sys.argv[0]))
        sys.exit(1)

    (relfile, packdir, thumbdir) = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    if not relfile.is_file() or not packdir.is_dir() or not thumbdir.is_dir():
        print("Invalid arguments")
        exit(1)

    if not BG_PATH.is_dir():
        print(f"{BG_PATH} is not a directory")

    main(relfile, packdir, thumbdir)
