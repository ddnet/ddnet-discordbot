import enum
import logging
import os
import re
from io import BytesIO
from typing import Optional

import discord

from utils.misc import run_process
from utils.text import human_join, sanitize

log = logging.getLogger(__name__)


class SubmissionState(enum.Enum):
    VALIDATED   = '☑️'
    UPLOADED    = '🆙'
    PROCESSED   = '✅'
    ERROR       = '❌'

    def __str__(self) -> str:
        return self.value


class Submission:
    __slots__ = ('message', 'author', 'channel', 'filename', '_bytes')

    def __init__(self, message: discord.Message, *, raw_bytes: Optional[bytes]=None):
        self.message = message
        self.author = message.author
        self.channel = message.channel

        self.filename = message.attachments[0].filename

        self._bytes = raw_bytes

    def __str__(self) -> str:
        return self.filename[:-4]

    async def buffer(self) -> BytesIO:
        if self._bytes is None:
            self._bytes = await self.message.attachments[0].read()

        return BytesIO(self._bytes)

    async def get_file(self) -> discord.File:
        return discord.File(await self.buffer(), filename=self.filename)

    async def set_state(self, status: SubmissionState):
        for reaction in self.message.reactions:
            if any(str(s) == str(reaction) for s in SubmissionState):
                await self.message.clear_reaction(reaction)

        await self.message.add_reaction(str(status))

    async def pin(self):
        if self.message.pinned:
            return

        try:
            await self.message.pin()
        except discord.HTTPException:
            pass


class InitialSubmission(Submission):
    __slots__ = Submission.__slots__ + ('name', 'mappers', 'server', 'map_channel')

    DIR = 'data/map-testing'

    _FORMAT_RE = r'^\"(?P<name>.+)\" +by +(?P<mappers>.+) +\[(?P<server>.+)\]$'

    SERVER_TYPES = {
        'Novice':       '👶',
        'Moderate':     '🌸',
        'Brutal':       '💪',
        'Insane':       '💀',
        'Dummy':        '♿',
        'Oldschool':    '👴',
        'Solo':         '⚡',
        'Race':         '🏁',
        'Fun':          '🎉',
    }

    def __init__(self, message: discord.Message, *, raw_bytes: Optional[bytes]=None):
        super().__init__(message, raw_bytes=raw_bytes)

        self.name = None
        self.mappers = None
        self.server = None

    def validate(self):
        # can't do this in init since we need a reference to the submission even if it's improper
        match = re.search(self._FORMAT_RE, self.message.content, flags=re.IGNORECASE)
        if match is None:
            raise ValueError('Your map submission doesn\'t contain correctly formated details')

        self.name = match.group('name')
        if sanitize(self.name) != str(self):
            raise ValueError('Name and filename of your map submission don\'t match')

        self.mappers = re.split(r', | , | & | and ', match.group('mappers'))

        self.server = match.group('server').capitalize()
        if self.server not in self.SERVER_TYPES:
            raise ValueError('The server type of your map submission is not valid')

    async def respond(self, error: Exception):
        try:
            await self.author.send(error)
        except discord.Forbidden:
            pass

    @property
    def emoji(self) -> str:
        return self.SERVER_TYPES.get(self.server, '')

    async def generate_thumbnail(self) -> Optional[discord.File]:
        tmp = f'{self.DIR}/tmp/{self.message.id}.map'

        buf = await self.buffer()
        with open(tmp, 'wb') as f:
            f.write(buf.getvalue())

        try:
            stdout, stderr = await run_process(f'{self.DIR}/render_map {tmp} --size 1280')
        except RuntimeError as exc:
            error = str(exc)
        else:
            error = ' '.join(e for e in (stdout, stderr) if e)  # render_map prints errors to stdout

        if error:
            return log.error('Failed to generate thumbnail of map %r (%d): %s', self.filename, self.message.id, error)

        with open(f'{tmp}.png', 'rb') as f:
            buf = BytesIO(f.read())

        # cleanup
        os.remove(tmp)
        os.remove(f'{tmp}.png')

        return discord.File(buf, filename=f'{self}.png')

    async def process(self) -> Submission:
        perms = discord.PermissionOverwrite(read_messages=True)
        users = [self.message.author]
        for reaction in self.message.reactions:
            users += await reaction.users().flatten()
        overwrites = {u: perms for u in users}
        # category permissions:
        # - @everyone:  read_messages=False
        # - Tester:     manage_channels=True, read_messages=True, manage_messages=True, manage_roles=True
        # - testing:    read_messages=True
        # - bot.user:   read_messages=True, manage_messages=True
        overwrites.update(self.channel.category.overwrites)

        from cogs.map_testing.map_channel import MapChannel  # circular import
        self.map_channel = await MapChannel.from_submission(self, overwrites=overwrites)

        file = await self.get_file()
        msg = f'{self.author.mention} this is your map\'s testing channel! '\
               'Post map updates here and remember to follow our mapper rules: https://ddnet.tw/rules'
        message = await self.map_channel.send(msg, file=file)

        thumbnail = await self.generate_thumbnail()
        await self.map_channel.send(self.map_channel.preview_url, file=thumbnail)

        return Submission(message, raw_bytes=self._bytes)
