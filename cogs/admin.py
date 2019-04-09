import traceback

import discord
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)


    @commands.command()
    async def load(self, ctx, *, extension):
        try:
            self.bot.load_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


    @commands.command()
    async def unload(self, ctx, *, extension):
        try:
            self.bot.unload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


    @commands.command()
    async def reload(self, ctx, *, extension):
        try:
            self.bot.reload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction('👌')


def setup(bot):
    bot.add_cog(Admin(bot))
