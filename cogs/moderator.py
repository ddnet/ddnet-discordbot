#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import requests

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

    @commands.Cog.listener('on_message')
    async def server_link(self, message: discord.Message):
        if message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id != CHAN_REPORTS \
                or message.author.bot:
            return

        jsondata = requests.get("https://info2.ddnet.tw/info").json()

        def extract_servers(json, tags, network):
            server_list = None
            if network == "ddnet":
                server_list = json.get('servers')
            elif network == "kog":
                server_list = json.get('servers-kog')

            all_servers = []
            for address in server_list:
                server = address.get('servers')
                for tag in tags:
                    server_lists = server.get(tag)
                    if server_lists is not None:
                        all_servers += server_lists
            return all_servers

        ddnet = extract_servers(jsondata, ['DDNet', 'Test', 'Tutorial'], "ddnet")
        ddnetpvp = extract_servers(jsondata, ['Block', 'Infection', 'iCTF', 'gCTF', 'Vanilla', 'zCatch',
                                              'TeeWare', 'TeeSmash', 'Foot', 'xPanic', 'Monster'], "ddnet")
        nobyfng = extract_servers(jsondata, ['FNG'], "ddnet")
        kog = extract_servers(jsondata, ['Gores', 'TestGores'], "kog")

        ipaddr = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,4}')
        try:
            re_match = ipaddr.findall(message.content)[0]
        except IndexError:
            return

        if re_match in ddnet:
            message_text = f'`{re_match}` is an official DDNet server. ' \
                           f'Non-Steam: <ddnet://{re_match}/> Steam: steam://run/412220//{re_match}/'
        elif re_match in ddnetpvp:
            message_text = f'`{re_match}` is an official DDNet PvP server. ' \
                           f'Non-Steam: <ddnet://{re_match}/> Steam: steam://run/412220//{re_match}/'
        elif re_match in kog:
            message_text = f'`{re_match}` appears to be a KoG server. DDNet and KoG aren\'t affiliated. ' \
                           f'Join their discord and ask for help there instead. https://discord.gg/3G5SJY49nY'
        elif re_match in nobyfng:
            message_text = f'`{re_match}` appears to be a FNG server found within the DDNet tab. ' \
                           f'These servers are classified as official but are not regulated by us. ' \
                           f'For support, join this https://discord.gg/utB4Rs3 discord server instead.'
        else:
            message_text = f'`{re_match}` is an unknown server address and not affiliated with DDNet or KoG.'

        await message.channel.send(message_text)


def setup(bot: commands.bot):
    bot.add_cog(Moderator(bot))
