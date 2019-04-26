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
        self.votes = {}


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
        if user == self.bot.user:
            return

        message = reaction.message
        if message.id not in self.votes:
            return

        emoji = str(reaction.emoji)
        if emoji == VOTE_YES:
            self.votes[message.id] += 1
        elif emoji == VOTE_NO:
            self.votes[message.id] -= 1
        elif emoji == VOTE_CANCEL and user.guild_permissions.kick_members:
            del self.votes[message.id]
        else:
            try:
                await reaction.remove(user)
            except discord.HTTPException:
                pass


    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
        if user == self.bot.user:
            return

        message = reaction.message
        if message.id not in self.votes:
            return

        emoji = str(reaction.emoji)
        if emoji == VOTE_YES:
            self.votes[message.id] -= 1
        elif emoji == VOTE_NO:
            self.votes[message.id] += 1


    @commands.Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: List[discord.Reaction]) -> None:
        if message.id not in self.votes:
            return

        self.votes[message.id] = 0


    @commands.command()
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, *, user: discord.Member) -> None:
        author = ctx.author

        msg = f'{author.mention} called for vote to kick {user.mention}'
        message = await ctx.send(msg)

        self.votes[message.id] = 0

        try:
            for emoji in (VOTE_YES, VOTE_NO, VOTE_CANCEL):
                await message.add_reaction(emoji.strip('<>'))  # TODO: Remove strip when discord.py 1.1.0 releases
        except discord.HTTPException:
            pass

        i = 30
        while True:
            if message.id not in self.votes:
                # Vote cancled
                i = 0

            await message.edit(content=f'{msg}. {i}s left')

            if i == 0:
                break

            i -= 1
            await asyncio.sleep(1)

        result = self.votes.pop(message.id, 0)
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
