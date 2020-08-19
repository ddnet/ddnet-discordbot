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

GUILD_DDNET     = 252358080522747904
CHAN_WELCOME    = 311192969493348362
CHAN_JOIN_LEAVE = 255191476315750401
CHAN_LOGS       = 364164149359411201

VALID_IMAGE_FORMATS = ('.webp', '.jpeg', '.jpg', '.png', '.gif')


class GuildLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_DDNET or member.bot:
            return

        msg = f'📥 {member.mention}, Welcome to **DDraceNetwork\'s Discord**! ' \
              f'Please make sure to read <#{CHAN_WELCOME}>. ' \
               'Have a great time here <:happy:395753933089406976>'
        chan = self.bot.get_channel(CHAN_JOIN_LEAVE)
        await chan.send(msg)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != GUILD_DDNET or member.bot:
            return

        msg = f'📤 **{escape(str(member))}** just left the server <:mmm:395753965410582538>'
        chan = self.bot.get_channel(CHAN_JOIN_LEAVE)
        await chan.send(msg)

    async def log_message(self, message: discord.Message):
        if not message.guild or message.guild.id != GUILD_DDNET or message.is_system():
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

        chan = self.bot.get_channel(CHAN_LOGS)
        await chan.send(file=file, embed=embed)

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
        groups = [(c, [s[2:] for s in w]) for c, w in itertools.groupby(diff, key=lambda d: d[0]) if c != '?']

        out = {'-': [], '+': []}
        for i, (code, words) in enumerate(groups):
            sub = ' '.join(words)
            if code in '-+':
                out[code].append(f'[{sub}](http://{code})')
            else:
                if len(words) > 2:
                    sub = ''
                    if i > 0:
                        sub += words[0]

                    sub += ' ... '

                    if i < len(groups) - 1:
                        sub += words[-1]

                out['-'].append(sub)
                out['+'].append(sub)

        return ' '.join(out['-']), ' '.join(out['+'])

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.guild.id != GUILD_DDNET or before.is_system():
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

        chan = self.bot.get_channel(CHAN_LOGS)
        await chan.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(GuildLog(bot))
