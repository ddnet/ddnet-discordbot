import enum
import json
import logging
from io import BytesIO, StringIO
from typing import Optional, Union

import discord
from discord.ext import commands

from cogs.map_testing.log import TestLog
from cogs.map_testing.submission import InitialSubmission, Submission, SubmissionState
from utils.text import sanitize

log = logging.getLogger(__name__)

CAT_MAP_TESTING     = 449352010072850443
CAT_EVALUATED_MAPS  = 462954029643989003
CHAN_INFO           = 455392314173554688
CHAN_SUBMIT_MAPS    = 455392372663123989
ROLE_TESTING        = 455814387169755176
WH_MAP_RELEASES     = 345299155381649408


class MapState(enum.Enum):
    TESTING     = ''
    READY       = '✅'
    DECLINED    = '❌'
    RELEASED    = '🆙'

    def __str__(self) -> str:
        return self.value


def is_testing(channel: discord.TextChannel) -> bool:
    return isinstance(channel, discord.TextChannel) and channel.category_id in (CAT_MAP_TESTING, CAT_EVALUATED_MAPS)

def is_staff(member: discord.Member, channel: discord.TextChannel) -> bool:
    return channel.permissions_for(member).manage_channels

def has_map(message: discord.Message) -> bool:
    return message.attachments and message.attachments[0].filename.endswith('.map')

def is_pin(message: discord.Message) -> bool:
    return message.type is discord.MessageType.pins_add

def testing_check():
    def predicate(ctx):
        channel = ctx.channel
        return channel.id not in (CHAN_INFO, CHAN_SUBMIT_MAPS) and is_testing(channel) and is_staff(ctx.author, channel)
    return commands.check(predicate)


