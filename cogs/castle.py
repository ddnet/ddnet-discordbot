import discord
from discord.ext import commands

from config import ROLE_TESTER, ROLE_MOD, ROLE_ADMIN, CHAN_CASTLE
from utils.d_utils import is_staff


def has_attachments(message: discord.Message):
    return message.attachments and \
        any(message.attachments[0].filename.endswith(s) for s in
            [".png", ".jpg", ".jpeg", ".gif", ".mp4", ".webm", ".wmv", ".mkv", ".avi", ".mov"])


class Castle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles = (ROLE_ADMIN, ROLE_MOD, ROLE_TESTER)

    @commands.Cog.listener('on_message')
    async def unwanted_message_react(self, message: discord.Message):
        author = message.author
        channel = message.channel
        if channel.id == CHAN_CASTLE:
            if not has_attachments(message) and not is_staff(author, self.roles):
                await message.delete()
            if has_attachments(message):
                await message.add_reaction('⬆️')
                await message.add_reaction('⬇️')


def setup(bot):
    bot.add_cog(Castle(bot))
