#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import discord
from discord.ext import commands

from config import ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_TESTER, ROLE_MOD, ROLE_SKIN_DB_CREW, GUILD_DDNET, CHAN_WIKI, CHAN_DEV, \
    CHAN_MODC, FORUM_CHANNEL
from utils.d_utils import is_staff


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.roles = (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_MOD, ROLE_TESTER, ROLE_SKIN_DB_CREW)

    @commands.Cog.listener('on_message')
    async def spam_link_filter(self, message: discord.Message):
        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id not in (CHAN_DEV, CHAN_WIKI):
            return

        link_pattern = re.compile(r'https?:\/\/(www\.)?t\.me', re.IGNORECASE) # noqa
        if link_pattern.search(message.content):
            await message.delete()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_DDNET or member.bot or not is_staff(member, self.roles):
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