class MapTesting(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        TestLog.bot = bot

        self._active_submissions = set()

    async def ddnet_upload(self, asset_type: str, buf: Union[BytesIO, StringIO], filename: str):
        url = self.bot.config.get('DDNET_UPLOAD', 'URL')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET_UPLOAD', 'TOKEN')}

        if asset_type == 'map':
            name = 'map_name'
        elif asset_type == 'log':
            name = 'channel_name'
        elif asset_type in ('attachment', 'avatar', 'emoji'):
            name = 'asset_name'
        else:
            raise ValueError('Invalid asset type')

        data = {
            'asset_type': asset_type,
            'file': buf,
            name: filename
        }

        async with self.bot.session.post(url, data=data, headers=headers) as resp:
            if resp.status != 200:
                fmt = 'Failed uploading %s %r to ddnet.tw: %s (status code: %d %s)'
                log.error(fmt, asset_type, filename, await resp.text(), resp.status, resp.reason)
                raise RuntimeError('Could not upload file to ddnet.tw')

            log.info('Successfully uploaded %s %r to ddnet.tw', asset_type, filename)

    async def upload_submission(self, subm: Submission):
        try:
            await self.ddnet_upload('map', await subm.buffer(), str(subm))
        except RuntimeError:
            await subm.set_status(SubmissionState.ERROR)
        else:
            await subm.set_status(SubmissionState.UPLOADED)

    async def validate_submission(self, isubm: InitialSubmission):
        try:
            isubm.validate()
        except ValueError as exc:
            await isubm.respond(exc)
            await isubm.set_status(SubmissionState.ERROR)
        else:
            await isubm.set_status(SubmissionState.VALIDATED)

    @commands.Cog.listener('on_message')
    async def handle_submission(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        if not has_map(message):
            return

        if message.channel.id == CHAN_SUBMIT_MAPS:
            isubm = InitialSubmission(message)
            await self.validate_submission(isubm)

        elif is_testing(message.channel):
            subm = Submission(message)
            if subm.can_bypass():
                await self.upload_submission(subm)
            else:
                await subm.set_status(SubmissionState.VALIDATED)

            await subm.pin()

    @commands.Cog.listener('on_raw_message_edit')
    async def handle_submission_edit(self, payload: discord.RawMessageUpdateEvent):
        # have to work with the raw data here to avoid unnecessary api calls
        data = payload.data
        if 'author' in data and int(data['author']['id']) == self.bot.user.id:
            return

        channel_id = int(data['channel_id'])  # TODO d.py 1.3.0: -> payload.channel_id
        if channel_id != CHAN_SUBMIT_MAPS:
            return

        if not ('attachments' in data and data['attachments'][0]['filename'].endswith('.map')):
            return

        # don't handle already processed submissions
        if 'reactions' in data and data['reactions'][0]['emoji']['name'] == str(SubmissionState.PROCESSED):
            return

        channel = self.bot.get_channel(channel_id)
        message = await channel.fetch_message(payload.message_id)

        isubm = InitialSubmission(message)
        await self.validate_submission(isubm)

    @commands.Cog.listener('on_raw_reaction_add')
    async def handle_submission_approve(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        if str(payload.emoji) != str(SubmissionState.VALIDATED):
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel.id == CHAN_SUBMIT_MAPS:
            initial = True
        elif is_testing(channel):
            initial = False
        else:
            return

        user = channel.guild.get_member(payload.user_id)
        if not is_staff(user, channel):
            return

        message = await channel.fetch_message(payload.message_id)
        if not has_map(message):
            return

        if initial:
            isubm = InitialSubmission(message)
            if isubm in self._active_submissions:
                return

            try:
                isubm.validate()
            except ValueError:
                return

            self._active_submissions.add(isubm)
            subm = await isubm.process()
            await isubm.set_status(SubmissionState.PROCESSED)
            self._active_submissions.discard(isubm)

        else:
            subm = Submission(message)

        await self.upload_submission(subm)
        log.info('%s approved submission %r in channel #%s', user, subm.filename, channel)

    @commands.Cog.listener('on_message')
    async def handle_unwanted_message(self, message: discord.Message):
        author = message.author
        channel = message.channel

        # delete system pin messages by ourself
        if not (is_testing(channel) and is_pin(message) and author == self.bot.user):
            return

        # delete messages without a map file by non staff in submit maps channel
        if not (channel.id == CHAN_SUBMIT_MAPS and not has_map(message) and not is_staff(author, channel)):
            return

        await message.delete()

    def get_map_channel(self, name: str) -> Optional[discord.TextChannel]:
        name = sanitize(name.lower())
        mt_category = self.bot.get_channel(CAT_MAP_TESTING)
        em_category = self.bot.get_channel(CAT_EVALUATED_MAPS)
        return discord.utils.find(lambda c: c.name[1:] == name, mt_category.text_channels) \
            or discord.utils.find(lambda c: c.name[2:] == name, em_category.text_channels)

    async def handle_perms(self, payload: discord.RawReactionActionEvent, action: str):
        # TODO d.py 1.3.0: action -> payload.event_type == 'REACTION_ADD' || 'REACTION_REMOVE'
        if payload.user_id == self.bot.user.id:
            return

        if str(payload.emoji) != str(SubmissionState.PROCESSED):
            return

        channel = self.bot.get_channel(payload.channel_id)
        user = channel.guild.get_member(payload.user_id)

        if channel.id == CHAN_INFO:
            testing_role = channel.guild.get_role(ROLE_TESTING)
            if testing_role in user.roles:
                if action == 'remove':
                    await user.remove_roles(testing_role)
            elif action == 'add':
                await user.add_roles(testing_role)

        elif channel.id == CHAN_SUBMIT_MAPS:
            message = await channel.fetch_message(payload.message_id)
            if not has_map(message):
                return

            map_channel = self.get_map_channel(message.attachments[0].filename[:-4])
            if map_channel is None:
                if action == 'add':
                    await message.remove_reaction(payload.emoji, user)
                return

            if map_channel.overwrites_for(user).read_messages:
                if action == 'remove':
                    await map_channel.set_permissions(user, overwrite=None)
            elif action == 'add':
                await map_channel.set_permissions(user, read_messages=True)

    @commands.Cog.listener('on_raw_reaction_add')
    async def handle_perms_add(self, payload: discord.RawReactionActionEvent):
        await self.handle_perms(payload, 'add')

    @commands.Cog.listener('on_raw_reaction_remove')
    async def handle_perms_remove(self, payload: discord.RawReactionActionEvent):
        await self.handle_perms(payload, 'remove')

    async def move_map_channel(self, channel: discord.TextChannel, *, state: MapState):
        # TODO: sort channels
        prev_state = next((s for s in MapState if str(s) == channel.name[0]), MapState.TESTING)
        if prev_state is state:
            return

        if prev_state is MapState.TESTING:
            name = channel.name
        else:
            name = channel.name[1:]

        if state is MapState.TESTING:
            category = self.bot.get_channel(CAT_MAP_TESTING)
        else:
            category = self.bot.get_channel(CAT_EVALUATED_MAPS)

        await channel.edit(name=str(state) + name, category=category)

    @commands.command()
    @testing_check()
    async def reset(self, ctx: commands.Context):
        """Reset a map"""
        await self.move_map_channel(ctx.channel, state=MapState.TESTING)

    @commands.command()
    @testing_check()
    async def ready(self, ctx: commands.Context):
        """Ready a map"""
        await self.move_map_channel(ctx.channel, state=MapState.READY)

    @commands.command()
    @testing_check()
    async def decline(self, ctx: commands.Context):
        """Decline a map"""
        await self.move_map_channel(ctx.channel, state=MapState.DECLINED)

    @commands.Cog.listener('on_message')
    async def handle_release(self, message: discord.Message):
        if message.webhook_id != WH_MAP_RELEASES:
            return

        map_url_re = r'\[(?P<name>.+)\]\(<?https:\/\/ddnet\.tw\/maps\/\?map=.+?>?\)'
        match = re.search(map_url_re, message.content)
        if match is None:
            return

        map_channel = self.get_map_channel(match.group('name'))
        if map_channel is None:
            return

        await self.move_map_channel(map_channel, state=MapState.RELEASED)

    @commands.command()
    @commands.is_owner()
    async def archive(self, ctx: commands.Context, channel_id: int):
        """Archive a map channel"""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return await ctx.send('Could not find that channel')

        if channel.category_id != CAT_EVALUATED_MAPS:
            return await ctx.send('Can\'t archive that channel')

        testlog = await TestLog.from_channel(channel)

        with open(f'{testlog.DIR}/json/{testlog.name}.json', 'w', encoding='utf-8') as f:
            f.write(testlog.json())

        buf = StringIO(testlog.json())
        try:
            await self.ddnet_upload('log', buf, testlog.name)
        except RuntimeError as exc:
            return await ctx.send(exc)

        failed = []
        for asset_type, assets in testlog.assets.items():
            for filename, url in assets.items():
                async with self.bot.session.get(url) as resp:
                    if resp.status != 200:
                        failed.append(filename)
                        continue

                    bytes_ = await resp.read()

                with open(f'{testlog.DIR}/assets/{asset_type}s/{filename}', 'wb') as f:
                    f.write(bytes_)

                buf = BytesIO(bytes_)
                try:
                    await self.ddnet_upload(asset_type, buf, filename)
                except RuntimeError as exc:
                    failed.append(filename)
                    continue

        msg = testlog.url
        if failed:
            fmt = ', '.join(repr(f) for f in failed)
            msg += f'\nFailed asset uploads:\n```py\n{fmt}\n```'

        await ctx.send(msg)


def setup(bot: commands.Bot):
    bot.add_cog(MapTesting(bot))
