import enum
import re
from typing import List

import discord
import asyncio

from cogs.map_testing.submission import InitialSubmission
from utils.text import human_join, sanitize

import logging

CAT_MAP_TESTING     = 449352010072850443
CAT_WAITING_MAPPER  = 746076708196843530
CAT_EVALUATED_MAPS  = 462954029643989003


class MapState(enum.Enum):
    TESTING     = ''
    RC          = '☑'
    WAITING     = '💤'
    READY       = '✅'
    DECLINED    = '❌'
    RELEASED    = '🆙'

    def __str__(self) -> str:
        return self.value


class MapChannel:
    def __init__(self, channel: discord.TextChannel):
        self._channel = channel

        self.state = next((s for s in MapState if str(s) == channel.name[0]), MapState.TESTING)

        try:
            details, _, self.mapper_mentions, *initial_ready = channel.topic.splitlines()
            self.initial_ready = initial_ready[0] if initial_ready else None
        except (AttributeError, IndexError):
            raise ValueError('Malformed channel topic') from None

        match = re.match(r'^"(?P<name>.+)" by (?P<mappers>.+) \[(?P<server>.+)\]$', details.replace('**', ''))
        if match is None:
            raise ValueError('Malformed map details')

        self.name = match.group('name')
        self.mappers = re.split(r', | & ', match.group('mappers'))
        self.server = match.group('server')

    def __getattr__(self, attr: str):
          return getattr(self._channel, attr)

    def __str__(self) -> str:
        return str(self.state) + self.emoji + self.filename

    @property
    def filename(self) -> str:
        return sanitize(self.name)

    @property
    def emoji(self) -> str:
        return InitialSubmission.SERVER_TYPES[self.server]

    @property
    def details(self) -> str:
        mappers = human_join([f'**{m}**' for m in self.mappers])
        return f'**"{self.name}"** by {mappers} [{self.server}]'

    @property
    def preview_url(self) -> str:
        return f'https://ddnet.org/testmaps/?map={self.filename}'

    @property
    def _initial_ready(self) -> str:
        return self.initial_ready

    @property
    def topic(self) -> str:
        topic = [i for i in (self.details, self.preview_url, self.mapper_mentions, self._initial_ready) if
                 i is not None]
        return '\n'.join(topic)

    async def update(self, name: str=None, mappers: List[str]=None, server: str=None):
        prev_details = self.details

        if name is not None:
            self.name = name
        if mappers is not None:
            self.mappers = mappers
        if server is not None:
            server = server.capitalize()
            if server not in InitialSubmission.SERVER_TYPES:
                raise ValueError('Invalid server type')
            self.server = server

        if prev_details != self.details:
            await self.edit(name=str(self), topic=self.topic)

    async def set_state(self, *, state: MapState, ready_state_set_by: str = None):
        self.state = state

        if state is MapState.TESTING:
            category_id = CAT_MAP_TESTING
        elif state is MapState.RC:
            category_id = CAT_MAP_TESTING
        elif state is MapState.WAITING:
            category_id = CAT_WAITING_MAPPER
        else:
            category_id = CAT_EVALUATED_MAPS

        options = {'name': str(self)}

        if ready_state_set_by is not None:
            self.initial_ready = ready_state_set_by
        else:
            self.initial_ready = None

        if category_id != self.category_id:
            options['category'] = category = self.guild.get_channel(category_id)
            options['position'] = category.channels[-1].position + 1 if state in [MapState.TESTING, MapState.RC] else 0

        options['topic'] = f"{self.topic}"

        await self.edit(**options)

    @classmethod
    async def from_submission(cls, isubm: InitialSubmission, **options):
        self = cls.__new__(cls)
        self.name = isubm.name
        self.mappers = isubm.mappers
        self.server = isubm.server
        self.state = MapState.TESTING
        self.mapper_mentions = isubm.author.mention
        self.initial_ready = None
        self._channel = await isubm.channel.category.create_text_channel(str(self), topic=self.topic, **options)

        # Workaround for Discord API issue
        # await asyncio.sleep(2)
        await self._channel.edit(topic=self.topic)
        return self
