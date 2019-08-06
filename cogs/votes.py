#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import Union

import discord
from discord.ext import commands

VOTE_YES    = '<:f3:397431188941438976>'
VOTE_NO     = '<:f4:397431204552376320>'


class Votes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._votes = {}
        self._vote_callers = set()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
        if user.bot:
            return

        message = reaction.message
        if message.id not in self._votes:
            return

        emoji = str(reaction.emoji)
        if emoji == VOTE_YES:
            self._votes[message.id] += 1
        elif emoji == VOTE_NO:
            self._votes[message.id] -= 1
        else:
            try:
                await reaction.remove(user)
            except discord.Forbidden:
                return

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
        if user.bot:
            return

        message = reaction.message
        if message.id not in self._votes:
            return

        emoji = str(reaction.emoji)
        if emoji == VOTE_YES:
            self._votes[message.id] -= 1
        elif emoji == VOTE_NO:
            self._votes[message.id] += 1

    @commands.Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, _):
        if message.id not in self._votes:
            return

        self._votes[message.id] = 0

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild and (ctx.channel.id, ctx.author.id) not in self._vote_callers

    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CheckFailure) and ctx.guild and not isinstance(error, commands.MissingPermissions):
            await ctx.send('You can only call one vote at a time')
        elif isinstance(error, commands.BadArgument):
            await ctx.send('Could not find that user')

    async def _kick(self, ctx: commands.Context, user: discord.Member, reason: str) -> int:
        channel = ctx.channel
        author = ctx.author

        msg = f'{author} called for vote to kick {user} ({reason})'
        try:
            message = await ctx.send(msg)
        except discord.Forbidden:
            return

        self._votes[message.id] = 0
        self._vote_callers.add((channel.id, author.id))

        try:
            await message.add_reaction(VOTE_YES)
            await message.add_reaction(VOTE_NO)
        except discord.Forbidden:
            # *shrug*
            pass

        i = 30
        while i >= 0:
            try:
                await message.edit(content=f'{msg} — {i}s left')
            except discord.Forbidden:
                pass

            # update countdown only every 5 seconds at first to avoid being rate limited
            seconds = 5 if i > 5 else 1
            i -= seconds
            await asyncio.sleep(seconds)

        result = self._votes.pop(message.id, 0)
        result_msg = f'Vote passed. {user} kicked by vote ({reason})' if result > 0 else 'Vote failed'

        try:
            await ctx.send(result_msg)
        except discord.Forbidden:
            pass

        self._vote_callers.remove((channel.id, author.id))

        return result

    @commands.command()
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str='No reason given'):
        await self._kick(ctx, user, reason)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def actualkick(self, ctx: commands.Context, user: discord.Member, *, reason: str='No reason given'):
        result = await self._kick(ctx, user, reason)
        if result > 0:
            await user.kick()


def setup(bot: commands.Bot):
    bot.add_cog(Votes(bot))
