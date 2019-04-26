#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.admin',
    'cogs.guild_log',
    'cogs.map_testing',
    'cogs.misc',
    'cogs.votes',
)


class DDNet(commands.Bot):
    def __init__(self, **kwargs) -> None:
        super().__init__(command_prefix='$', fetch_offline_members=True)

        self.config = kwargs.pop('config')
        self.pool = kwargs.pop('pool')
        self.session = kwargs.pop('session')


    @property
    def guild(self) -> discord.Guild:
        return self.get_guild(self.config.getint('GENERAL', 'GUILD'))


    async def on_ready(self) -> None:
        self.start_time = datetime.utcnow()
        log.info('Logged in as %s (ID: %d)', self.user, self.user.id)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as exc:
                log.exception('Failed to load extension %s: %s', extension, exc)
            else:
                log.info('Successfully loaded extension %s', extension)


    async def on_resumed(self) -> None:
        log.info('Resumed')


    async def close(self) -> None:
        log.info('Closing')
        await super().close()
        await self.pool.close()
        await self.session.close()


    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        await self.wait_until_ready()
        await self.process_commands(message)


    async def on_command(self, ctx: commands.Context) -> None:
        log.info('%s (ID: %d) used %s (channel ID: %d)', ctx.author, ctx.author.id, ctx.message.content, ctx.channel.id)


    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        ignored = (commands.CheckFailure, commands.CommandNotFound, discord.Forbidden)
        if isinstance(error, ignored):
            return
