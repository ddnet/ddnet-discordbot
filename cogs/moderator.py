#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands

from utils.text import clean_content, escape_backticks

log = logging.getLogger(__name__)

GUILD_DDNET     = 252358080522747904
CHAN_REPORTS    = 779761780129005568
CHAN_MODERATOR  = 345588928482508801
ROLE_ADMIN      = 293495272892399616
ROLE_MODERATOR  = 252523225810993153
ROLE_MUTED      = 768872500263911495

Ban = namedtuple('Ban', 'ip expires name reason mod region')

def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_MODERATOR) for r in member.roles)


class Moderator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._current_ban = None
        self._active_ban = asyncio.Event()
        self._task = bot.loop.create_task(self.dispatch_unbans())
        self._warned_users = set()

    def cog_unload(self):
        self._task.cancel()

    def restart_dispatch(self):
        self._task.cancel()
        self._task = self.bot.loop.create_task(self.dispatch_unbans())

    async def ddnet_request(self, method: str, ip: str, name: Optional[str]=None, reason: Optional[str]=None, region: Optional[str]=None):
        url = self.bot.config.get('DDNET', 'BAN')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET', 'BAN-TOKEN')}

        params = {'ip': ip}
        if name is not None:
            params['name'] = name
        if reason is not None:
            params['reason'] = reason
        if region is not None:
            params['region'] = region

        async with self.bot.session.request(method, url, params=params, headers=headers) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                fmt = 'Failed %s request for %r on ddnet.tw: %s (status code: %d %s)'
                log.error(fmt, method, ip, text, resp.status, resp.reason)
                raise RuntimeError(text)

    async def ddnet_ban(self, ip: str, name: str, expires: datetime, reason: str, mod: str, region: Optional[str]=None):
        await self.ddnet_request('POST', ip, name, reason, region)

        query = """INSERT INTO ddnet_bans (ip, expires, name, reason, mod, region) VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (ip) DO UPDATE SET expires = $2, name = $3, reason = $4, mod = $5, region = $6;"""
        await self.bot.pool.execute(query, ip, expires, name, reason, mod, region)

        self._active_ban.set()
        if self._current_ban is not None and expires < self._current_ban.expires:
            self.restart_dispatch()

    async def ddnet_unban(self, ip: str):
        await self.ddnet_request('DELETE', ip)

        query = 'DELETE FROM ddnet_bans WHERE ip = $1;'
        await self.bot.pool.execute(query, ip)

        if self._current_ban is not None and self._current_ban.ip == ip:
            self.restart_dispatch()

    async def get_active_ban(self) -> Ban:
        query = 'SELECT * FROM ddnet_bans ORDER BY expires LIMIT 1;'
        record = await self.bot.pool.fetchrow(query)
        if record is None:
            self._active_ban.clear()
            self._current_ban = None
            await self._active_ban.wait()
            return await self.get_active_ban()
        else:
            return Ban(**record)

    async def dispatch_unbans(self):
        while not self.bot.is_closed():
            ban = self._current_ban = await self.get_active_ban()
            now = datetime.utcnow()

            if ban.expires > now:
                to_sleep = (ban.expires - now).total_seconds()
                await asyncio.sleep(to_sleep)

            await self.ddnet_unban(ban.ip)

    async def _global_ban(self, ctx: commands.Context, ip: str, name: str, minutes: int, reason: str, region: Optional[str]=None):
        if minutes < 1:
            return await ctx.send('Minutes need to be greater than 0')

        if region is not None and len(region) != 3:
            return await ctx.send('Invalid region')

        expires = datetime.utcnow() + timedelta(minutes=min(minutes, 60 * 24 * 30))

        try:
            await self.ddnet_ban(ip, name, expires, reason, str(ctx.author), region)
        except RuntimeError as exc:
            await ctx.send(exc)
        else:
            await ctx.send(f'Successfully banned `{ip}` until {expires:%d/%m/%Y %H:%M} UTC')

    def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.channel.id == CHAN_MODERATOR and is_staff(ctx.author)

    @commands.command()
    async def global_ban(self, ctx: commands.Context, ip: str, name: str, minutes: int, *, reason: clean_content):
        """Ban an ip from all DDNet servers.
           Minutes need to be greater than 0.
        """
        await self._global_ban(ctx, ip, name, minutes, reason)

    @commands.command()
    async def global_ban_region(self, ctx: commands.Context, region: str, ip: str, name: str, minutes: int, *, reason: clean_content):
        """Ban an ip from all DDNet servers in given region.
           Minutes need to be greater than 0. Region needs to be the 3 char server code.
        """
        await self._global_ban(ctx, ip, name, minutes, reason, region)

    @global_ban.error
    @global_ban_region.error
    async def global_ban_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Minutes need to be greater than 0')

    @commands.command(usage='<ip|name>')
    async def global_unban(self, ctx: commands.Context, *, name: str):
        """Unban an ip from all DDNet servers. If you pass a name, all currently globally banned ips associated with that name will be unbanned."""
        if re.match(r'^[\d\.-]*$', name) is None:
            query = 'SELECT ip FROM ddnet_bans WHERE name = $1;'
            ips = [r['ip'] for r in await self.bot.pool.fetch(query, name)]
            if not ips:
                return await ctx.send(f'`{escape_backticks(name)}` isn\'t banned')
        else:
            ips = [name]

        for ip in ips:
            try:
                await self.ddnet_unban(ip)
            except RuntimeError as exc:
                await ctx.send(exc)
            else:
                await ctx.send(f'Successfully unbanned `{ip}`')

    @commands.command()
    async def global_bans(self, ctx: commands.Context):
        """Show all currently globally banned ips"""
        admin_cog = self.bot.get_cog('Admin')
        query = """SELECT ip, name, to_char(expires, \'YYYY-MM-DD HH24:MI\') AS expires, reason, mod, region
                   FROM ddnet_bans ORDER BY expires;
                """
        await admin_cog.sql(ctx, query=query)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        message = reaction.message
        if message.guild is None or message.guild.id != GUILD_DDNET:
            return

        if f'<@&{ROLE_MODERATOR}>' in message.content and not is_staff(user):
            await reaction.remove(user)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        author = message.author
        if message.guild is None or message.channel.id == CHAN_REPORTS or is_staff(author) or f'<@&{ROLE_MODERATOR}>' not in message.content:
            return

        await message.delete()

        if author not in self._warned_users:
            msg = f'Don\'t ping Moderators outside of <#{CHAN_REPORTS}>. If you do it again, you will be muted.'
            try:
                await author.send(msg)
            except discord.Forbidden:
                pass

            self._warned_users.add(author)
        else:
            muted_role = message.guild.get_role(ROLE_MUTED)
            await author.add_roles(muted_role)
            await asyncio.sleep(60 * 60)
            await author.remove_roles(muted_role)


def setup(bot: commands.bot):
    bot.add_cog(Moderator(bot))
