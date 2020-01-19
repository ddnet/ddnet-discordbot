#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import asyncpg
import msgpack
import requests

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

PLAYERS_FILE_URL = 'https://ddnet.tw/players.msgpack'

def unpack_stats():
    resp = requests.get(PLAYERS_FILE_URL)
    buf = BytesIO(resp.content)
    buf.seek(0)

    unpacker = msgpack.Unpacker(buf, use_list=False, raw=True, max_array_len=2147483647, max_map_len=2147483647)
    unpacker.skip()                         # Server types: `(type, ...)`
    stats_maps = unpacker.unpack()          # Maps: `{type: ((map, points, finishers), ...), ...}`
    unpacker.skip()                         # Total points: `points`
    stats_points = unpacker.unpack()        # Points: `((player, points), ...)`
    unpacker.skip()                         # Weekly points: `((player, points), ...)`
    unpacker.skip()                         # Monthly points: `((player, points), ...)`
    stats_teamranks = unpacker.unpack()     # Team rank points: `((player, points), ...)`
    stats_ranks = unpacker.unpack()         # Solo rank points: `((player, points), ...)`
    unpacker.skip()                         # Servers: `{type: (points, ((player, points), ...)), ...}`
    stats_players = unpacker.unpack()       # Players: `{player: ({map: (teamrank, rank, finishes, timestamp, time), ...}, {country: finishes, ...}), ...}`

    return stats_maps, stats_points, stats_teamranks, stats_ranks, stats_players

def sort_stats(stats_maps, stats_points, stats_teamranks, stats_ranks, stats_players):
    out = {
        'players': defaultdict(dict),
        'finishes': defaultdict(lambda: defaultdict(int)),
        'maps': {
            map_: [server.decode(), points, finishers, []]
            for server, maps in stats_maps.items()
            for map_, points, finishers in maps
        }
    }

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

            out['players'][player][type_] = (rank, points)

    for player, (maps, countries) in stats_players.items():
        for map_, (_, rank, _, timestamp, time) in maps.items():
            if 1 <= rank <= 10:  # there are invalid rank 0s for some reason
                out['maps'][map_][3].append((player.decode(), rank, time))

            points = out['maps'][map_][1]
            if points > 0 and not timestamp.startswith(b'2030'):  # 2030 is used as the identifier for corrupt records
                out['finishes'][player][timestamp[:10]] += points

        # '', 'AUS', 'BRA', 'CAN', 'CHL', 'CHN', 'FRA', 'GER', 'GER2', 'IRN', 'KSA', 'RUS', 'USA', 'ZAF'
        if countries:
            eu_countries = (b'', b'FRA', b'GER', b'GER2')  # '' = OLD (GER)
            eu_finishes = sum(countries.pop(c, 0) for c in eu_countries)
            if eu_finishes:
                countries[b'EUR'] = eu_finishes

            # sort alphabetically to get consistent results
            out['players'][player]['country'] = max(sorted(countries.items()), key=lambda c: c[1])[0]

    return out

async def update_database(data):
    tables = defaultdict(list)

    for player, details in data['players'].items():
        tables['stats_players'].append((
            player.decode(),
            *details.get('points', (None, None)),
            *details.get('teamrank', (None, None)),
            *details.get('rank', (None, None)),
            details.get('country', b'UNK').decode()
        ))

    tables['stats_finishes'] = [
        (player.decode(), datetime.strptime(timestamp.decode(), '%Y-%m-%d'), points)
        for player, dates in data['finishes'].items()
        for timestamp, points in dates.items()
    ]

    for map_, details in data['maps'].items():
        ranks = sorted(details.pop(3), key=lambda r: (r[1], r[0]))[:10]
        tables['stats_maps'].append((map_.decode(), *details, ranks))

    con = await asyncpg.connect()
    async with con.transaction():
        status = []
        for table, records in tables.items():
            await con.execute(f'TRUNCATE {table} RESTART IDENTITY;')
            msg = await con.copy_records_to_table(table, records=records)
            status.append(f'{table}: {msg}')

    await con.close()

    return ', '.join(status)

def main():
    stats = unpack_stats()
    data = sort_stats(*stats)
    status = asyncio.run(update_database(data))

    print(f'[{TIMESTAMP}] Successfully updated: {status}')


if __name__ == '__main__':
    main()
