import discord
from discord.ext import commands

from config import wiki_curators


class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def wikicontributor(self, ctx, member: discord.Member):

        if ctx.author.id not in wiki_curators:
            await ctx.reply("You are not authorized to use this command.")
            return

        wiki_contributor = discord.utils.get(ctx.guild.roles, name='Wiki Contributor')

        if wiki_contributor in member.roles:
            await member.remove_roles(wiki_contributor)
            await ctx.send(f"Removed the Wiki Contributor from user {member.mention}.")
        else:
            await member.add_roles(wiki_contributor)
            await ctx.send(f"{member.mention} has been assigned the Wiki Contributor role.")


async def setup(bot):
    await bot.add_cog(Wiki(bot))
