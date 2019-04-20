import asyncio
import traceback
from configparser import ConfigParser
from datetime import datetime
from sys import platform

import aiohttp
import discord
from discord.ext import commands

try:
    import uvloop
except ImportError:
    if platform == 'linux':
        print('Please install uvloop: `pip install uvloop`')
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
finally:
    loop = asyncio.get_event_loop()

config = ConfigParser()
config.read('config.ini')

initial_extensions = (
    'cogs.admin',
    'cogs.guild_log',
    'cogs.map_testing'
)


class DDNet(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='$', fetch_offline_members=True)

        self.loop = loop
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.config = config


    @property
    def guild(self) -> discord.Guild:
        return self.get_guild(self.config.getint('GENERAL', 'GUILD'))


    async def on_ready(self) -> None:
        self.start_time = datetime.utcnow()
        print(f'Logged in as {self.user} ({self.user.id})')
        print(f'discord.py version {discord.__version__}')

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}')
                print(traceback.format_exc())


    async def on_resumed(self) -> None:
        print('resumed..')


    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        await self.process_commands(message)


    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        ignored = (commands.CheckFailure, commands.CommandNotFound, discord.Forbidden)
        if isinstance(error, ignored):
            return


    def run(self) -> None:
        self.remove_command('help')
        super().run(self.config.get('AUTH', 'TOKEN'), reconnect=True)


if __name__ == '__main__':
    DDNet().run()
