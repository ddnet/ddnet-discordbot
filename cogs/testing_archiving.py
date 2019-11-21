#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import re
from io import BytesIO, StringIO
from typing import Optional, Tuple

import discord
from discord.ext import commands

URL_RE = r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b' \
         r'(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)'
MULTILINE_RE = re.compile(r'```(?:[^`]*?\n)?([^`]+)\n?```')
INLINE_RE = re.compile(r'(?:`|``)([^`]+)(?:`|``)')
CUSTOM_EMOJI_RE = re.compile(r'<(a)?:(.*):(\d*)>')
USER_RE = re.compile(r'<@!?(\d+)>')
CHANNEL_RE = re.compile(r'<#(\d+)>')
ROLE_RE = re.compile(r'<@&(\d+)>')


class Archiving(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def gen_json(self, channel: discord.TextChannel) -> Tuple[str, dict]:
        guild = channel.guild

        def process_multiline_codeblock(text: str) -> dict:
            return {
                'multiline-codeblock': {
                    'text': text
                }
            }

        def process_inline_codeblock(text: str) -> dict:
            return {
                'inline-codeblock': {
                    'text': text
                }
            }

        async def process_custom_emoji(animated: str, emoji_name: str, emoji_id: str) -> Optional[dict]:
            emoji = discord.PartialEmoji(animated=bool(animated), name=emoji_name, id=int(emoji_id))

            resp = await self.bot.session.get(str(emoji.url))
            if resp.status != 200:
                return None

            assets['emojis'].add((f'{emoji.id}.png', emoji.url))

            return {
                'custom-emoji': {
                    'name': emoji.name,
                    'id': emoji.id
                }
            }

        async def process_user_mention(user_id: str) -> Optional[dict]:
            user_id = int(user_id)
            user = guild.get_member(user_id) or self.bot.get_user(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except discord.NotFound:
                    return None

            if user.avatar:
                assets['avatars'].add((f'{user.avatar}.png', user.avatar_url_as(format='png')))

            if isinstance(user, discord.Member):
                roles = [
                    'generic' if r == guild.default_role else r.name
                    for r in user.roles[::-1]
                ]
            else:
                roles = ['generic']

            return {
                'user-mention': {
                    'name': user.name,
                    'discriminator': user.discriminator,
                    'avatar': {
                        'id': user.avatar or str(user.default_avatar.value)
                    },
                    'roles': roles
                }
            }

        async def process_channel_mention(channel_id: str) -> Optional[dict]:
            channel_id = int(channel_id)
            channel = guild.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except discord.NotFound:
                    return None

            return {
                'channel-mention': {
                    'name': channel.name,
                    'highlight': channel.guild == guild
                }
            }

        def process_role_mention(role_id: str) -> Optional[dict]:
            role = guild.get_role(int(role_id))
            if not role:
                return None

            return {
                'role-mention': {
                    'name': role.name,
                    'hightlight': role.mentionable
                }
            }

        regexes = {
            MULTILINE_RE:    process_multiline_codeblock,
            INLINE_RE:       process_inline_codeblock,
            CUSTOM_EMOJI_RE: process_custom_emoji,
            USER_RE:         process_user_mention,
            CHANNEL_RE:      process_channel_mention,
            ROLE_RE:         process_role_mention
        }

        assets = {
            'avatars': set(),
            'attachments': set(),
            'emojis': set()
        }

        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            author = message.author
            if author.avatar:
                assets['avatars'].add((f'{author.avatar}.png', author.avatar_url_as(format='png')))

            if isinstance(author, discord.Member):
                if author.roles is None:
                    roles = ['generic']
                else:
                    roles = [
                        'generic' if r == guild.default_role else r.name
                        for r in author.roles[::-1]
                    ]
            else:
                roles = ['generic']

            author = {
                'name': author.name,
                'discriminator': author.discriminator,
                'avatar': {
                    'id': author.avatar or str(author.default_avatar.value)
                },
                'roles': roles
            }

            content = []

            if message.content:
                content_text = [
                    {
                        'text': re.sub(r'<(%s)>' % URL_RE, r'\1', message.content)
                    }
                ]

                for pattern, processor in regexes.items():
                    for i, chunk in enumerate(content_text):
                        text = chunk.get('text')
                        if text is None:
                            continue

                        match = pattern.search(text)
                        if match is None:
                            continue

                        if asyncio.iscoroutinefunction(processor):
                            processed = await processor(*match.groups())
                        else:
                            processed = processor(*match.groups())

                        if processed is None:
                            # Disregard false positives
                            continue

                        if match.start() > 0:
                            content_text[i] = {'text': text[:match.start()]}
                            i += 1
                        else:
                            del content_text[i]

                        content_text.insert(i, processed)

                        if match.end() < len(text):
                            content_text.insert(i + 1, {'text': text[match.end():]})

                content.append({'text': content_text})

            if message.attachments:
                attachment = message.attachments[0]
                basename, extension = os.path.splitext(attachment.filename)
                extension = extension.lower()
                assets['attachments'].add((f'{attachment.id}{extension}', attachment.url))
                base = {
                    'id': attachment.id,
                    'basename': basename,
                    'extension': extension
                }

                if extension in ('.webp', '.jpeg', '.jpg', '.png', '.gif'):
                    content_attachment = {'image': base}
                elif extension in ('.webm', '.mp4'):
                    content_attachment = {'video': base}
                else:
                    def format_size(size):
                        for unit in ('B','KB','MB','GB','TB'):
                            if size < 1024.0:
                                break
                            size /= 1024.0
                        return round(size, 2), unit

                    filesize, units = format_size(attachment.size)
                    size = {
                        'filesize': filesize,
                        'filesize-units': units
                    }
                    content_attachment = {
                        'attachment': {**base, **size}
                    }

                content.append(content_attachment)

            if message.reactions:
                content_reactions = []
                for reaction in message.reactions:
                    emoji = reaction.emoji
                    chunk =  {'count': reaction.count}
                    if isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
                        assets['emojis'].add((f'{emoji.id}.png', emoji.url))
                        chunk.update({
                            'name': emoji.name,
                            'id': emoji.id
                        })
                    else:
                        chunk['emoji'] = emoji

                    content_reactions.append(chunk)

                content.append({'reactions': content_reactions})

            messages.append({
                'author': author,
                'timestamp': message.created_at.isoformat(),
                'content': content
            })

        data = {
            'protocol': {
                'version': 1.0
            },
            'name': channel.name[2:],  # Strip first 2 chars as they are status emojis
            'topic': channel.topic.split('\n')[0].replace('**', '') if channel.topic else '',  # Remove markdown bolding
            'messages': messages
        }

        return data, assets

    async def upload_file(self, asset_type: str, file: BytesIO, filename: str) -> str:
        url = self.bot.config.get('DDNET_UPLOAD', 'URL')

        if asset_type == 'map':
            name = 'map_name'
        elif asset_type == 'log':
            name = 'channel_name'
        elif asset_type in ('attachment', 'avatar', 'emoji'):
            name = 'asset_name'
        else:
            return str(-1)

        data = {
            'asset_type': asset_type,
            'file': file,
            name: filename
        }

        headers = {'X-DDNet-Token': self.bot.config.get('DDNET_UPLOAD', 'TOKEN')}

        async with self.bot.session.post(url, data=data, headers=headers) as resp:
            status = resp.status
            if status != 200:
                return await resp.text()

            return str(status)

    @commands.command()
    @commands.is_owner()
    async def archive(self, ctx: commands.Context, channel_id: int):
        failed = []
        channel = self.bot.get_channel(channel_id)
        data, assets = await self.gen_json(channel)

        with open(f'testlogs/json/{channel.name[2:]}.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(data))

        code = await self.upload_file('log', StringIO(json.dumps(data)), channel.name[2:])
        if code != '200':
            await ctx.send(code)
            return

        for type_, elements in assets.items():
            for id_, a in elements:
                async with self.bot.session.get(str(a)) as resp:
                    bytes_ = await resp.read()
                    with open(f'testlogs/assets/{type_}/{id_}', 'wb') as f:
                        f.write(bytes_)


                    file = BytesIO(bytes_)

                    code = await self.upload_file(type_[:-1], file, id_)
                    if code != '200':
                        failed.append(f'{id_}: {code}')

        await ctx.message.add_reaction('📄')


def setup(bot):
    bot.add_cog(Archiving(bot))
