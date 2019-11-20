#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import enum
import logging
from collections import namedtuple
from datetime import datetime
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from data.countryflags import COUNTRYFLAGS, FLAG_UNK
from utils.text import escape

log = logging.getLogger(__name__)


class Player:
    __slots__ = ('name', 'clan', 'score', 'country', '_playing', 'url')

    def __init__(self, **kwargs):
        self.name = kwargs.pop('name')
        self.clan = kwargs.pop('clan')
        self.score = kwargs.pop('score')
        self.country = kwargs.pop('country')
        self._playing = kwargs.pop('playing')
        self.url = kwargs.pop('url', None)

    def is_playing(self) -> bool:
        return self._playing

    def is_connected(self) -> bool:
        # https://github.com/ddnet/ddnet/blob/38f91d3891eefc392f60f77b1b82ecdb3a47ec62/src/engine/client/serverbrowser.cpp#L348
        return self.name != '(connecting)' or self.clan != '' or self.score != 0 or self.country != -1

    @property
    def flag(self) -> str:
        return COUNTRYFLAGS.get(self.country, FLAG_UNK)

    @property
    def time(self) -> str:
        if self.score == -9999:
            return '--:--'
        else:
            return '{0:02d}:{1:02d}'.format(*divmod(abs(self.score), 60))

    def format(self, time_score: bool=False) -> str:
        if self.url is None:
            line = [f'**{escape(self.name)}**']
        else:
            line = [f'[{escape(self.name)}]({self.url})']

        if self.clan:
            line.append(escape(self.clan))

        if self._playing:
            score = self.time if time_score else self.score
            line = [self.flag, f'`{score}`'] + line

        return ' '.join(line)


Scoreboard = namedtuple('Scoreboard', 'title pages')


class Server:
    __slots__ = ('ip', 'port', 'host', 'name', 'map', 'map_url', 'gametype',
                 'max_players', 'max_clients', '_clients', 'timestamp')

    def __init__(self, **kwargs):
        self.ip = kwargs.pop('ip')
        self.port = kwargs.pop('port')
        self.host = kwargs.pop('host')
        self.name = kwargs.pop('name')
        self.map = kwargs.pop('map')
        self.map_url = kwargs.pop('map_url', None)
        self.gametype = kwargs.pop('gametype')
        self.max_players = kwargs.pop('max_players')
        self.max_clients = kwargs.pop('max_clients')
        self._clients = [Player(**p) for p in kwargs.pop('players')]
        self.timestamp = kwargs.pop('timestamp')

    def __contains__(self, item) -> bool:
        return any(p.name == item and p.is_connected() for p in self._clients)

    @property
    def title(self) -> str:
        return f'{self.name}: {self.map}'

    @property
    def address(self) -> str:
        return f'{self.host}:{self.port}'

    @property
    def color(self) -> Optional[int]:
        # https://github.com/ddnet/ddnet/blob/f1b54d32b909a3c6fc9e1dc6c37475a1d7c21ec4/src/engine/shared/serverbrowser.cpp
        # https://github.com/ddnet/ddnet/blob/f1b54d32b909a3c6fc9e1dc6c37475a1d7c21ec4/src/game/client/components/menus_browser.cpp#L442-L457
        gametype = self.gametype.lower()
        if self.gametype in ('DM', 'TDM', 'CTF'):
            return 0x82FF7F  # Vanilla
        elif 'catch' in gametype:
            return 0xFCFF7F  # Catch
        elif any(t in gametype for t in ('idm', 'itdm', 'ictf')):
            return 0xFF7F7F  # Instagib
        elif 'fng' in gametype:
            return 0xFC7FFF  # FNG
        elif any(t in gametype for t in ('ddracenet', 'ddnet', 'blockz', 'infectionz')):
            return 0x7EBFFD  # DDNet
        elif any(t in gametype for t in ('ddrace', 'mkrace')):
            return 0xBF7FFF  # DDRace
        elif any(t in gametype for t in ('race', 'fastcap')):
            return 0x7FFFE0  # Race

    @property
    def time_score(self) -> bool:
        # https://github.com/ddnet/ddnet/blob/f1b54d32b909a3c6fc9e1dc6c37475a1d7c21ec4/src/game/client/gameclient.cpp#L1008
        gametype = self.gametype.lower()
        return any(t in gametype for t in ('race', 'fastcap', 'ddnet', 'blockz', 'infectionz'))

    @property
    def players(self) -> List[Player]:
        return [p for p in self._clients if p.is_playing() and p.is_connected()]

    @property
    def spectators(self) -> List[Player]:
        return [p for p in self._clients if not p.is_playing() and p.is_connected()]

    @property
    def scoreboard(self) -> Scoreboard:
        title = f'Players [{len(self.players)}/{self.max_players}]'

        # https://github.com/ddnet/ddnet/blob/38f91d3891eefc392f60f77b1b82ecdb3a47ec62/src/game/client/gameclient.cpp#L1381-L1406
        players = sorted(self.players, key=lambda p: (self.time_score and p.score == -9999, -p.score, p.name.lower()))
        pages = [
            (
                '\n'.join(p.format(self.time_score) for p in players[i:i+8]),
                '\n'.join(p.format(self.time_score) for p in players[i+8:i+16])
            )
            for i in range(0, len(players), 16)
        ]

        return Scoreboard(title=title, pages=pages)

    @property
    def specboard(self) -> Scoreboard:
        title = f'Spectators [{len(self.spectators)}/{self.max_clients}]'

        spectators = sorted(self.spectators, key=lambda p: p.name.lower())
        page = ', '.join(p.format() for p in spectators)

        return Scoreboard(title=title, pages=[page])


