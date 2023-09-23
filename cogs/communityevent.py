import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

import re

CHAN_COM_SUBMIT_MAPS    = 929368485417594950
ROLE_ADMIN              = 293495272892399616
ROLE_TESTER             = 293543421426008064


def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_TESTER) for r in member.roles)


def has_attachments(message: discord.Message):
    return message.attachments and \
           any(message.attachments[0].filename.endswith(s) for s in [".map", ".png", ".jpg", ".jpeg"])

class MapEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @has_permissions(manage_roles=True)
    async def eventmsg(self, ctx):
        embed = discord.Embed(
            title="Community Map 2022 Registration",
            description="Very Long Event Description, hurray.",
            color=0x3498db)
        embed.add_field(
            name="Rule Set",
            value="Rule 1. Rule 2. Rule 3. Rule 4.",
            inline=True)
        embed.add_field(
            name="Dates",
            value="<date> info1, <date> info2, <date> info3",
            inline=False)
        embed.add_field(
            name="Mappers",
            value="Click the 🌸 emote if you'd like to participate",
            inline=True)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('🌸')
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        messageid = 933374481542545428
        if messageid == payload.message_id:
            member = payload.member
            guild = member.guild
            emoji = payload.emoji.name
            if emoji == '🌸':
                role = discord.utils.get(guild.roles, name="CM-Mapper")
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        messageid = 933374481542545428
        if messageid == payload.message_id:
            guild = await(self.bot.fetch_guild(payload.guild_id))
            emoji = payload.emoji.name
            if emoji == '🌸':
                role = discord.utils.get(guild.roles, name="Experienced")
            member = await(guild.fetch_member(payload.user_id))
            if member is not None:
                await member.remove_roles(role)

    @commands.Cog.listener('on_message')
    async def handle_unwanted_message(self, message: discord.Message):
        author = message.author
        channel = message.channel
        if channel.id == CHAN_COM_SUBMIT_MAPS and not has_attachments(message) and not is_staff(author):
            if message.author.bot:
                return
            if message.content.startswith('Mapper:'):
                return
            await message.delete()


def setup(bot):
    bot.add_cog(MapEvent(bot))
