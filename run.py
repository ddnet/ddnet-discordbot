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


def setup_logger(name, level, filename, propagate):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate

    handler = logging.FileHandler(filename, 'a', encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s]: %(message)s', '%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.WARNING)

# root logger
setup_logger(None, logging.INFO, 'logs/bot.log', propagate=True)

# tickets logger
setup_logger('tickets', logging.INFO, 'logs/tickets.log', propagate=False)


async def main():
    config = ConfigParser()
    config.read('config.ini')

    try:
        pool = await asyncpg.create_pool()
        logging.info('Successfully connected to PostgresSQL')
    except (ConnectionRefusedError, asyncpg.CannotConnectNowError):
        return logging.exception('Failed to connect to PostgreSQL, exiting')

    session = aiohttp.ClientSession(loop=loop)

    bot = DDNet(config=config, pool=pool, session=session)
    await bot.start(config.get('AUTH', 'DISCORD'))


if __name__ == '__main__':
    loop.run_until_complete(main())
