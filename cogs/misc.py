#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from io import BytesIO
from typing import Union

import discord
import psutil
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.process = psutil.Process()


    def get_uptime(self) -> str:
        delta = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        return f'{days}d {hours}h {minutes}m {seconds}s'


    @commands.command()
    async def about(self, ctx: commands.Context) -> None:
        desc = f'Discord bot for [DDraceNetwork](https://ddnet.tw/)'
        url = 'https://github.com/12pm/ddnet-discordbot'
        embed = discord.Embed(title='GitHub repository', description=desc, color=0xFEA500, url=url)

        owner = self.bot.get_user(self.bot.owner_id)
        embed.set_author(name=owner, icon_url=owner.avatar_url_as(format='png'))

        channels = sum(len(g.voice_channels + g.text_channels) for g in self.bot.guilds)
        stats = f'{len(self.bot.guilds)} Guilds\n{channels} Channels\n{len(self.bot.users)} Users'
        embed.add_field(name='Stats', value=stats)

        memory = self.process.memory_full_info().uss / 1024**2
        cpu = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory:.2f} MB\n{cpu:.2f}% CPU')

        embed.add_field(name='Uptime', value=self.get_uptime())

        await ctx.send(embed=embed)


    @commands.command()
    async def avatar(self, ctx: commands.Context, *, user: Union[discord.Member, discord.User]=None) -> None:
        await ctx.trigger_typing()

        user = user or ctx.author
        avatar = user.avatar_url_as(static_format='png')
        buf = BytesIO()
        await avatar.save(buf)

        ext = 'gif' if user.is_avatar_animated() else 'png'
        file = discord.File(buf, filename=f'avatar_{user.name}.{ext}')
        await ctx.send(file=file)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Misc(bot))
