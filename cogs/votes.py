#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import Optional, Union

import discord
from discord.ext import commands

from config import VOTE_NO_id, VOTE_YES_id

VOTE_YES = f'<:f3:{VOTE_YES_id}>'
VOTE_NO = f'<:f4:{VOTE_NO_id}>'


class Votes(commands.Cog):
    def __init__(self):
        self._votes = {}

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

    async def _kick(self, ctx: commands.Context, user: discord.Member, reason: Optional[str]) -> int:
        reason = reason or 'No reason given'
        msg = f'{ctx.author} called for vote to kick {user} ({reason})'
        message = await ctx.send(msg)

        self._votes[message.id] = 0

        await message.add_reaction(VOTE_YES)
        await message.add_reaction(VOTE_NO)

        i = 30
        while i >= 0:
            await message.edit(content=f'{msg} — {i}s left')

            # update countdown only every 5 seconds at first to avoid being rate limited
            seconds = 5 if i > 5 else 1
            i -= seconds
            await asyncio.sleep(seconds)

        result = self._votes.pop(message.id, 0)
        result_msg = f'Vote passed. {user} kicked by vote ({reason})' if result > 0 else 'Vote failed'
        await ctx.send(result_msg)

        return result

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        await self._kick(ctx, user, reason)

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def actualkick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        result = await self._kick(ctx, user, reason)
        if result > 0:
            await user.kick()

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(f'You can only call {error.number} vote at a time')
        if isinstance(error, commands.BadArgument):
            await ctx.send('Could not find that user')
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send('I can\'t kick members')


async def setup(bot: commands.Bot):
    await bot.add_cog(Votes())
