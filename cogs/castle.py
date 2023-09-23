import discord
from discord.ext import commands
from discord.ext.commands import has_permissions

GUILD_DDNET     = 252358080522747904
CHAN_CASTLE    =  959174798955642931
ROLE_ADMIN      = 293495272892399616
ROLE_MODERATOR  = 252523225810993153
ROLE_TESTER     = 293543421426008064

def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_MODERATOR, ROLE_TESTER) for r in member.roles)


def has_attachments(message: discord.Message):
    return message.attachments and \
           any(message.attachments[0].filename.endswith(s) for s in [".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".wmv", ".mkv", ".avi", ".mov"])

class Castle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener('on_message')
    async def unwanted_message_react(self, message: discord.Message):
        author = message.author
        channel = message.channel
        if channel.id == CHAN_CASTLE:
            if not has_attachments(message) and not is_staff(author):
                await message.delete()
            if has_attachments(message):
                await message.add_reaction('⬆️')
                await message.add_reaction('⬇️')

def setup(bot):
    bot.add_cog(Castle(bot))
