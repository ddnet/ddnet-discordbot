import enum
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional

import discord
from discord.ext import commands, tasks

from cogs.map_testing.log import TestLog
from cogs.map_testing.submission import InitialSubmission, Submission, SubmissionState
from utils.text import sanitize

log = logging.getLogger(__name__)

CAT_MAP_TESTING     = 449352010072850443
CAT_EVALUATED_MAPS  = 462954029643989003
CHAN_ANNOUNCEMENTS  = 420565311863914496
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

def by_releases_webhook(message: discord.Message) -> bool:
    return message.webhook_id == WH_MAP_RELEASES

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
        self.bot = TestLog.bot = bot

        self._active_submissions = set()

        self.auto_archive.start()

    def cog_unload(self):
        self.auto_archive.cancel()

    async def ddnet_upload(self, asset_type: str, buf: BytesIO, filename: str):
        url = self.bot.config.get('DDNET', 'UPLOAD')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET', 'TOKEN')}

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
            await subm.pin()

    async def validate_submission(self, isubm: InitialSubmission):
        try:
            exists = self.get_map_channel(isubm.name)
            if exists:
                raise ValueError('A channel for this map already exists')

            query = 'SELECT TRUE FROM stats_maps_static WHERE name = $1;'
            released = await self.bot.pool.fetchrow(query, isubm.name)
            if released:
                raise ValueError('A map with that name is already released')

            isubm.validate()
        except ValueError as exc:
            await isubm.respond(exc)
            await isubm.set_status(SubmissionState.ERROR)
        else:
            await isubm.set_status(SubmissionState.VALIDATED)

    @commands.Cog.listener('on_message')
    async def handle_submission(self, message: discord.Message):
        author = message.author
        if author == self.bot.user:
            return

        if not has_map(message):
            return

        channel = message.channel
        if channel.id == CHAN_SUBMIT_MAPS:
            isubm = InitialSubmission(message)
            await self.validate_submission(isubm)

        elif is_testing(channel):
            subm = Submission(message)
            if subm.is_original():
                if subm.is_by_mapper() or is_staff(author, channel):
                    await self.upload_submission(subm)
                else:
                    await subm.set_status(SubmissionState.VALIDATED)

    @commands.Cog.listener('on_raw_message_edit')
    async def handle_submission_edit(self, payload: discord.RawMessageUpdateEvent):
        # have to work with the raw data here to avoid unnecessary api calls
        data = payload.data
        if 'author' in data and int(data['author']['id']) == self.bot.user.id:
            return

        if payload.channel_id != CHAN_SUBMIT_MAPS:
            return

        if not ('attachments' in data and data['attachments'][0]['filename'].endswith('.map')):
            return

        # don't handle already processed submissions
        if 'reactions' in data and data['reactions'][0]['emoji']['name'] == str(SubmissionState.PROCESSED):
            return

        channel = self.bot.get_channel(payload.channel_id)
        message = self.bot.get_message(payload.message_id) or await channel.fetch_message(payload.message_id)

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

        message = self.bot.get_message(payload.message_id) or await channel.fetch_message(payload.message_id)
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
        bot_pin = is_testing(channel) and is_pin(message) and author == self.bot.user

        # delete messages without a map file by non staff in submit maps channel
        non_submission = channel.id == CHAN_SUBMIT_MAPS and not has_map(message) and not is_staff(author, channel)

        if bot_pin or non_submission:
            await message.delete()

    def get_map_channel(self, name: str) -> Optional[discord.TextChannel]:
        name = sanitize(name.lower())
        mt_category = self.bot.get_channel(CAT_MAP_TESTING)
        em_category = self.bot.get_channel(CAT_EVALUATED_MAPS)
        return discord.utils.find(lambda c: c.name[1:] == name, mt_category.text_channels) \
            or discord.utils.find(lambda c: c.name[2:] == name, em_category.text_channels)

    @commands.Cog.listener('on_raw_reaction_add')
    @commands.Cog.listener('on_raw_reaction_remove')
    async def handle_perms(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        if str(payload.emoji) != str(SubmissionState.PROCESSED):
            return

        action = payload.event_type
        channel = self.bot.get_channel(payload.channel_id)
        guild = channel.guild
        if action == 'REACTION_ADD':
            member = payload.member
        else:
            member = guild.get_member(payload.user_id)
            if member is None:
                return

        if channel.id == CHAN_INFO:
            testing_role = guild.get_role(ROLE_TESTING)
            if testing_role in member.roles:
                if action == 'REACTION_REMOVE':
                    await member.remove_roles(testing_role)
            elif action == 'REACTION_ADD':
                await member.add_roles(testing_role)

        elif channel.id == CHAN_SUBMIT_MAPS:
            message = self.bot.get_message(payload.message_id) or await channel.fetch_message(payload.message_id)
            if not has_map(message):
                return

            map_channel = self.get_map_channel(message.attachments[0].filename[:-4])
            if map_channel is None:
                if action == 'REACTION_ADD':
                    await message.remove_reaction(payload.emoji, member)
                return

            if map_channel.overwrites_for(member).read_messages:
                if action == 'REACTION_REMOVE':
                    await map_channel.set_permissions(member, overwrite=None)
            elif action == 'REACTION_ADD':
                await map_channel.set_permissions(member, read_messages=True)

    async def move_map_channel(self, channel: discord.TextChannel, *, state: MapState):
        name = channel.name

        prev_state = next((s for s in MapState if str(s) == name[0]), MapState.TESTING)
        if prev_state is state:
            return

        if prev_state is not MapState.TESTING:
            name = name[1:]

        options = {'name': str(state) + name}
        category = self.bot.get_channel(CAT_MAP_TESTING if state is MapState.TESTING else CAT_EVALUATED_MAPS)
        if category != channel.category:
            position = category.channels[-1].position + 1 if state is MapState.TESTING else 0

            options.update({'position': position, 'category': category})

        await channel.edit(**options)

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

    def get_map_channel_from_ann(self, content: str) -> Optional[discord.TextChannel]:
        map_url_re = r'\[(?P<name>.+)\]\(<?https:\/\/ddnet\.tw\/maps\/\?map=.+?>?\)'
        match = re.search(map_url_re, content)
        return match and self.get_map_channel(match.group('name'))

    @commands.Cog.listener('on_message')
    async def handle_map_release(self, message: discord.Message):
        if not by_releases_webhook(message):
            return

        map_channel = self.get_map_channel_from_ann(message.content)
        if map_channel is None:
            return

        try:
            await self.move_map_channel(map_channel, state=MapState.RELEASED)
        except discord.Forbidden as exc:
            log.error('Failed moving map channel #%s on release: %s', map_channel, exc.text)

    async def ddnet_delete(self, filename: str):
        url = self.bot.config.get('DDNET', 'DELETE')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET', 'TOKEN')}
        data = {'map_name': filename}

        async with self.bot.session.post(url, data=data, headers=headers) as resp:
            if resp.status != 200:
                fmt = 'Failed deleting map %r on ddnet.tw: %s (status code: %d %s)'
                log.error(fmt, filename, await resp.text(), resp.status, resp.reason)
                raise RuntimeError('Could not delete map on ddnet.tw')

            log.info('Successfully delete map %r on ddnet.tw', filename)

    async def archive_testlog(self, testlog: TestLog) -> bool:
        failed = False

        js = testlog.json()
        with open(f'{testlog.DIR}/json/{testlog.name}.json', 'w', encoding='utf-8') as f:
            f.write(js)

        try:
            await self.ddnet_upload('log', BytesIO(js.encode('utf-8')), testlog.name)
        except RuntimeError:
            failed = True

        for asset_type, assets in testlog.assets.items():
            for filename, url in assets.items():
                async with self.bot.session.get(url) as resp:
                    if resp.status != 200:
                        log.error('Failed fetching asset %r: %s', filename, await resp.text())
                        failed = True
                        continue

                    bytes_ = await resp.read()

                with open(f'{testlog.DIR}/assets/{asset_type}s/{filename}', 'wb') as f:
                    f.write(bytes_)

                try:
                    await self.ddnet_upload(asset_type, BytesIO(bytes_), filename)
                except RuntimeError:
                    failed = True
                    continue

        if testlog.map is not None:
            try:
                await self.ddnet_delete(testlog.map)
            except RuntimeError:
                pass

        return not failed

    @tasks.loop(hours=1.0)
    async def auto_archive(self):
        await self.bot.wait_until_ready()
        now = datetime.utcnow()

        ann_channel = self.bot.get_channel(CHAN_ANNOUNCEMENTS)
        ann_history = await ann_channel.history(after=now - timedelta(days=3)).filter(by_releases_webhook).flatten()
        recent_releases = {self.get_map_channel_from_ann(m.content) for m in ann_history}

        em_category = self.bot.get_channel(CAT_EVALUATED_MAPS)
        for channel in em_category.text_channels:
            # keep the channel until its map is released, including a short grace period
            if channel.name[0] == str(MapState.READY) or channel in recent_releases:
                continue

            # make sure there is no active discussion going on
            recent_message = await channel.history(limit=1, after=now - timedelta(days=5)).flatten()
            if recent_message:
                continue

            testlog = await TestLog.from_channel(channel)
            archived = await self.archive_testlog(testlog)

            if archived:
                await channel.delete()
                log.info('Sucessfully auto-archived channel #%s', channel)
            else:
                log.error('Failed auto-archiving channel #%s', channel)

    @commands.command()
    @commands.is_owner()
    async def archive(self, ctx: commands.Context, channel_id: int):
        """Archive a map channel"""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return await ctx.send('Couldn\'t find that channel')

        if not isinstance(channel, discord.TextChannel) or channel.category_id != CAT_EVALUATED_MAPS:
            return await ctx.send('Can\'t archive that channel')

        testlog = await TestLog.from_channel(channel)
        archived = await self.archive_testlog(testlog)

        if archived:
            await channel.delete()
            await ctx.send(f'Sucessfully archived channel {channel.mention}: {testlog.url}')
        else:
            await ctx.send(f'Failed archiving channel {channel.mention}: {testlog.url}')


def setup(bot: commands.Bot):
    bot.add_cog(MapTesting(bot))
