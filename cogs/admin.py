import traceback
from typing import Union

import discord
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot: Union[commands.Bot, commands.AutoShardedBot]) -> None:
        self.bot = bot


    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)


    @commands.command()
    async def load(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.load_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


    @commands.command()
    async def unload(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.unload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


    @commands.command()
    async def reload(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.reload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


def setup(bot: Union[commands.Bot, commands.AutoShardedBot]) -> None:
    bot.add_cog(Admin(bot))
