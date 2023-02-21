#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import requests
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands

from utils.text import clean_content, escape_backticks

log = logging.getLogger(__name__)

GUILD_DDNET     = 
CHAN_REPORTS    = 
CHAN_MODERATOR  = 
CHAN_BOTTERS    = 
CHAN_DEV        = 
CHAN_WIKI       = 
ROLE_ADMIN      = 
ROLE_MODERATOR  = 
ROLE_MUTED      = 

def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_MODERATOR) for r in member.roles)


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._warned_users = set()

    @commands.Cog.listener('on_message')
    async def pingoutsidereports(self, message: discord.Message):
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
    async def linkfilter(self, message: discord.Message):

        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id not in (CHAN_DEV, CHAN_WIKI):
            return

        linkpattern = re.compile(r'https?:\/\/(www\.)?t\.me', re.IGNORECASE)
        if linkpattern.search(message.content):
            await message.delete()

    @commands.Cog.listener('on_message')
    async def serverlink(self, message: discord.Message):
        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id != CHAN_REPORTS \
                or message.author.bot:
            return

        url = "https://info2.ddnet.tw/info"
        jsonData = requests.get(url).json()
        def extract_servers(jsonData, tags, network):
            if network == "ddnet":
                data = jsonData.get('servers')
            elif network == "kog":
                data = jsonData.get('servers-kog')
            servers = []
            for i in data:
                list = i.get('servers')
                for tag in tags:
                    server_lists = list.get(tag)
                    if server_lists is not None:
                        servers += server_lists
            return servers

        DDNetddr = extract_servers(jsonData, ['DDNet', 'Test', 'Tutorial'], "ddnet")
        DDNetPVP = extract_servers(jsonData, ['Block', 'Infection', 'iCTF', 'gCTF', 'Vanilla', 'zCatch', 'TeeWare', 'TeeSmash', 'Foot', 'xPanic', 'Monster'], "ddnet")
        nobyFNG = extract_servers(jsonData, ['FNG'], "ddnet")
        KoG = extract_servers(jsonData, ['Gores', 'TestGores'], "kog")

        ipaddr = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,4}')
        try:
            re_match = ipaddr.findall(message.content)[0]
        except IndexError:
            return
        
        if re_match in DDNetddr:
            message_text = f'`{re_match}` is an official DDNet server. Non-Steam: <ddnet://{re_match}/> Steam: steam://run/412220//{re_match}/'
        elif re_match in DDNetPVP:
            message_text = f'`{re_match}` is an official DDNet PvP server. Non-Steam: <ddnet://{re_match}/> Steam: steam://run/412220//{re_match}/'
        elif re_match in KoG:
            message_text = f'`{re_match}` appears to be a KoG server. DDNet and KoG aren\'t affiliated. Join their discord and ask for help there instead. https://discord.gg/3G5SJY49nY'
        elif re_match in nobyFNG:
            message_text = f'`{re_match}` appears to be a FNG server found within the DDNet tab. These servers are classified as official but are not regulated by us. For support, join this https://discord.gg/utB4Rs3 discord server instead.'
        else:
            message_text = f'`{re_match}` is an unknown server address and not affiliated with DDNet/KoG.'

        await message.channel.send(message_text)


def setup(bot: commands.bot):
    bot.add_cog(Moderator(bot))
