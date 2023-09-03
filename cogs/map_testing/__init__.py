import io
import itertools
import logging
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Optional

import discord
from discord.ext import commands, tasks

from cogs.map_testing.log import TestLog
from cogs.map_testing.map_channel import MapChannel, MapState
from cogs.map_testing.submission import InitialSubmission, Submission, SubmissionState

log = logging.getLogger(__name__)

CAT_GROUP_MAP_TESTING     = [449352010072850443, 1118205044353941554]
CAT_GROUP_WAITING_MAPPER  = [746076708196843530]
CAT_GROUP_EVALUATED_MAPS  = [462954029643989003]
CAT_GROUP_TESTING = itertools.chain(CAT_GROUP_MAP_TESTING, CAT_GROUP_WAITING_MAPPER, CAT_GROUP_EVALUATED_MAPS)
CHAN_ANNOUNCEMENTS  = 420565311863914496
CHAN_INFO           = 455392314173554688
CHAN_SUBMIT_MAPS    = 455392372663123989
ROLE_ADMIN          = 293495272892399616
ROLE_TESTING_LEAD   = 746414504488861747
ROLE_TESTER         = 293543421426008064
ROLE_TESTING        = 455814387169755176
WH_MAP_RELEASES     = 345299155381649408


def is_testing(channel: discord.TextChannel) -> bool:
    return isinstance(channel, discord.TextChannel) and channel.category_id in CAT_GROUP_TESTING

def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_TESTER) for r in member.roles)

def by_releases_webhook(message: discord.Message) -> bool:
    return message.webhook_id == WH_MAP_RELEASES

def has_map(message: discord.Message) -> bool:
    return message.attachments and message.attachments[0].filename.endswith('.map')

def tester_check():
    def predicate(ctx: commands.Context) -> bool:
        return ctx.channel.id in ctx.cog._map_channels and is_staff(ctx.author)
    return commands.check(predicate)

def testing_lead_check():
    def predicate(ctx: commands.Context) -> bool:
        return ctx.guild is not None and any(r.id == ROLE_TESTING_LEAD for r in ctx.author.roles)
    return commands.check(predicate)


