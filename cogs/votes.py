#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import List, Union

import discord
from discord.ext import commands

VOTE_YES     = '<:f3:397431188941438976>'
VOTE_NO      = '<:f4:397431204552376320>'
VOTE_CANCEL  = '\N{NO ENTRY SIGN}'


class Votes(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._votes = {}


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
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
        elif emoji == VOTE_CANCEL and user.guild_permissions.kick_members:
            del self._votes[message.id]
        else:
            try:
                await reaction.remove(user)
            except discord.HTTPException:
                pass


    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
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
    async def on_reaction_clear(self, message: discord.Message, reactions: List[discord.Reaction]) -> None:
        if message.id not in self._votes:
            return

        self._votes[message.id] = 0


    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 30, type=commands.BucketType.member)
    async def kick(self, ctx: commands.Context, *, user: discord.Member) -> None:
        author = ctx.author

        msg = f'{author.mention} called for vote to kick {user.mention}'
        message = await ctx.send(msg)

        self._votes[message.id] = 0

        try:
            for emoji in (VOTE_YES, VOTE_NO, VOTE_CANCEL):
                await message.add_reaction(emoji.strip('<>'))  # TODO: Remove strip when discord.py 1.1.0 releases
        except discord.HTTPException:
            pass

        i = 30
        while True:
            if message.id not in self._votes:
                # Vote cancled
                i = 0

            if i % 5 == 0 or i % 1 == 0 and i <= 5:
                # Update countdown only every 5 seconds at first to avoid being rate limited
                await message.edit(content=f'{msg}. {int(i)}s left')

            if i == 0:
                break

            i -= 0.5
            await asyncio.sleep(0.5)

        result = self._votes.pop(message.id, 0)
        if result > 0:
            result_msg = 'Vote passed'

            if (author.guild_permissions.kick_members
                and (author == ctx.guild.owner or author.top_role > user.top_role)
                and author != user):
                try:
                    await user.kick(reason='Kicked by vote')
                except discord.HTTPException:
                    # Bot doesn't have kick members permission, a higher role, or the user is owner
                    pass
                else:
                    result_msg += f'. {user.mention} kicked by vote'
        else:
            result_msg = 'Vote failed'

        await ctx.send(result_msg)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Votes(bot))