class ServerPaginator:
    def __init__(self, ctx: commands.Context, server: Server):
        self.ctx = ctx
        self.bot = ctx.bot
        self.server = server
        self.message = None
        self.current_page = 0
        self.num_pages = len(server.scoreboard.pages)

        self.paginating = self.num_pages > 1
        self.emojis = {
            '\N{BLACK LEFT-POINTING TRIANGLE}': self.prev_page,
            '\N{BLACK RIGHT-POINTING TRIANGLE}': self.next_page
        }

    def gen_embed(self, server: Server, page: int) -> discord.Embed:
        embed = discord.Embed(title=server.title, url=server.map_url, color=server.color, timestamp=server.timestamp)

        if server.players:
            embed.add_field(name=server.scoreboard.title, value=server.scoreboard.pages[page][0])
            if server.scoreboard.pages[page][1]:
                embed.add_field(name='\u200b', value=server.scoreboard.pages[page][1])

        if server.spectators:
            embed.add_field(name=server.specboard.title, value=server.specboard.pages[0], inline=False)

        embed.set_footer(text=f'{server.address} (Page {page + 1}/{self.num_pages})')

        return embed

    async def show_page(self, page: int):
        embed = self.gen_embed(self.server, page)
        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
            if self.paginating:
                for emoji in self.emojis:
                    await self.message.add_reaction(emoji)
        else:
            await self.message.edit(embed=embed)

        self.current_page = page

    async def start_paginating(self):
        await self.show_page(0)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if user is None or user != self.ctx.author:
                return False

            if reaction.message.id != self.message.id:
                return False

            emoji = str(reaction)
            if emoji in self.emojis:
                self.match = self.emojis[emoji]
                return True

            return False

        while self.paginating:
            # TODO: break on message deleted
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=120.0)
            except asyncio.TimeoutError:
                try:
                    await self.message.clear_reactions()
                except discord.Forbidden:
                    pass
                finally:
                    break

            try:
                await reaction.remove(user)
            except (discord.Forbidden, discord.NotFound):
                pass

            await self.match()

    async def prev_page(self):
        page = self.current_page - 1
        if page == -1:
            page = self.num_pages - 1

        await self.show_page(page)

    async def next_page(self):
        page = self.current_page + 1
        if page == self.num_pages:
            page = 0

        await self.show_page(page)


