from datetime import datetime, timedelta
import re

from fuzzywuzzy import fuzz
import discord
from discord.ext import commands

from .utils import misc, testing

# DDNet guild IDs
GUILD_DDNET = 252358080522747904
CAT_MAP_TESTING = 449352010072850443
CAT_EVALUATED_MAPS = 462954029643989003
CHAN_TESTING_INFO = 455392314173554688
CHAN_SUBMIT_MAPS = 455392372663123989
CHAN_LOG = 364164149359411201
ROLE_ADMIN = 293495272892399616
ROLE_TESTER = 293543421426008064
ROLE_MRS = 437966495901941771
ROLE_TESTING = 455814387169755176
MSG_OPT = 458735654021627935

FILE_PATH = 'map_testing/map_files/{}.{}'


def is_staff(user: discord.Member):
    return any(r.id in [ROLE_ADMIN, ROLE_TESTER, ROLE_MRS] for r in user.roles)


def is_testing_channel(channel: discord.TextChannel):
    if not channel.category_id:
        return False

    return channel.category_id in [CAT_MAP_TESTING, CAT_EVALUATED_MAPS]


def has_map_file(message: discord.Message):
    if message.attachments and message.attachments[0].filename.endswith('.map'):
        return True

    return False


def map_details(server_types, message: discord.Message):
    regex = r'("|\'|`|``)(.+)\1 +by +(.+) +\[([a-zA-Z0-9\*: ]+)\]'
    m = re.search(regex, message.content)
    if not m:
        return None

    name = m.group(2)
    sanitized_name = misc.sanitize_channel_name(name)
    filename = misc.get_filename(message.attachments[0].filename)
    sanitized_filename = misc.sanitize_channel_name(filename)
    if sanitized_name != sanitized_filename:
        return None

    mapper = re.split(r', | & | and ', m.group(3))

    for server in server_types:
        if re.search(r'%s' % server['name'].lower(), m.group(4).lower()):
            return name, mapper, (server['name'], server['emoji'])


def is_duplicate(name, message: discord.Message):
    sanitized_name = misc.sanitize_channel_name(name)
    evaluated_maps = misc.get(message.guild.categories, CAT_EVALUATED_MAPS)
    testing_chans = [*message.channel.category.channels, *evaluated_maps.channels]
    duplicate = discord.utils.find(lambda t: sanitized_name in [t.name[1:], t.name[2:]], testing_chans)
    return True if duplicate else False


