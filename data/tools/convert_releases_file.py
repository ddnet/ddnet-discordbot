#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import asyncpg
import msgpack
import requests
from colorthief import ColorThief
from PIL import Image

from utils.color import pack_rgb
from utils.text import normalize

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

BG_PATH = 'data/assets/map_backgrounds/{0}.png'

RELEASES_FILE_URL = 'https://ddnet.tw/releases/releases'
MSGPACK_URL = 'https://ddnet.tw/maps/{0}.msgpack'
THUMBNAIL_URL = 'https://ddnet.tw/ranks/maps/{0}.png'

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

def get_tiles(name: str) -> List[str]:
    resp = requests.get(MSGPACK_URL.format(name))
    buf = BytesIO(resp.content)

    unpacker = msgpack.Unpacker(buf, use_list=False, raw=False)
    unpacker.skip()             # width
    unpacker.skip()             # height
    tiles = unpacker.unpack()   # tiles
    return [t for t in tiles if t in VALID_TILES]

def get_background(name: str) -> int:
    name = normalize(name)

    resp = requests.get(THUMBNAIL_URL.format(name))
    buf = BytesIO(resp.content)

    img = Image.open(buf).convert('RGBA').resize(BG_SIZE)
    img.save(BG_PATH.format(name))

    color = ColorThief(buf).get_color(quality=1)
    return pack_rgb(color)

def get_data() -> List[Tuple[str, datetime, str, List[str], str]]:
    out = []

    resp = requests.get(RELEASES_FILE_URL)
    for line in resp.text.splitlines():
        timestamp, _, details = line.split('\t')

        try:
            _, name, mappers = details.split('|')
        except ValueError:
            _, name = details.split('|')
            mappers = None

        if os.path.isfile(BG_PATH.format(normalize(name))):
            continue

        out.append((
            name,
            datetime.strptime(timestamp, '%Y-%m-%d %H:%M'),
            mappers,
            get_tiles(name),
            get_background(name)
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

def main():
    data = get_data()
    status = asyncio.run(update_database(data)) if data else 'Nothing to update'

    print(f'[{TIMESTAMP}] Successfully updated: {status}')


if __name__ == '__main__':
    main()
