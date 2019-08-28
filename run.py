#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys
from configparser import ConfigParser
from datetime import datetime

import aiohttp
import asyncpg
import uvloop

from bot import DDNet

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()

TIMESTAMP = datetime.utcnow().strftime('%Y-%m-%d_%H.%M.%S.%f')

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.WARNING)

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename=f'logs/{TIMESTAMP}.log', encoding='utf-8', mode='w')
fmt = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s]: %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(fmt)
log.addHandler(handler)

async def main():
    config = ConfigParser()
    config.read('config.ini')

    try:
        pool = await asyncpg.create_pool(user = 'ddnet-discordbot',
                                         password = config.get('AUTH', 'PSQL'),
                                         host = 'localhost',
                                         database = 'ddnet-discordbot')

        with open('data/schema.sql', 'r') as f:
            await pool.execute(f.read())
    except (ConnectionRefusedError, asyncpg.CannotConnectNowError):
        return log.exception('Failed to connect to PostgreSQL, exiting')

    session = aiohttp.ClientSession(loop=loop)

    bot = DDNet(config=config, pool=pool, session=session)
    await bot.start(config.get('AUTH', 'DISCORD'))

if __name__ == '__main__':
    loop.run_until_complete(main())
