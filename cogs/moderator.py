#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import discord
from discord.ext import commands

GUILD_DDNET      = 252358080522747904
ROLE_ADMIN       = 293495272892399616
ROLE_DISCORD_MOD = 737776812234506270
ROLE_MOD         = 252523225810993153
ROLE_TESTER      = 293543421426008064
ROLE_DB_CREW     = 390516461741015040
CHAN_DEV         = 293493549758939136
CHAN_WIKI        = 871738312849752104
CHAN_MODC        = 534520700548022272
FORUM_CHANNEL    = 1019730229838758028


def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_MOD, ROLE_TESTER, ROLE_DB_CREW) for r in member.roles)


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener('on_message')
    async def spam_link_filter(self, message: discord.Message):
        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id not in (CHAN_DEV, CHAN_WIKI):
            return

        link_pattern = re.compile(r'https?:\/\/(www\.)?t\.me', re.IGNORECASE) # noqa
        if link_pattern.search(message.content):
            await message.delete()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_DDNET or member.bot or not is_staff(member):
            return

        channel = self.bot.get_channel(CHAN_MODC)
        await channel.send(f'A staff member named {member.name} ({member.display_name}) has left the server.')

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent_id == FORUM_CHANNEL:
            # thread.starting_message doesn't work, so I just simply use history instead
            async for msg in thread.history(limit=1, oldest_first=True):
                await msg.pin()

            await thread.send('Make sure to read <#1147040594288443512> and adjust your application accordingly.')


async def setup(bot: commands.bot):
    await bot.add_cog(Moderator(bot))
