#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys
from configparser import ConfigParser

import aiohttp
import asyncpg

from bot import DDNet

try:
    import uvloop
except ImportError:
    if sys.platform == 'linux':
        print('Please install uvloop with `pip install uvloop`')
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
finally:
    loop = asyncio.get_event_loop()

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.WARNING)

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename='ddnet.log', encoding='utf-8', mode='a')
fmt = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s]: %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(fmt)
log.addHandler(handler)


async def main():
    config = ConfigParser()
    config.read('config.ini')

    try:
        password = config.get('AUTH', 'PSQL')
        psql = f'postgresql://ddnet-discordbot:{password}@localhost/ddnet-discordbot'
        pool = await asyncpg.create_pool(psql)
    except (ConnectionRefusedError, asyncpg.CannotConnectNowError) as exc:
        return log.exception('Failed to connect to PostgreSQL: %s, exiting', exc)

    session = aiohttp.ClientSession(loop=loop)

    bot = DDNet(config=config, pool=pool, session=session)
    await bot.start(config.get('AUTH', 'DISCORD'))


if __name__ == '__main__':
    loop.run_until_complete(main())
