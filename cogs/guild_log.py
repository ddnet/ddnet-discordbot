#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from io import BytesIO
from typing import List

import discord
from discord.ext import commands

from utils.text import escape, truncate

VALID_IMAGE_FORMATS = ('.webp', '.jpeg', '.jpg', '.png', '.gif')


class GuildLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = self.bot.guild

    @property
    def welcome_chan(self) -> discord.TextChannel:
        return discord.utils.get(self.guild.text_channels, name='welcome')

    @property
    def join_chan(self) -> discord.TextChannel:
        return discord.utils.get(self.guild.text_channels, name='join-leave')

    @property
    def log_chan(self) -> discord.TextChannel:
        return discord.utils.get(self.guild.text_channels, name='logs')

    @property
    def eyes_emoji(self) -> discord.Emoji:
        return discord.utils.get(self.guild.emojis, name='happy')

    @property
    def dotdot_emoji(self) -> discord.Emoji:
        return discord.utils.get(self.guild.emojis, name='mmm')

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild != self.guild or member.bot:
            return

        msg = f'📥 {member.mention}, Welcome to **DDraceNetwork\'s Discord**! ' \
              f'Please make sure to read {self.welcome_chan.mention}. ' \
              f'Have a great time here {self.eyes_emoji}'
        await self.join_chan.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild != self.guild or member.bot:
            return

        msg = f'📤 **{escape(str(member))}** just left the server {self.dotdot_emoji}'
        await self.join_chan.send(msg)

    async def log_message(self, message: discord.Message):
        author = message.author

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

        embed.set_author(name=f'{author} → #{message.channel}', icon_url=author.avatar_url_as(format='png'))
        embed.set_footer(text=f'Author ID: {author.id} | Message ID: {message.id}')

        await self.log_chan.send(file=file, embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self.log_message(message)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        # sort by timestamp to make sure messages are logged in correct order
        messages = sorted(messages, key=lambda m: m.created_at)
        for message in messages:
            await self.log_message(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        author = before.author

        if not after.guild or before.guild != self.guild:
            return

        if before.type is not discord.MessageType.default:
            return

        if before.content == after.content:
            return

        desc = f'[Jump to message]({before.jump_url})'
        embed = discord.Embed(title='Message edited', description=desc, color=0xF5B942, timestamp=datetime.utcnow())
        embed.add_field(name='Before', value=truncate(before.content, length=1024), inline=False)
        embed.add_field(name='After', value=truncate(after.content, length=1024), inline=False)
        embed.set_author(name=f'{author} → #{before.channel}', icon_url=author.avatar_url_as(format='png'))
        embed.set_footer(text=f'Author ID: {author.id} | Message ID: {before.id}')

        await self.log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        embed = discord.Embed(title='Joined guild')
        embed.add_field(name='Name', value=guild.name)
        embed.add_field(name='ID', value=guild.id)


        msg = f'📥 Joined guild **{escape(guild.name)}** ({guild.id}) with {(guild.member_count)} members'
        await self.log_chan.send(msg)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        msg = f'📤 Left guild **{escape(guild.name)}** ({guild.id}) with {guild.member_count} members'
        await self.log_chan.send(msg)


def setup(bot: commands.Bot):
    bot.add_cog(GuildLog(bot))
