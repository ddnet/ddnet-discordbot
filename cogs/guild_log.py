from datetime import datetime
from io import BytesIO

import discord
from discord.ext import commands

from utils.text import escape


VALID_IMAGE_FORMATS = ('.webp', '.jpeg', '.jpg', '.png', '.gif')

class GuildLog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = self.bot.guild


    @property
    def welcome_chan(self):
        return discord.utils.get(self.guild.channels, name='welcome')


    @property
    def join_chan(self):
        return discord.utils.get(self.guild.channels, name='join-leave')


    @property
    def log_chan(self):
        return discord.utils.get(self.guild.channels, name='logs')


    @property
    def eyes_emoji(self):
        return discord.utils.get(self.guild.emojis, name='happy')


    @property
    def dotdot_emoji(self):
        return discord.utils.get(self.guild.emojis, name='mmm')


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild != self.guild or member.bot:
            return

        msg = f'📥 {member.mention}, Welcome to **DDraceNetwork\'s Discord**! ' \
              f'Please make sure to read {self.welcome_chan.mention}. ' \
              f'Have a great time here {self.eyes_emoji}'
        await self.join_chan.send(msg)


    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild != self.guild or member.bot:
            return

        msg = f'📤 **{escape(str(member))}** just left the server {self.dotdot_emoji}'
        await self.join_chan.send(msg)


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.guild != self.guild:
            return

        if message.type is not discord.MessageType.default:
            return

        embed = discord.Embed(title='Message deleted', description=message.content, color=0xDD2E44, timestamp=datetime.utcnow())

        file = None
        if message.attachments:
            attachment = message.attachments[0]

            # Can only properly recover images
            if attachment.filename.endswith(VALID_IMAGE_FORMATS):
                buf = BytesIO()
                try:
                    await attachment.save(buf, use_cached=True)
                except discord.HTTPException:
                    pass
                else:
                    file = discord.File(buf, filename=attachment.filename)
                    embed.set_image(url=f'attachment://{attachment.filename}')

        embed.set_author(name=f'{message.author} → #{message.channel}', icon_url=message.author.avatar_url_as(format='png'))

        await self.log_chan.send(file=file, embed=embed)


def setup(bot):
    bot.add_cog(GuildLog(bot))
