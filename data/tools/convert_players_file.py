#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime

import asyncpg

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

async def main():
    with open('players-file.json', 'r') as f:
        data = json.loads(f.read())

    tables = defaultdict(list)

    for player, details in data['players'].items():
        if len(player) > 15:
            print(player)
            continue

        tables['stats_players'].append((
            player,
            *details.get('points', (None, None)),
            *details.get('teamrank', (None, None)),
            *details.get('rank', (None, None)),
            details.get('country', 'UNK')[:3]
        ))

    tables['stats_finishes'] = [
        (player, datetime.strptime(timestamp, '%Y-%m-%d'), points)
        for player, dates in data['finishes'].items()
        for timestamp, points in dates.items() if len(player) <= 15
    ]

    for map_, details in data['maps'].items():
        ranks = sorted([tuple(r) for r in details.pop(3)], key=lambda r: (r[1], r[0]))[:10]
        tables['stats_maps'].append((map_, *details, ranks))

    con = await asyncpg.connect()
    async with con.transaction():
        status = []
        for table, records in tables.items():
            await con.execute(f'TRUNCATE {table} RESTART IDENTITY;')
            print(table)
            msg = await con.copy_records_to_table(table, records=records)
            status.append(f'{table}: {msg}')

    await con.close()

    os.remove('players-file.json')
    print(f'[{TIMESTAMP}] Successfully updated:', ', '.join(status))


if __name__ == '__main__':
    asyncio.run(main())
