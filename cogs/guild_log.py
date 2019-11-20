#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import difflib
import itertools
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import discord
from discord.ext import commands

from utils.text import escape

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
        if not message.guild or message.guild != self.guild:
            return

        if message.type is not discord.MessageType.default: # TODO d.py 1.3: if message.is_system()
            return

        embed = discord.Embed(title='Message deleted', description=message.content, color=0xDD2E44, timestamp=datetime.utcnow())

        file = None
        if message.attachments:
            attachment = message.attachments[0]

            # can only properly recover images
            if attachment.filename.endswith(VALID_IMAGE_FORMATS):
                buf = BytesIO()
                try:
                    await attachment.save(buf, use_cached=True)
                except discord.HTTPException:
                    pass
                else:
                    file = discord.File(buf, filename=attachment.filename)
                    embed.set_image(url=f'attachment://{attachment.filename}')

        author = message.author
        embed.set_author(name=f'{author} → #{message.channel}', icon_url=author.avatar_url_as(format='png'))
        embed.set_footer(text=f'Author ID: {author.id} | Message ID: {message.id}')

        await self.log_chan.send(file=file, embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self.log_message(message)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):
        # sort by timestamp to make sure messages are logged in correct order
        messages.sort(key=lambda m: m.created_at)
        for message in messages:
            await self.log_message(message)

    def format_content_diff(self, before: str, after: str) -> Tuple[str, str]:
        # taken from https://github.com/python-discord/bot/pull/646
        diff = difflib.ndiff(before.split(), after.split())
        groups = [(t, [s[2:] for s in w]) for t, w in itertools.groupby(diff, key=lambda s: s[0])]

        out_before = []
        out_after = []
        for index, (type_, words) in enumerate(groups):
            sub = ' '.join(words)
            if type_ == '-':
                out_before.append(f'[{sub}](http://-)')
            elif type_ == '+':
                out_after.append(f'[{sub}](http://+)')
            elif type_ == ' ':
                if len(words) > 2:
                    sub = ''
                    if index > 0:
                        sub += words[0]

                    sub += ' ... '

                    if index < len(groups):
                        sub += words[-1]

                out_before.append(sub)
                out_after.append(sub)

        return ' '.join(out_before), ' '.join(out_after)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not after.guild or before.guild != self.guild:
            return

        if before.type is not discord.MessageType.default: # TODO d.py 1.3: if message.is_system()
            return

        if before.content == after.content:
            return

        desc = f'[Jump to message]({before.jump_url})'
        embed = discord.Embed(title='Message edited', description=desc, color=0xF5B942, timestamp=datetime.utcnow())

        before_content, after_content = self.format_content_diff(before.content, after.content)
        embed.add_field(name='Before', value=before_content, inline=False)
        embed.add_field(name='After', value=after_content, inline=False)

        author = before.author
        embed.set_author(name=f'{author} → #{before.channel}', icon_url=author.avatar_url_as(format='png'))
        embed.set_footer(text=f'Author ID: {author.id} | Message ID: {before.id}')

        await self.log_chan.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(GuildLog(bot))
