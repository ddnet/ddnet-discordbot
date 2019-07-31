#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import gc
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime
from io import BytesIO
from typing import Tuple

import asyncpg
import msgpack
import requests

gc.disable()

config = ConfigParser()
config.read('config.ini')

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
PLAYERS_FILE_URL = 'https://ddnet.tw/players.msgpack'

def unpack_stats() -> Tuple[tuple, tuple, tuple, dict]:
    resp = requests.get(PLAYERS_FILE_URL)
    buf = BytesIO(resp.content)
    buf.seek(0)

    unpacker = msgpack.Unpacker(buf, use_list=False, raw=True, max_array_len=2147483647, max_map_len=2147483647)
    unpacker.skip()                         # Server types: `(type, ...)`
    unpacker.skip()                         # Maps: `{type: ((map, points, finishers), ...), ...}`
    unpacker.skip()                         # Total points: `points`
    stats_points = unpacker.unpack()        # Points: `((player, points), ...)`
    unpacker.skip()                         # Weekly points: `((player, points), ...)`
    unpacker.skip()                         # Monthly points: `((player, points), ...)`
    stats_teamranks = unpacker.unpack()     # Team rank points: `((player, points), ...)`
    stats_ranks = unpacker.unpack()         # Solo rank points: `((player, points), ...)`
    unpacker.skip()                         # Servers: `{type: (points, ((player, points), ...)), ...}`
    stats_players = unpacker.unpack()       # Players: `{player: ({map: (teamrank, rank, finishes, timestamp, time), ...}, {country: finishes, ...}), ...}`

    return stats_points, stats_teamranks, stats_ranks, stats_players

def sort_stats(stats_points: tuple, stats_teamranks: tuple, stats_ranks: tuple, stats_players: dict) -> dict:
    out = defaultdict(dict)

    types = (
        ('points', stats_points),
        ('teamrank', stats_teamranks),
        ('rank', stats_ranks)
    )

    for type_, stats in types:
        rank = 0
        skips = 1
        prev_points = 0
        for player, points in stats:
            if points != prev_points:
                prev_points = points
                rank += skips
                skips = 1
            else:
                skips += 1

            out[player][type_] = (rank, points)

    for player, (_, countries) in stats_players.items():
        # '', 'AUS', 'BRA', 'CAN', 'CHL', 'CHN', 'FRA', 'GER', 'GER2', 'IRN', 'KSA', 'RUS', 'USA', 'ZAF'
        if countries:
            eu_countries = (b'', b'FRA', b'GER', b'GER2')  # '' = OLD (GER)
            eu_finishes = sum(countries.pop(c, 0) for c in eu_countries)
            if eu_finishes:
                countries[b'EUR'] = eu_finishes

            # sort alphabetically to get consistent results
            country = max(sorted(countries.items()), key=lambda c: c[1])[0]
            out[player]['country'] = country

    return out

async def update_database(stats: dict) -> str:
    records = []
    default = (None, None)
    for player, details in stats.items():
        records.append((
            player.decode(),
            *details.get('points', default),
            *details.get('teamrank', default),
            *details.get('rank', default),
            details.get('country', b'UNK').decode()
        ))

    con = await asyncpg.connect(user = 'ddnet-discordbot',
                                password = config.get('AUTH', 'PSQL'),
                                host = 'localhost',
                                database = 'ddnet-discordbot')

    async with con.transaction():
        await con.execute('TRUNCATE stats_players RESTART IDENTITY;')
        return await con.copy_records_to_table('stats_players', records=records)

    await con.close()

async def main():
    stats = unpack_stats()
    stats = sort_stats(*stats)
    result = await update_database(stats)

    print(f'[{TIMESTAMP}] Successfully updated: {result}')

if __name__ == '__main__':
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except Exception as exc:
        print(f'[{TIMESTAMP}] Failed to update: {exc}')
