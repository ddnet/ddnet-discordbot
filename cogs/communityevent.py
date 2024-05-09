import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

from config import ROLE_ADMIN, ROLE_TESTER, CHAN_COM_SUBMIT_MAPS
from utils.discord_utils import is_staff


def has_attachments(message: discord.Message):
    return message.attachments and \
        any(message.attachments[0].filename.endswith(s) for s in [".map", ".png", ".jpg", ".jpeg"])


class MapEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_id = 0
        self.roles = [ROLE_ADMIN, ROLE_TESTER]

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
        self.msg_id = msg.id
        await msg.add_reaction('🌸')
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.msg_id == payload.message_id:
            member = payload.member
            guild = member.guild
            emoji = payload.emoji.name
            if emoji != '🌸':
                return
            role = discord.utils.get(guild.roles, name="CM-Mapper")
            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if self.msg_id == payload.message_id:
            guild = await self.bot.fetch_guild(payload.guild_id)
            emoji = payload.emoji.name
            if emoji != '🌸':
                return
            role = discord.utils.get(guild.roles, name="Experienced")
            member = await guild.fetch_member(payload.user_id)
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