class MapTesting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = TestLog.bot = bot

        self._map_channels = {}
        self._active_submissions = set()

        bot.loop.create_task(self.load_map_channels())
        self.auto_archive.start()

    def cog_unload(self):
        self.auto_archive.cancel()

    async def load_map_channels(self):
        await self.bot.wait_until_ready()

        for category_id in CAT_GROUP_TESTING:
            category = self.bot.get_channel(category_id)
            for channel in category.text_channels:
                if channel.id in (CHAN_INFO, CHAN_SUBMIT_MAPS):
                    continue

                try:
                    self._map_channels[channel.id] = MapChannel(channel)
                except ValueError as exc:
                    log.error('Failed loading map channel #%s: %s', channel, exc)

    @property
    def map_channels(self) -> List[MapChannel]:
        return self._map_channels.values()

    def get_map_channel(self, channel_id: Optional[int]=None, **kwargs) -> Optional[MapChannel]:
        if channel_id is not None:
            return self._map_channels.get(channel_id)
        else:
            return discord.utils.get(self.map_channels, **kwargs)

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
                fmt = 'Failed uploading %s %r to ddnet.org: %s (status code: %d %s)'
                log.error(fmt, asset_type, filename, await resp.text(), resp.status, resp.reason)
                raise RuntimeError('Could not upload file to ddnet.org')

            log.info('Successfully uploaded %s %r to ddnet.org', asset_type, filename)

    async def ddnet_delete(self, filename: str):
        url = self.bot.config.get('DDNET', 'DELETE')
        headers = {'X-DDNet-Token': self.bot.config.get('DDNET', 'TOKEN')}
        data = {'map_name': filename}

        async with self.bot.session.post(url, data=data, headers=headers) as resp:
            if resp.status != 200:
                fmt = 'Failed deleting map %r on ddnet.org: %s (status code: %d %s)'
                log.error(fmt, filename, await resp.text(), resp.status, resp.reason)
                raise RuntimeError('Could not delete map on ddnet.org')

            log.info('Successfully deleted map %r on ddnet.org', filename)

    async def upload_submission(self, subm: Submission):
        try:
            await self.ddnet_upload('map', await subm.buffer(), str(subm))
        except RuntimeError:
            await subm.set_state(SubmissionState.ERROR)
        else:
            await subm.set_state(SubmissionState.UPLOADED)
            await subm.pin()

    async def validate_submission(self, isubm: InitialSubmission):
        try:
            isubm.validate()

            exists = self.get_map_channel(name=isubm.name)
            if exists:
                raise ValueError('A channel for this map already exists')

            query = 'SELECT TRUE FROM stats_maps_static WHERE name = $1;'
            released = await self.bot.pool.fetchrow(query, isubm.name)
            if released:
                raise ValueError('A map with that name is already released')
        except ValueError as exc:
            await isubm.respond(exc)
            await isubm.set_state(SubmissionState.ERROR)
        else:
            await isubm.set_state(SubmissionState.VALIDATED)

    @commands.Cog.listener('on_message')
    async def handle_submission(self, message: discord.Message):
        author = message.author
        if not has_map(message):
            return

        channel = message.channel
        if channel.id == CHAN_SUBMIT_MAPS:
            isubm = InitialSubmission(message)
            await self.validate_submission(isubm)

        else:
            map_channel = self.get_map_channel(channel.id)
            if map_channel is None:
                return

            subm = Submission(message)
            if map_channel.filename == str(subm):
                by_mapper = str(author.id) in map_channel.mapper_mentions
                if by_mapper and map_channel.state in (MapState.WAITING, MapState.READY):
                    await map_channel.set_state(state=MapState.TESTING)

                if by_mapper or is_staff(author) or author == self.bot.user:
                    await self.upload_submission(subm)
                else:
                    await subm.set_state(SubmissionState.VALIDATED)
                debug_output = await subm.debug_map()
                if debug_output:
                    if len(debug_output) + 6 < 2000:
                        await message.reply("```" + debug_output + "```", mention_author=False)
                    else:
                        file = discord.File(io.StringIO(debug_output), filename="debug_output.txt")
                        await message.reply("Error log in the attached file", file=file, mention_author=False)
                else:
                    await subm.message.add_reaction("👌")


    @commands.Cog.listener('on_raw_message_edit')
    async def handle_submission_edit(self, payload: discord.RawMessageUpdateEvent):
        # have to work with the raw data here to avoid unnecessary api calls
        data = payload.data
        if 'author' in data and int(data['author']['id']) == self.bot.user.id:
            return

        if payload.channel_id != CHAN_SUBMIT_MAPS:
            return

        if not ('attachments' in data and data['attachments'] and data['attachments'][0]['filename'].endswith('.map')):
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
        if not is_staff(user):
            return

        message = self.bot.get_message(payload.message_id) or await channel.fetch_message(payload.message_id)
        if not has_map(message):
            return

        if initial:
            if message.id in self._active_submissions:
                return

            isubm = InitialSubmission(message)
            try:
                isubm.validate()
            except ValueError:
                return

            self._active_submissions.add(message.id)
            subm = await isubm.process()
            await isubm.set_state(SubmissionState.PROCESSED)
            self._map_channels[isubm.map_channel.id] = isubm.map_channel
            self._active_submissions.discard(message.id)

        else:
            subm = Submission(message)
            debug_output = await subm.debug_map()
            if debug_output:
                if len(debug_output) + 6 < 2000:
                    await message.reply("```" + debug_output + "```", mention_author=False)
                else:
                    file = discord.File(io.StringIO(debug_output), filename="debug_output.txt")
                    await message.reply("Error log in the attached file", file=file, mention_author=False)
            else:
                await subm.message.add_reaction("👌")

        await self.upload_submission(subm)
        log.info('%s approved submission %r in channel #%s', user, subm.filename, channel)

    @commands.Cog.listener('on_message')
    async def handle_unwanted_message(self, message: discord.Message):
        author = message.author
        channel = message.channel

        # system pin messages by ourself
        # messages without a map file by non staff in submit maps channel
        if (is_testing(channel) and message.type is discord.MessageType.pins_add and message.author.bot) \
            or (channel.id == CHAN_SUBMIT_MAPS and not has_map(message) and not is_staff(author)):
            await message.delete()

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

            map_channel = self.get_map_channel(filename=message.attachments[0].filename[:-4])
            if map_channel is None:
                if action == 'REACTION_ADD':
                    await message.remove_reaction(payload.emoji, member)
                return

            if map_channel.overwrites_for(member).read_messages:
                if action == 'REACTION_REMOVE':
                    await map_channel.set_permissions(member, overwrite=None)
            elif action == 'REACTION_ADD':
                await map_channel.set_permissions(member, read_messages=True)

    def get_map_channel_from_ann(self, content: str) -> Optional[MapChannel]:
        map_url_re = r'\[(?P<name>.+)\]\(<?https://ddnet\.org/(?:maps|mappreview)/\?map=.+?>?\)'
        match = re.search(map_url_re, content)
        return match and self.get_map_channel(name=match.group('name'))

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

        return not failed

    @tasks.loop(hours=1.0)
    async def auto_archive(self):
        now = datetime.utcnow()

        ann_channel = self.bot.get_channel(CHAN_ANNOUNCEMENTS)
        ann_history = await ann_channel.history(after=now - timedelta(days=3)).filter(by_releases_webhook).flatten()
        recent_releases = {self.get_map_channel_from_ann(m.content) for m in ann_history}

        query = 'SELECT channel_id FROM waiting_maps WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL \'60 days\';'
        records = await self.bot.pool.fetch(query)
        deleted_waiting_maps_ids = [r['channel_id'] for r in records]

        to_archive = []
        for map_channel in self.map_channels:
            # keep the channel until its map is released, including a short grace period
            if map_channel.state in (MapState.TESTING, MapState.READY) or map_channel in recent_releases:
                continue

            # don't tele waiting maps before 60 days have passed
            if map_channel.state is MapState.WAITING and map_channel.id not in deleted_waiting_maps_ids:
                continue

            # make sure there is no active discussion going on
            recent_message = await map_channel.history(limit=1, after=now - timedelta(days=5)).flatten()
            if recent_message:
                continue

            to_archive.append(map_channel)

        for map_channel in to_archive:
            testlog = await TestLog.from_map_channel(map_channel)
            archived = await self.archive_testlog(testlog)

            if archived:
                await map_channel.delete()
                log.info('Sucessfully auto-archived channel #%s', map_channel)
            else:
                log.error('Failed auto-archiving channel #%s', map_channel)

    @auto_archive.before_loop
    async def _before_loop(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        try:
            map_channel = self._map_channels.pop(channel.id)
        except KeyError:
            return

        query = 'DELETE FROM waiting_maps where channel_id = $1'
        await self.bot.pool.execute(query, map_channel.id)

        try:
            await self.ddnet_delete(map_channel.filename)
        except RuntimeError:
            return

    @commands.Cog.listener('on_message')
    async def handle_map_release(self, message: discord.Message):
        if not by_releases_webhook(message):
            return

        map_channel = self.get_map_channel_from_ann(message.content)
        if map_channel is None:
            return

        await map_channel.set_state(state=MapState.RELEASED)

    @commands.command()
    @tester_check()
    async def reset(self, ctx: commands.Context):
        """Reset a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.set_state(state=MapState.TESTING)

    @commands.command()
    @tester_check()
    async def waiting(self, ctx: commands.Context):
        """Set a map to waiting"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.set_state(state=MapState.WAITING)

        query = """INSERT INTO waiting_maps (channel_id) VALUES ($1)
                   ON CONFLICT (channel_id) DO UPDATE SET timestamp = CURRENT_TIMESTAMP;
                """
        await self.bot.pool.execute(query, map_channel.id)

    @commands.command()
    @tester_check()
    async def ready(self, ctx: commands.Context):
        """Ready a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.set_state(state=MapState.READY)

    @commands.command()
    @tester_check()
    async def decline(self, ctx: commands.Context):
        """Decline a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.set_state(state=MapState.DECLINED)

    @commands.command()
    @tester_check()
    async def released(self, ctx: commands.Context):
        """Mark a map as released"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.set_state(state=MapState.RELEASED)

    @commands.command()
    @tester_check()
    async def edit(self, ctx: commands.Context, *args: str):
        """Edits a map according to the passed arguments"""
        subm = None
        if has_map(ctx.message):
            subm = Submission(ctx.message)
        elif ctx.message.reference is not None:
            replied_msg = await ctx.fetch_message(ctx.message.reference.message_id)
            if has_map(replied_msg):
                subm = Submission(replied_msg)
        if subm is None:
            map_channel = self.get_map_channel(ctx.channel.id)
            if map_channel is None:
                return
            async for msg in ctx.history():
                if not has_map(msg):
                    continue
                by_mapper = str(msg.author.id) in map_channel.mapper_mentions
                if by_mapper or is_staff(msg.author) or msg.author.id == self.bot.user.id:
                    subm = Submission(msg)
                    break

        if subm is None:
            return
        stdout, file = await subm.edit_map(*args)
        if stdout:
            stdout = "```" + stdout + "```"
        await ctx.channel.send(stdout, file=file)

    @commands.command()
    @tester_check()
    async def optimize(self, ctx: commands.Context):
        """Shortcut for the `edit` command, passes the arguments `--remove-everything-unused` and `--shrink-layers`"""
        await self.edit(ctx, "--remove-everything-unused", "--shrink-tiles-layers")

    @commands.group()
    @tester_check()
    async def change(self, ctx: commands.Context):
        """Change details of a map"""
        pass

    @change.command(name='name')
    async def change_name(self, ctx: commands.Context, name: str):
        """Change the name of a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        old_filename = map_channel.filename
        await map_channel.update(name=name)

        try:
            await self.ddnet_delete(old_filename)
        except RuntimeError:
            pass

    @change.command(name='mappers')
    async def change_mappers(self, ctx: commands.Context, *mappers: str):
        """Change the mappers of a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        await map_channel.update(mappers=mappers)

    @change.command(name='server')
    async def change_server(self, ctx: commands.Context, server: str):
        """Change the server type of a map"""
        map_channel = self.get_map_channel(ctx.channel.id)
        try:
            await map_channel.update(server=server)
        except ValueError as exc:
            await ctx.send(exc)

    @commands.command()
    @testing_lead_check()
    async def add_tester(self, ctx: commands.Context, user: discord.Member):
        """Add Tester role to a user"""
        tester_role = ctx.guild.get_role(ROLE_TESTER)
        if tester_role in user.roles:
            return await ctx.send(f'{user.mention} is already a Tester')

        await user.add_roles(tester_role)

    @commands.command()
    @testing_lead_check()
    async def remove_tester(self, ctx: commands.Context, user: discord.Member):
        """Remove Tester role from a user"""
        tester_role = ctx.guild.get_role(ROLE_TESTER)
        if tester_role not in user.roles:
            return await ctx.send(f'{user.mention} isn\'t a Tester')

        await user.remove_roles(tester_role)

    @add_tester.error
    @remove_tester.error
    async def manage_tester_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Could not find that user')


def setup(bot: commands.Bot):
    bot.add_cog(MapTesting(bot))
