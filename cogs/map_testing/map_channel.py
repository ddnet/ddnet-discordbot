import enum
import re
from typing import List, Optional

import discord

from cogs.map_testing.submission import InitialSubmission
from utils.text import human_join, sanitize

from . import CAT_GROUP_MAP_TESTING, CAT_GROUP_WAITING_MAPPER, CAT_GROUP_EVALUATED_MAPS

class MapState(enum.Enum):
    TESTING     = ''
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
            details, _, self.mapper_mentions = channel.topic.splitlines()
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
    def topic(self) -> str:
        return '\n'.join((self.details, self.preview_url, self.mapper_mentions))


    async def get_category_with_free_slot(self, cat_group: list[int]) -> discord.CategoryChannel:
        for c in cat_group:
            category = self.guild.get_channel(c)
            if not isinstance(category, discord.CategoryChannel):
                continue # Perhaps log this as this should be impossible

            if len(category.channels) < 50:
                return category

        raise RuntimeError("Testing category full")

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

    async def set_state(self, *, state: MapState):
        if state == self.state:
            return

        if state is MapState.TESTING:
            cat_group_target = CAT_GROUP_MAP_TESTING
        elif state is MapState.WAITING:
            cat_group_target = CAT_GROUP_WAITING_MAPPER
        else:
            cat_group_target = CAT_GROUP_EVALUATED_MAPS

        options = {'name': str(self)}
        if self.category_id not in cat_group_target:
            options['category'] = category = await self.get_category_with_free_slot(cat_group_target)
            options['position'] = category.channels[-1].position + 1 if state is MapState.TESTING else 0

        await self.edit(**options)

        # Only change the state if nothing fails
        self.state = state

    @classmethod
    async def from_submission(cls, isubm: InitialSubmission, **options):
        self = cls.__new__(cls)
        self.name = isubm.name
        self.mappers = isubm.mappers
        self.server = isubm.server
        self.state = MapState.TESTING
        self.mapper_mentions = isubm.author.mention
        category = self.get_category_with_free_slot(CAT_GROUP_MAP_TESTING)
        self._channel = await category.create_text_channel(str(self), topic=self.topic, **options)
        return self
