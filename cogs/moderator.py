#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

GUILD_DDNET     = 252358080522747904
CHAN_REPORTS    = 779761780129005568
CHAN_DEV        = 293493549758939136
CHAN_WIKI       = 871738312849752104
ROLE_ADMIN      = 293495272892399616
ROLE_MODERATOR  = 252523225810993153
ROLE_MUTED      = 987001532581052446


def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_MODERATOR) for r in member.roles)


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._warned_users = set()
        self.servers_url = "https://master1.ddnet.tw/ddnet/15/servers.json"

    @commands.Cog.listener('on_message')
    async def mentions_outside_reports(self, message: discord.Message):
        author = message.author
        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id == CHAN_REPORTS \
           or message.author.bot or is_staff(author) or f'<@&{ROLE_MODERATOR}>' not in message.content:
            return

        await message.delete()

        if author not in self._warned_users:
            warning = f'Don\'t ping Moderators outside of <#{CHAN_REPORTS}>. If you do it again, you will be muted.'
            try:
                await author.send(warning)
            except discord.Forbidden:
                pass

            self._warned_users.add(author)
        else:
            muted_role = message.guild.get_role(ROLE_MUTED)
            await author.add_roles(muted_role)
            await asyncio.sleep(60 * 60)
            await author.remove_roles(muted_role)

    @commands.Cog.listener('on_message')
    async def link_filter(self, message: discord.Message):

        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id not in (CHAN_DEV, CHAN_WIKI):
            return

        link_pattern = re.compile(r'https?:\/\/(www\.)?t\.me', re.IGNORECASE)
        if link_pattern.search(message.content):
            await message.delete()


def setup(bot: commands.bot):
    bot.add_cog(Moderator(bot))