class ServerInfo:
    __slots__ = ('host', '_online', 'packets')

    PPS_THRESHOLD = 3000  # we usually get max 2 kpps legit traffic so this should be a safe threshold

    COUNTRYFLAGS = {
        'GER': '🇩🇪',
        'RUS': '🇷🇺',
        'CHL': '🇨🇱',
        'USA': '🇺🇸',
        'BRA': '🇧🇷',
        'ZAF': '🇿🇦',
        'CHN': '🇨🇳',
    }

    class Status(enum.Enum):
        UP          = 'up'
        ATTACKED    = 'ddos'  # not necessarily correct but easy to understand
        DOWN        = 'down'

        def __str__(self) -> str:
            return self.value

    def __init__(self, **kwargs):
        self.host = kwargs.pop('type')
        self._online = kwargs.pop('online4')

        self.packets = (kwargs.pop('packets_rx'), kwargs.pop('packets_tx')) if self._online else None

    def is_online(self) -> bool:
        return self._online

    def is_under_attack(self) -> bool:
        return self.packets is not None and self.packets[0] > self.PPS_THRESHOLD

    @property
    def status(self) -> Status:  # noqa: F821
        if not self.is_online():
            return self.Status.DOWN
        elif self.is_under_attack():
            return self.Status.ATTACKED
        else:
            return self.Status.UP

    @property
    def country(self) -> str:
        # monkey patch BRA so that country abbreviations are consistent
        return self.host.split('.')[0].upper().replace('BR', 'BRA')

    @property
    def flag(self) -> str:
        return self.COUNTRYFLAGS.get(self.country, FLAG_UNK)

    def format(self) -> str:
        def humanize_pps(pps: int) -> str:
            return f'{pps} pps' if pps < 1000 else f'{round(pps / 1000, 2)} kpps'

        if self.packets is None:
            packets = ('', '')
        else:
            packets = (humanize_pps(self.packets[0]), humanize_pps(self.packets[1]))

        return f'{self.flag} `{self.country} | {self.status:^4} | ▲ {packets[0]:>10} | ▼ {packets[1]:>10}`'


class ServerStatus:
    __slots__ = ('servers', 'timestamp')

    URL = 'https://ddnet.tw/status/'

    def __init__(self, servers: List[Dict], updated: str):
        # drop ddnet.tw, we only care about game servers
        self.servers = [ServerInfo(**s) for s in servers if s['name'] != 'DDNet.tw']
        self.timestamp = datetime.utcfromtimestamp(float(updated))

    @property
    def embed(self) -> discord.Embed:
        desc = '\n'.join(s.format() for s in self.servers)
        return discord.Embed(title='Server Status', description=desc, url=self.URL, timestamp=self.timestamp)


class Teeworlds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def fetch_status(self) -> List[Server]:
        url = 'https://ddnet.tw/status/index.json'
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                log.error('Failed to fetch DDNet status data (status code: %d %s)', resp.status, resp.reason)
                raise RuntimeError('Could not fetch DDNet status')

            # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Last-Modified
            timestamp = datetime.strptime(resp.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S GMT')
            js = await resp.json()

            return [Server(**s, timestamp=timestamp) for s in js]

    @commands.command()
    async def find(self, ctx: commands.Context, *, player: str=None):
        """Find a player on a DDNet server"""
        player = player or ctx.author.display_name
        for user in ctx.message.mentions:
            player = player.replace(user.mention, user.display_name)

        try:
            servers = await self.fetch_status()
        except RuntimeError as exc:
            return await ctx.send(exc)

        servers = [s for s in servers if player in s]
        if not servers:
            return await ctx.send('Could not find that player')

        server = max(servers, key=lambda s: len(s.players) + len(s.spectators))

        paginator = ServerPaginator(ctx, server)
        await paginator.start_paginating()

    async def fetch_stats(self) -> ServerStatus:
        url = 'https://ddnet.tw/status/json/stats.json'
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                log.error('Failed to fetch DDNet server stats (status code: %d %s)', resp.status, resp.reason)
                raise RuntimeError('Could not fetch DDNet stats')

            js = await resp.json()

            return ServerStatus(**js)

    @commands.command()
    async def ddos(self, ctx: commands.Context):
        """Display DDNet server status"""
        try:
            status = await self.fetch_stats()
        except RuntimeError as exc:
            await ctx.send(exc)
        else:
            await ctx.send(embed=status.embed)


def setup(bot: commands.Bot):
    bot.add_cog(Teeworlds(bot))
