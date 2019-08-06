#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
import traceback
from datetime import datetime

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.admin',
    'cogs.guild_log',
    'cogs.map_testing',
    'cogs.meme',
    'cogs.misc',
    'cogs.profile',
    'cogs.records',
    'cogs.testing_archiving',
    'cogs.votes',
)


class DDNet(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix='$', fetch_offline_members=True, help_command=commands.MinimalHelpCommand())

        self.config = kwargs.pop('config')
        self.pool = kwargs.pop('pool')
        self.session = kwargs.pop('session')

    @property
    def guild(self) -> discord.Guild:
        return self.get_guild(self.config.getint('GENERAL', 'GUILD'))

    async def on_ready(self):
        self.start_time = datetime.utcnow()
        log.info('Logged in as %s (ID: %d)', self.user, self.user.id)

        # TODO: move this to __init__
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                log.exception('Failed to load extension %r', extension)
            else:
                log.info('Successfully loaded extension %r', extension)

    async def on_resumed(self):
        log.info('Resumed')

    async def close(self):
        log.info('Closing')
        await super().close()
        await self.pool.close()
        await self.session.close()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        await self.wait_until_ready()
        await self.process_commands(message)

    async def register_command(self, ctx: commands.Context):
        if ctx.command is None:
            return

        if ctx.guild is None:
            destination = 'Private Message'
            guild_id = None
        else:
            destination = f'#{ctx.channel} ({ctx.guild})'
            guild_id = ctx.guild.id

        log.info('%s used command in %s: %s', ctx.author, destination, ctx.message.content)

        query = """INSERT INTO stats_commands (guild_id, channel_id, author_id, timestamp, command, failed)
                   VALUES ($1, $2, $3, $4, $5, $6);
                """
        values = (
            guild_id,
            ctx.channel.id,
            ctx.author.id,
            ctx.message.created_at,
            ctx.command.qualified_name,
            ctx.command_failed
        )

        await self.pool.execute(query, *values)

    async def on_command_completion(self, ctx: commands.Context):
        await self.register_command(ctx)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await self.register_command(ctx)

        command = ctx.command
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'{self.command_prefix}{command.qualified_name} {command.signature}')
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.Forbidden):
                await ctx.send('I do not have proper permission')
            elif not (hasattr(command, 'on_error') or hasattr(command.cog, 'cog_command_error')):
                # handle uncaught errors
                exc = ''.join(traceback.format_exception(type(original), original, original.__traceback__))
                log.error('Command %r caused an exception\n%s', command.qualified_name, exc)
                await ctx.send('An internal error occurred')

    async def on_error(self, event: str, *args, **kwargs):
        log.exception('Event %r caused an exception:', event)
