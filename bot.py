import sys
import traceback
import datetime
import logging
import contextlib

import discord
from discord.ext import commands

from cogs.utils.credentials import DISCORDBOT_TOKEN


@contextlib.contextmanager
def setup_logging():
    try:
        # __enter__
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='ddnet.log', encoding='utf-8', mode='w')
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)


initial_extensions = [
    'cogs.member_log',
    'cogs.profilecard',
    'cogs.testing_main',
    'cogs.testing_archiving',
    'cogs.testing_moderation',
    'cogs.twstatus'
]


class DDNet(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='$', description='DDNet Discordbot', pm_help=None)
        self.remove_command('help')

        if __name__ == '__main__':
            for extension in initial_extensions:
                try:
                    self.load_extension(extension)
                except Exception as e:
                    print(f'Failed to load extension {extension}.', file=sys.stderr)
                    traceback.print_exc()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send('This command cannot be used in private messages.')
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(f'{error.original.__class__.__name__}: {error.original}', file=sys.stderr)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        print(f'Logged in as {self.user}\ndiscord.py version {discord.__version__}')

    async def on_resumed(self):
        print('resumed...')

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def close(self):
        await super().close()

    def run(self):
        super().run(DISCORDBOT_TOKEN, reconnect=True)


bot = DDNet()

with setup_logging():
    bot.run()