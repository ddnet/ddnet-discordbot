import json
import re
from typing import Dict, List, Union

import discord

from utils.misc import maybe_coroutine

def format_size(size):
    for unit in ('B', 'KB', 'MB'):
        if size < 1024.0:
            return round(size, 2), unit
        size /= 1024.0


class TestLogError(Exception):
    pass


class TestLog:
    __slots__ = ('channel', 'guild', '_messages', '_avatars', '_attachments', '_emojis')

    VERSION = 1.0

    DIR = 'data/map-testing/testlogs'

    bot = None

    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.guild = channel.guild

        self._messages = []
        self._avatars = {}
        self._attachments = {}
        self._emojis = {}

    @property
    def name(self) -> str:
        return self.channel.name[2:]  # strip leading emojis

    @property
    def topic(self) -> str:
        if self.channel.topic is None:
            return ''

        return self.channel.topic.split('\n')[0].replace('**', '')  # strip markdown bolding

    @property
    def url(self) -> str:
        return f'https://ddnet.tw/testlogs/show/{self.name}'

    @property
    def content(self) -> Dict:
        return {
            'protocol': {
                'version': self.VERSION
            },
            'name': self.name,
            'topic': self.topic,
            'messages': self._messages
        }

    @property
    def assets(self) -> Dict:
        return {
            'avatar': self._avatars,
            'attachment': self._attachments,
            'emoji': self._emojis
        }

    def json(self) -> str:
        return json.dumps(self.content)

    def _handle_multiline_codeblock(self, text: str) -> Dict:
        return {'multiline-codeblock': {'text': text}}

    def _handle_inline_codeblock(self, text: str) -> Dict:
        return {'inline-codeblock': {'text': text}}

    async def _handle_custom_emoji(self, animated: str, emoji_name: str, emoji_id: str) -> Dict:
        emoji = discord.PartialEmoji(animated=bool(animated), name=emoji_name, id=int(emoji_id))

        emoji_url = str(emoji.url)
        async with self.bot.session.get(emoji_url) as resp:
            if resp.status != 200:
                raise TestLogError(':deleted-emoji:')

        self._emojis[f'{emoji.id}.png'] = emoji_url

        return {
            'custom-emoji': {
                'name': emoji.name,
                'id': emoji.id
            }
        }

    async def _handle_user_mention(self, user_id: str) -> Dict:
        user_id = int(user_id)
        user = self.guild.get_member(user_id) or self.bot.get_user(user_id)
        if user is None:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                raise TestLogError('@Deleted User')

        return {'user-mention': self._handle_user(user)}

    async def _handle_channel_mention(self, channel_id: str) -> Dict:
        channel_id = int(channel_id)
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.NotFound:
                raise TestLogError('#deleted-channel')

        return {
            'channel-mention': {
                'name': channel.name,
                'highlight': channel.guild == self.guild
            }
        }

    def _handle_role_mention(self, role_id: str) -> Dict:
        role = self.guild.get_role(int(role_id))
        if role is None:
            raise TestLogError('@Deleted Role')

        return {
            'role-mention': {
                'name': role.name,
                'highlight': role.mentionable
            }
        }

    def _handle_user(self, user: Union[discord.User, discord.Member]) -> Dict:
        if user.avatar is not None:
            self._avatars[f'{user.avatar}.png'] = str(user.avatar_url_as(format='png'))

        roles = ['generic']
        if isinstance(user, discord.Member):
            roles += [r.name for r in user.roles if not r.is_default()]

        return {
            'name': user.name,
            'discriminator': user.discriminator,
            'avatar': {
                'id': user.avatar or str(user.default_avatar.value)
            },
            'roles': roles[::-1]
        }

    async def _handle_text(self, text: str) -> Dict:
        url_re = r'<((?:https?|steam):\/\/(?:-\.)?(?:[^\s\/?\.#-]+\.?)+(?:\/[^\s]*)?)>'
        out = [{'text': re.sub(url_re, r'\1', text)}]  # TODO: handle urls after codeblocks

        regexes = {
            r'\`\`\`(?:[^\`]*?\n)?([^\`]+)\n?\`\`\`':   self._handle_multiline_codeblock,
            r'(?:\`|\`\`)([^\`]+)(?:\`|\`\`)':          self._handle_inline_codeblock,
            r'<(a)?:(.*):(\d*)>':                       self._handle_custom_emoji,
            r'<@!?(\d+)>':                              self._handle_user_mention,
            r'<#(\d+)>':                                self._handle_channel_mention,
            r'<@&(\d+)>':                               self._handle_role_mention
        }

        for regex, handler in regexes.items():
            for i, chunk in enumerate(out):
                text = chunk.get('text', None)
                if text is None:
                    continue

                match = re.search(regex, text)
                if match is None:
                    continue

                start = text[:match.start()]
                end = text[match.end():]

                try:
                    processed = await maybe_coroutine(handler, *match.groups())
                except TestLogError as exc:
                    out[i] = {'text': start + str(exc) + end}
                else:
                    if start:
                        out[i] = {'text': start}
                        i += 1
                    else:
                        del out[i]

                    out.insert(i, processed)

                    if end:
                        out.insert(i + 1, {'text': end})

        return {'text': out}

    def _handle_attachments(self, attachments: List[discord.Attachment]) -> Dict:
        attachment = attachments[0]  # TODO: handle multiple attachments

        filename, ext = attachment.filename.rsplit('.', 1)
        self._attachments[f'{attachment.id}.{ext}'] = attachment.url

        out = {
            'id': attachment.id,
            'basename': filename,
            'extension': f'.{ext}'  # TODO: prefix the dot server-side
        }

        if ext in ('webp', 'jpeg', 'jpg', 'png', 'gif'):
            return {'image': out}
        elif ext in ('webm', 'mp4'):
            return {'video': out}  # TODO: handle videos server-side
        else:
            size, unit = format_size(attachment.size)
            out.update({
                'filesize': size,
                'filesize-units': unit
            })

            return {'attachment': out}

    def _handle_reactions(self, reactions: List[discord.Reaction]) -> Dict:
        out = []
        for reaction in reactions:
            emoji = reaction.emoji
            chunk = {'count': reaction.count}
            if reaction.custom_emoji:
                self._emojis[f'{emoji.id}.png'] = str(emoji.url)
                chunk.update({
                    'name': emoji.name,
                    'id': emoji.id
                })
            else:
                chunk['emoji'] = emoji

            out.append(chunk)

        return {'reactions': out}

    async def _process(self):
        async for message in self.channel.history(limit=None, oldest_first=True):
            content_handlers = (
                (self._handle_text, message.content),
                (self._handle_attachments, message.attachments),
                (self._handle_reactions, message.reactions)
            )

            self._messages.append({
                'author': self._handle_user(message.author),
                'timestamp': message.created_at.isoformat(),
                'content': [await maybe_coroutine(h, a) for h, a in content_handlers if a]
            })

    @classmethod
    async def from_channel(cls, channel: discord.TextChannel):
        self = cls(channel)
        await self._process()

        return self
