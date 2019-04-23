from typing import Union

import discord
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot: Union[commands.Bot, commands.AutoShardedBot]) -> None:
        self.bot = bot


    @commands.command
    async def avatar(self, ctx: commands.Context, *, user: discord.User=None) -> None:
        await ctx.trigger_typing()

        user = user or ctx.author
        url = user.avatar_url_as(static_format='png')
        async with self.bot.session.get(url) as r:
            avatar = await r.read()

        file = discord.File(avatar, filename=f'avatar_{user.name}.png')
        await ctx.send(file=file)


def setup(bot):
    bot.add_cog(Misc(bot))