class TestingMain:
    def __init__(self, bot):
        self.bot = bot
        self.criteria = testing.get_criteria()['criteria']
        self.criteria_total = sum([m['max'] for m in self.criteria.values()])
        self.criteria_total_required = testing.get_criteria()['general']['required']
        self.server_types = testing.get_server_types()

    async def status_emoji(self, message: discord.Emoji, emoji: str):
        if emoji not in message.reactions:
            await message.clear_reactions()
            await message.add_reaction(emoji)

    async def on_message(self, message):
        user = message.author
        channel = message.channel

        if not message.guild or message.guild.id != GUILD_DDNET:
            return

        if user == self.bot.user:
            if message.type == discord.MessageType.pins_add:
                return await message.delete()

            return

        if is_testing_channel(channel) and has_map_file(message):
            map_file = message.attachments[0]
            await map_file.save(FILE_PATH.format(map_file.id, 'map'))

            if channel.id == CHAN_SUBMIT_MAPS:
                details = map_details(self.server_types, message)
                if not details:
                    await self.status_emoji(message, '❓')
                    msg = f'Hey, your map submission in <#{CHAN_SUBMIT_MAPS}> doesn\'t cointain ' \
                          'correctly formated details about the map. ' \
                          'Please, edit the message to include the map\'s details ' \
                          'as follows: `"<map-name>" by <mappers> [<server-type>]`'
                    return await user.send(msg)

                if is_duplicate(details[0], message):
                    return await self.status_emoji(message, '❗')

            else:
                await message.pin()

            return await self.status_emoji(message, '☑')

        if channel.id == CHAN_SUBMIT_MAPS and not is_staff(user):
            await message.delete()

            msg = f'Hey, your message in <#{CHAN_SUBMIT_MAPS}> was deleted because it wasn\'t a map submission. ' \
                  'If you want to discuss a map, please do so in its individual channel <:happy:395753933089406976>'

            history = await user.history(after=message.created_at - timedelta(days=1)).flatten()
            recent_messages = [m.content for m in history]
            if msg not in recent_messages:
                return await user.send(msg)

    async def on_raw_message_edit(self, payload):
        if 'guild_id' not in payload.data or int(payload.data['guild_id']) != GUILD_DDNET:
            return

        channel = self.bot.get_channel(int(payload.data['channel_id']))
        message = await channel.get_message(payload.message_id)
        if channel.id == CHAN_SUBMIT_MAPS:
            if not payload.data['attachments']:
                return

            if not any(str(r.emoji) in ['❗', '❓'] for r in message.reactions):
                return

            details = map_details(self.server_types, message)
            if not details:
                return

            if is_duplicate(details[0], message):
                return

            return await self.status_emoji(message, '☑')

        if not channel.category_id or channel.category_id != CAT_MAP_TESTING:
            return

        if not message.content.startswith('$rate '):
            return

        if not misc.get(message.author.roles, ROLE_MRS) or not misc.get(message.author.roles, ROLE_ADMIN):
            return

        submission = message.content.replace('$rate ', '').split()
        submission = testing.format_submission(self.criteria, submission)
        ok_hands = ['👌', '👌🏻', '👌🏼', '👌🏽', '👌🏾', '👌🏿']
        if isinstance(submission, str):
            for r in message.reactions:
                if r.me and str(r.emoji) in ok_hands:
                    await message.remove_reaction(r.emoji, self.bot.user)
                    break

            return await message.add_reaction('❌')

        testing.submit_ratings(submission, channel.id, message.author.id)
        mrs = misc.get(message.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        ratings, rater_count = testing.get_ratings(self.criteria, channel.id, mrs_ids)
        schedule_pos = testing.get_schedule_pos(channel.id)
        topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
        await channel.edit(topic=topic)

        for r in message.reactions:
            if not r.me:
                continue

            await message.remove_reaction(r.emoji, self.bot.user)
            if str(r.emoji) in ok_hands:
                index = ok_hands.index(r.emoji) + 1
                break

        else:
            index = 0

        await message.add_reaction(ok_hands[index if index <= 5 else 5])
        await message.pin()

        if not None in ratings and channel.topic[0] != '⭐':
            self.add_job(ratings, rater_count, channel)

    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.guild_id != GUILD_DDNET:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not is_testing_channel(channel):
            return

        message = await channel.get_message(payload.message_id)
        user = message.guild.get_member(payload.user_id)
        if not user or user.bot:
            return

        if not has_map_file(message):
            return

        if str(payload.emoji) != '☑':
            return

        if not is_staff(user):
            return

        map_file = message.attachments[0]

        if channel.id == CHAN_SUBMIT_MAPS:
            map_name, mapper, server_type = map_details(self.server_types, message)

            if not server_type:
                return await self.status_emoji(message, '❓')

            if is_duplicate(map_name, message):
                return await self.status_emoji(message, '❗')

            await self.status_emoji(message, '🔄')

            role_tester = misc.get(message.guild.roles, ROLE_TESTER)
            role_mrs = misc.get(message.guild.roles, ROLE_MRS)
            role_testing = misc.get(message.guild.roles, ROLE_TESTING)
            perms_staff = discord.PermissionOverwrite(read_messages=False, manage_messages=True)
            perms_default = discord.PermissionOverwrite(read_messages=False)

            overwrites = {
                message.guild.default_role: perms_default,
                role_tester: perms_staff,
                role_mrs: perms_staff,
                role_testing: perms_default,
                message.author: perms_default
            }

            msg = f'{message.author.mention}\n\n**"{map_name}"** by '
            for n, m in enumerate(mapper):
                if n > 0:
                    if n == len(mapper) - 1:
                        msg += ' & '
                    else:
                        msg += ', '

                msg += f'**{m}**'

                users = [u for u in message.guild.members if u.display_name == m]
                for u in users:
                    overwrites[u] = perms_default

            map_channel_name = f'{server_type[1]}{map_file.filename.replace(".map", "")}'
            map_channel = await message.guild.create_text_channel(name=map_channel_name, overwrites=overwrites,
                                                                  category=message.channel.category)
            map_message_file = discord.File(fp=FILE_PATH.format(map_file.id, 'map'), filename=map_file.filename)
            map_message = await map_channel.send(content=msg, file=map_message_file)
            await map_message.pin()
            await map_file.save(FILE_PATH.format(map_file.id, 'map'))

            try:
                await misc.render_thumbnail(FILE_PATH.format(map_file.id, 'map'))
                await map_channel.send(file=discord.File(FILE_PATH.format(map_file.id, 'map.png'),
                                                         filename=map_file.filename.replace('.map', '.png')))
            except:
                pass

            for t, p in map_channel.overwrites:
                if t == message.guild.default_role:
                    continue
                p.read_messages = True
                await map_channel.set_permissions(t, overwrite=p)

            testing.update_schedule('add', map_channel.id, map_channel.created_at)
            schedule_pos = testing.get_schedule_pos(map_channel.id)
            if server_type[0] in ['Oldschool', 'DDmaX']:
                topic = testing.update_ratings_prompt(None, None, None, schedule_pos)

            else:
                ratings = [None] * len(self.criteria)
                topic = testing.update_ratings_prompt(self.criteria, ratings, 0, schedule_pos)

            await map_channel.edit(topic=topic)

            await self.status_emoji(message, '✅')
            message = map_message

        await self.status_emoji(message, '🔄')
        r = testing.upload_map(map_file.filename.replace(".map", ""), FILE_PATH.format(map_file.id, 'map'))

        desc = f'**``{map_file.filename}`` approved by <@{user.id}>**\n' \
               f'[Map file: {map_file.filename} ({"".join(misc.format_size(map_file.size))})]({map_file.url})'
        embed = discord.Embed(description=desc, color=0x77B255, timestamp=datetime.utcnow())
        embed.set_author(name=f'{user} | {map_file.id}', icon_url=user.avatar_url_as(format='png'))
        log_channel = self.bot.get_channel(CHAN_LOG)
        await log_channel.send(embed=embed)

        if r != 200:
            print(r)
            return await self.status_emoji(message, '❌')

        return await self.status_emoji(message, '🆙')

    @commands.command(pass_context=True)
    @commands.has_any_role('Admin', 'Map Release Squad')
    async def rate(self, ctx, *submission):
        user = ctx.message.author
        channel = ctx.channel
        message = ctx.message

        if not ctx.guild or ctx.guild.id != GUILD_DDNET:
            return

        if not channel.category_id or channel.category_id != CAT_MAP_TESTING:
            return

        submission = testing.format_submission(self.criteria, submission)
        if isinstance(submission, str):
            await message.add_reaction('❌')
            return await channel.send(content=submission, delete_after=15)

        testing.submit_ratings(submission, channel.id, user.id)
        mrs = misc.get(ctx.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        ratings, rater_count = testing.get_ratings(self.criteria, channel.id, mrs_ids)
        schedule_pos = testing.get_schedule_pos(channel.id)
        topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
        await channel.edit(topic=topic)
        await message.add_reaction('👌')
        await message.pin()

        if not None in ratings and schedule_pos > 2:
            self.add_job(ratings, rater_count, channel)

    @commands.command(pass_context=True)
    async def refresh_all(self, ctx):
        guild = self.bot.get_guild(GUILD_DDNET)
        map_testing = discord.utils.get(guild.categories, id=CAT_MAP_TESTING)
        mrs = misc.get(guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]

        self.criteria = testing.get_criteria()['criteria']
        self.criteria_total = sum([m['max'] for m in self.criteria.values()])
        self.criteria_total_required = testing.get_criteria()['general']['required']
        self.server_types = testing.get_server_types()

        for c in map_testing.channels:
            if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                continue

            ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
            schedule_pos = testing.get_schedule_pos(c.id)
            topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
            await c.edit(topic=topic)
            # if not None in ratings and c.topic[0] != '⭐':
            # self.add_job(ratings, rater_count, c)
            # await ctx.send(f'{c.name}: process')

    def add_job(self, ratings, rater_count, channel: discord.TextChannel = None):
        criteria_required = [t['required'] for t in self.criteria.values()]

        pos_cond_1_check = [True for r, t in zip(ratings, criteria_required) if t and r >= t + 2]
        pos_cond_1 = True if pos_cond_1_check.count(
            True) >= 2 else False  # 2 or more scores greater than or equal to required score + 2
        pos_cond_2 = all(r >= t + 1 for r, t in zip(ratings, criteria_required) if
                         t)  # All scores greater than or equal to required score + 1

        neg_cond_1 = any(r <= t - 3 for r, t in zip(ratings, criteria_required) if
                         t)  # 1 or more scores less than or equal to required score - 3
        neg_cond_2_check = [True for r, t in zip(ratings, criteria_required) if t and r <= t - 2]
        neg_cond_2 = True if neg_cond_2_check.count(
            True) >= 2 else False  # 2 or more scores less than or equal to required score - 2
        neg_cond_3 = any(r <= t - 2 for r, t in zip(ratings, criteria_required) if
                         t)  # 1 or more scores less than or equal to required score - 2
        neg_cond_4_check = [True for r, t in zip(ratings, criteria_required) if t and r <= t - 1]
        neg_cond_4 = True if neg_cond_4_check.count(
            True) >= 2 else False  # 2 or more scores less than or equal to required score - 1

        if ((rater_count >= 3 and sum(ratings) >= self.criteria_total_required + 10 and pos_cond_1 and pos_cond_2) or
                (rater_count >= 4 and sum(ratings) >= self.criteria_total_required + 5 and pos_cond_2) or
                (rater_count >= 2 and sum(ratings) <= self.criteria_total_required - 10 and (
                        neg_cond_1 or neg_cond_2)) or
                (rater_count >= 3 and sum(ratings) <= self.criteria_total_required - 5 and (neg_cond_3 or neg_cond_4))):

            if channel:
                if datetime.utcnow() < (channel.created_at + timedelta(days=6)):
                    date = channel.created_at + timedelta(weeks=1)
                else:
                    date = datetime.utcnow() + timedelta(days=1)

            date = date.replace(minute=0, second=0, microsecond=0)
            testing.update_schedule_process(channel.id, date)

        else:
            testing.update_schedule_process(channel.id)

    @commands.command(pass_context=True)
    async def ratings(self, ctx, channel=None):
        def output_string(criterion, rating):
            status_emoji = '✅' if rating else '❌'
            if not rating:
                rating = 0
            crit_max = self.criteria[criterion]['max']
            right_align = max(map(len, self.criteria)) - len(criterion)
            string = '{}`{}' + '.' * right_align + ':` **{}**/{}\n'
            return string.format(status_emoji, criterion.capitalize(), rating, crit_max)

        if ctx.message.guild:
            return

        await ctx.trigger_typing()
        guild = self.bot.get_guild(GUILD_DDNET)
        user = ctx.message.author
        map_testing = misc.get(guild.categories, CAT_MAP_TESTING)
        evaluated_maps = misc.get(guild.categories, CAT_EVALUATED_MAPS)
        testing_chans = [*map_testing.channels, *evaluated_maps.channels]
        content = ''

        if channel:
            match = re.search(r'^<#([0-9]+)>$', channel)
            if match:
                channel = self.bot.get_channel(int(match.group(1)))
                if not channel:
                    return await ctx.send('Channel not found')

                if channel not in testing_chans:
                    return await ctx.send(f'{channel.mention} is not a map channel')

            else:
                channel_name = channel.replace('#', '').lower()

                names = []
                for c in testing_chans:
                    if channel_name in [c.name, c.name[1:]]:
                        channel = c
                        break

                    if sorted(channel_name) == sorted(c.name) or sorted(channel_name) == sorted(c.name[1:]):
                        names.append(f'- {c.mention}')
                        continue

                    ratio = fuzz.ratio(channel_name, c.name[1:])
                    ratio_2 = fuzz.ratio(channel_name, c.name[1:])
                    if ratio >= 70 or ratio_2 >= 70:
                        names.append(f'- {c.mention}')

                else:
                    msg = 'Channel not found'
                    if names:
                        msg += '. Did you mean..\n' + '\n'.join(names)
                    return await ctx.send(msg)

            for server in self.server_types:
                if channel.name[0] == server['emoji']:
                    if server['name'] == 'DDmaX':
                        return await ctx.send(f'{channel.mention} is a DDmaX map channel')

                    if server['name'] == 'Oldschool':
                        return await ctx.send(f'{channel.mention} is an Oldschool map channel')

            if channel.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                return await ctx.send(f'{channel.mention} is not a map channel')

            title = f'{user} | #{channel.name}'
            ratings = testing.get_ratings(self.criteria, channel.id, user.id)
            if ratings:
                status_emoji = '❕' if None in ratings else '✅'
            else:
                status_emoji = '❌'
                ratings = [None] * len(self.criteria)

            for c, r in zip(self.criteria, ratings):
                content += output_string(c, r)

            content += '**--------------------------------**\n'
            ratings_total = sum(filter(None, ratings))
            right_align = len(max(self.criteria)) - len('Overall')
            content += f'{status_emoji} `Overall' + '.' * right_align + f':` **{ratings_total}**/{self.criteria_total}'

        else:
            msg_new = '**---------------- New maps ----------------**\n'
            msg_week = '**------------ Older than 1 week -----------**\n'
            msg_month = '**----------- Older than 1 month -----------**\n'
            testing_schedule = testing.get_full_schedule()

            for n, s in enumerate(testing_schedule):
                channel = self.bot.get_channel(s[0])

                for server in self.server_types:
                    if channel.name[0] == server['emoji']:
                        if server['name'] == 'DDmaX':
                            status_emoji = self.server_types['DDmaX']
                            break

                        if server['name'] == 'Oldschool':
                            status_emoji = self.server_types['Oldschool']
                            break

                else:
                    ratings = testing.get_ratings(self.criteria, channel.id, user.id)
                    if ratings:
                        status_emoji = '❕' if None in ratings else '✅'
                    else:
                        status_emoji = '❌'

                week_ago = datetime.utcnow() - timedelta(days=7)
                month_ago = datetime.utcnow() - timedelta(weeks=4)

                if s[1] >= week_ago and msg_new not in content:
                    content += msg_new

                if week_ago >= s[1] >= month_ago and msg_week not in content:
                    content += msg_week

                if s[1] <= month_ago and msg_month not in content:
                    content += msg_month

                pos = f'`#0{n + 1}`' if n < 9 else f'`#{n + 1}`'
                content += f'{pos} {status_emoji} {channel.mention}\n'

            title = user

        embed = discord.Embed(description=content)
        embed.set_author(name=title, icon_url=user.avatar_url_as(format='png'))
        await ctx.send(embed=embed)

    async def on_guild_channel_delete(self, channel):
        if channel.guild.id != GUILD_DDNET:
            return

        if not channel.category_id or channel.category_id != CAT_MAP_TESTING:
            return

        mrs = misc.get(channel.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]

        for c in channel.category.channels:
            if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                continue

            ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
            schedule_pos = testing.get_schedule_pos(c.id)
            topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
            await c.edit(topic=topic)

    async def on_guild_channel_update(self, before, after):
        if before.guild.id != GUILD_DDNET:
            return

        if not before.category_id or not after.category_id:
            return

        if not (before.category_id == CAT_MAP_TESTING and after.category_id == CAT_EVALUATED_MAPS):
            return

        if not (before.category_id == CAT_EVALUATED_MAPS and after.category_id == CAT_MAP_TESTING):
            return

        map_testing = misc.get(before.guild.categories, CAT_MAP_TESTING)
        mrs = misc.get(before.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]

        for c in map_testing.channels:
            if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                continue
            try:
                ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
                schedule_pos = testing.get_schedule_pos(c.id)
                topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
                await before.edit(topic=topic)
            except:
                pass


def setup(bot):
    bot.add_cog(TestingMain(bot))
