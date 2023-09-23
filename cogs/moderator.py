#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import discord
from discord.ext import commands


GUILD_DDNET      = 252358080522747904
CHAN_DEV         = 293493549758939136
CHAN_WIKI        = 871738312849752104
FORUM_CHANNEL    = 1147027590356414565


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
    async def on_thread_create(self, thread):
        if thread.parent_id == FORUM_CHANNEL:
            # thread.starting_message doesn't work, so I just simply use history instead
            async for msg in thread.history(limit=1, oldest_first=True):
                await msg.pin()

            await thread.send('Make sure to read <#1147040594288443512> and adjust your application accordingly.')

async def setup(bot: commands.bot):
    await bot.add_cog(Moderator(bot))
