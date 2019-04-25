#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import BytesIO
from typing import Union

import discord
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


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


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))
