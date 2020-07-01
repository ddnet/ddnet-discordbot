#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional

from discord.ext import commands

log = logging.getLogger(__name__)

CHAN_MODERATOR  = 345588928482508801
ROLE_ADMIN      = 293495272892399616
ROLE_MODERATOR  = 252523225810993153

def is_moderator(ctx: commands.Context) -> bool:
    return ctx.channel.id == CHAN_MODERATOR and any(r.id in (ROLE_ADMIN, ROLE_MODERATOR) for r in ctx.author.roles)

Ban = namedtuple('Ban', 'ip expires')


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._current_ban = None
        self._active_ban = asyncio.Event()
        self._task = bot.loop.create_task(self.dispatch_unbans())

    def cog_unload(self):
        self._task.cancel()

    async def ddnet_request(self, method: str, ip: str, name: Optional[str]=None, reason: Optional[str]=None):
        url = self.bot.config.get('DDNET', 'BAN')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET', 'BAN-TOKEN')}

        params = {'ip': ip}
        if name is not None:
            params['name'] = name
        if reason is not None:
            params['reason'] = reason

        async with self.bot.session.request(method, url, params=params, headers=headers) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                fmt = 'Failed %s request for %r on ddnet.tw: %s (status code: %d %s)'
                log.error(fmt, method, ip, text, resp.status, resp.reason)
                raise RuntimeError(text)

    async def ddnet_ban(self, ip: str, name: str, minutes: int, reason: str):
        expires = datetime.utcnow() + timedelta(minutes=minutes)

        await self.ddnet_request('POST', ip, name, reason)

        query = """INSERT INTO ddnet_bans (ip, expires) VALUES ($1, $2)
                   ON CONFLICT (ip) DO UPDATE SET expires = $2;"""
        await self.bot.pool.execute(query, ip, expires)

        self._active_ban.set()
        if self._current_ban and expires < self._current_ban.expires:
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def ddnet_unban(self, ip: str):
        await self.ddnet_request('DELETE', ip)

        query = 'DELETE FROM ddnet_bans WHERE ip = $1;'
        await self.bot.pool.execute(query, ip)

    async def get_active_ban(self) -> Ban:
        query = 'SELECT * FROM ddnet_bans ORDER BY expires LIMIT 1;'
        record = await self.bot.pool.fetchrow(query)
        if record is None:
            self._active_ban.clear()
            self._current_ban = None
            await self._active_ban.wait()
            return await self.get_active_ban()
        else:
            self._active_ban.set()
            return Ban(**record)

    async def dispatch_unbans(self):
        while not self.bot.is_closed():
            ban = self._current_ban = await self.get_active_ban()
            now = datetime.utcnow()

            if ban.expires > now:
                to_sleep = (ban.expires - now).total_seconds()
                await asyncio.sleep(to_sleep)

            await self.ddnet_unban(ban.ip)

    @commands.command()
    @commands.check(is_moderator)
    async def global_ban(self, ctx: commands.Context, ip: str, name: str, minutes: int, *, reason: str):
        if minutes < 1:
            return await ctx.send('Minutes need to be greater than 0')

        try:
            await self.ddnet_ban(ip, name, minutes, reason)
        except RuntimeError as exc:
            await ctx.send(exc)
        else:
            await ctx.send(f'Successfully banned `{ip}`')

    @commands.command()
    @commands.check(is_moderator)
    async def global_unban(self, ctx: commands.Context, ip: str):
        try:
            await self.ddnet_unban(ip)
        except RuntimeError as exc:
            await ctx.send(exc)
        else:
            await ctx.send(f'Successfully unbanned `{ip}`')


def setup(bot: commands.bot):
    bot.add_cog(Moderator(bot))
