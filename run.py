#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from configparser import ConfigParser

import aiohttp
import asyncpg
import uvloop

from bot import DDNet

uvloop.install()
loop = asyncio.get_event_loop()

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.WARNING)

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler('logs/bot.log', 'a', encoding='utf-8')
fmt = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s]: %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(fmt)
log.addHandler(handler)

async def main():
    config = ConfigParser()
    config.read('config.ini')

    try:
        pool = await asyncpg.create_pool()
    except (ConnectionRefusedError, asyncpg.CannotConnectNowError):
        return log.exception('Failed to connect to PostgreSQL, exiting')

    session = aiohttp.ClientSession(loop=loop)

    bot = DDNet(config=config, pool=pool, session=session)
    await bot.start(config.get('AUTH', 'DISCORD'))

if __name__ == '__main__':
    loop.run_until_complete(main())
