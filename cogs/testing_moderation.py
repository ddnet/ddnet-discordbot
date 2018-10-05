import asyncio
from datetime import datetime, timedelta
import re

import requests
import discord
from discord.ext import commands

from cogs.utils import misc, testing

#DDNet guild IDs
GUILD_DDNET = 252358080522747904
CAT_MAP_TESTING = 449352010072850443
CAT_EVALUATED_MAPS = 462954029643989003
CHAN_ANNOUNCEMENTS = 420565311863914496
CHAN_MRS = 437967315557023745
CHAN_TESTING_INFO = 455392314173554688
CHAN_SUBMIT_MAPS = 455392372663123989
ROLE_ADMIN = 293495272892399616
ROLE_TESTER = 293543421426008064
ROLE_MRS = 437966495901941771
ROLE_TESTING = 455814387169755176
MSG_OPT = 458735654021627935
MSG_MRS_EMBED = 459473712341712906
MSG_UNSCHD_EMBED = 497484373902360576

def has_map_file(message: discord.Message):
    if message.attachments and misc.get_extension(message.attachments[0].filename) == '.map':
        return True

    return False

class TestingModeration:
    def __init__(self, bot):
        self.bot = bot
        self.criteria = testing.get_criteria()['criteria']
        self.criteria_total = sum([m['max'] for m in self.criteria.values()])
        self.criteria_total_required = testing.get_criteria()['general']['required']
        self.server_types = testing.get_server_types()

    async def on_ready(self):
        await self.run_jobs()

    async def run_jobs(self):
        while not self.bot.is_closed():
            now = datetime.utcnow()
            now = now.replace(minute=0, second=0, microsecond=0)
            weekday = now.weekday()
            hour = now.hour

            channel_ids = testing.get_process(now)
            if channel_ids:
                await self.process_scheduled_maps(channel_ids)

            #if weekday == 0 and hour == 10:
                #testing_schedule = testing.get_schedule()
                #await self.process_scheduled_maps(testing_schedule[:3])
                #await self.announce_schedule()

            #if weekday == 4 and hour == 10:
                #await self.reminder()

            await asyncio.sleep(3600)

    async def approve_map(self, channel_id):
        channel = self.bot.get_channel(channel_id)
        name = f'✅{channel.name}'
        mrs = misc.get(channel.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        ratings, rater_count = testing.get_ratings(self.criteria, channel.id, mrs_ids)
        topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, -1)

        evaluated_maps = discord.utils.get(channel.guild.categories, id=CAT_EVALUATED_MAPS)

        await channel.edit(name=name, topic=topic, position=0, category=evaluated_maps)

        msg = 'The map scored **all required points**! It only needs to be checked by a ' \
             f'<@&{ROLE_TESTER}> now to be released <:happy:395753933089406976>'
        await channel.send(msg)

    async def decline_map(self, channel_id, reasons=None):
        channel = self.bot.get_channel(channel_id)
        name = f'❌{channel.name}'
        mrs = misc.get(channel.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        ratings, rater_count = testing.get_ratings(self.criteria, channel.id, mrs_ids)
        topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, -1)

        evaluated_maps = discord.utils.get(channel.guild.categories, id=CAT_EVALUATED_MAPS)
        first_declined = discord.utils.find(lambda c: c.name[0] == '❌', evaluated_maps.channels)
        if first_declined:
            pos = first_declined.position - 1
        else:
            if evaluated_maps.channels:
                pos = evaluated_maps.channels[len(evaluated_maps.channels)].position
            else:
                pos = 0

        await channel.edit(name=name, topic=topic, position=pos, category=evaluated_maps)

        if not reasons:
            return

        msg = 'The map didn\'t reach sufficient ratings '

        if reasons['criteria']:
            msg += 'in '
            for n, r in enumerate(reasons['criteria']):
                if n > 0:
                    if n == len(reasons['criteria']) - 1:
                        msg += ' and '
                    else:
                        msg += ', '

                msg += f'**{r}** ({self.criteria[r]["required"]} required)'

            if reasons['total']:
                msg += ' as well as '

        if reasons['total']:
            msg += f'**overall** ({self.criteria_total_required} required)'

        msg += ' and, therefore, won\'t be released. However, feel free to rework it to improve ' \
            'low rated criteria, or simply start a new map <:heartw:395753947396046850>'

        await channel.send(msg)

    async def on_message(self, message):
        if not message.guild or message.guild.id != GUILD_DDNET:
            return

        if message.channel.id != CHAN_ANNOUNCEMENTS:
            return

        regex = r'New map \[(.+)\]\(.+\) by \[.+\]\(.+\) released on \[.+\]\(.+\)'
        m = re.search(regex, message.content)
        if not m:
            return

        channel_name = misc.sanitize_channel_name(m.group(1))
        evaluated_maps = discord.utils.get(message.guild.channels, id=CAT_EVALUATED_MAPS)
        channel = discord.utils.find(lambda c: channel_name == c.name[2:], evaluated_maps.channels)
        if not channel:
            return

        await channel.edit(name='🔥' + channel.name[1:])

    async def process_scheduled_maps(self, channel_ids):
        guild = self.bot.get_guild(GUILD_DDNET)
        criteria_required = [t['required'] for t in self.criteria.values()]
        mrs = discord.utils.get(guild.roles, id=ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]

        for c_id in channel_ids:
            ratings = testing.get_ratings(self.criteria, c_id, mrs_ids)[0]
            #Maps should only be processed if every criteria has been evaluated
            if None in ratings:
                continue

            if (sum(ratings) >= self.criteria_total_required and
                all(r >= t for r, t in zip(ratings, criteria_required) if t)):
                await self.approve_map(c_id)

            else:
                reasons = {
                    'total': True if sum(ratings) < self.criteria_total_required else False,
                    'criteria': [c for r, c, t in zip(ratings, self.criteria, criteria_required) if t and r < t]
                }

                await self.decline_map(c_id, reasons)

    async def announce_schedule(self):
        testing_schedule = testing.get_schedule()[:3]
        testing_schedule = [f'- <#{c_id}>' for c_id in testing_schedule]
        msg = f'<@&{ROLE_MRS}> This week\'s maps to rate:\n' + '\n'.join(testing_schedule)
        guild = self.bot.get_guild(GUILD_DDNET)
        chan_mrs = misc.get(guild.channels, CHAN_MRS)
        await chan_mrs.send(msg)

    async def reminder(self):
        guild = self.bot.get_guild(GUILD_DDNET)
        mrs = discord.utils.get(guild.roles, id=ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        testing_schedule = testing.get_schedule()[:3]

        for m_id in mrs_ids:
            reminders = []
            for c_id in testing_schedule:
                channel = self.bot.get_channel(c_id)
                for server in self.server_types:
                    if channel.name[0] == server['emoji'] and server['name'] in ['DDmaX', 'Oldschool']:
                        continue

                ratings = testing.get_ratings(self.criteria, c_id, m_id)
                if not ratings:
                    reminders.append(channel.mention)

            if not reminders:
                continue

            msg = '**Reminder:** Don\'t forget to rate '
            for n, r in enumerate(reminders):
                if n > 0:
                    if n == len(reminders) - 1:
                        msg += ' and '
                    else:
                        msg += ', '

                msg += r

            msg += '! You have time to do so until Monday <:happy:395753933089406976>'
            user = self.bot.get_user(m_id)
            try: #Fails if the user has blocked the bot
                await user.send(msg)
            except discord.Forbidden(f'{user} has blocked the bot', msg):
                pass

    @commands.command(pass_context=True)
    @commands.has_any_role('Admin', 'Tester')
    async def ready(self, ctx, difficulty, map_name=None, mappers=None):
        def slugify2(name):
            x = '[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+'
            string = ''
            for c in name:
                if c in x or ord(c) >= 128:
                    string += f'-{ord(c)}-'
                else:
                    string += c

            return string

        def get_stars(difficulty):
            return '★' * difficulty + '☆' * max(5 - difficulty, 0)

        channel = ctx.channel
        message = ctx.message
        category = channel.category

        detail_msg = await channel.history(reverse=True).get(author=self.bot.user)
        match = re.search(r'\*\*"(.*)"\*\* by (.*)', detail_msg.content)
        if  match:
            map_name = match.group(1)
            mappers = match.group(2)

        if not map_name:
            await message.add_reaction('❌')
            return await channel.send('Map name not specified')

        if not mappers:
            await message.add_reaction('❌')
            return await channel.send('Mapper(s) not specified')

        mappers = re.split(r', | & ', mappers)

        for server in self.server_types:
            if server['emoji'] == channel.name[1]:
                server_type = server['name']

        details_string = f'**"{map_name}"** by '

        for n, m in enumerate(mappers):
            if n > 0:
                if n == len(mappers) - 1:
                    details_string += ' & '
                else:
                    details_string += ', '

            match = re.search(r'\*\*(.*)\*\*', m)
            if match:
                m = match.group(1)

            m_url = f'https://ddnet.tw/mappers/{slugify2(m)}/'
            details_string += f'[{m}]({m_url})' if requests.get(m_url).status_code == 200 else f'**{m}**'

        diff_string = f'({server_type} {get_stars(int(difficulty))})'

        if channel.name[0] != '📆':
            first_ready = discord.utils.find(lambda c: c.name[0] != '✅', category.channels)
            pos = first_ready.position - 1 if first_ready else category.channels[-1].position
            await channel.edit(name='📆' + channel.name[1:], position=pos)

        info_chan = self.bot.get_channel(CHAN_TESTING_INFO)
        async for msg in info_chan.history():
            if msg.embeds and msg.author == self.bot.user:
                embed_title = msg.embeds[0].title
                if embed_title == 'Not yet Scheduled':
                    break

                embed_desc = msg.embeds[0].description.split('\n')
                if re.search(r'\*\*"%s"\*\*' % map_name, embed_desc[1]):
                    embed_desc[1] = details_string
                    embed_desc[2] = diff_string
                    embed = discord.Embed(title=embed_title, description='\n'.join(embed_desc))
                    return await msg.edit(embed=embed)

        unschd_embed_msg = await info_chan.get_message(MSG_UNSCHD_EMBED)
        unschd_embed_desc = unschd_embed_msg.embeds[0].description.split('\n')
        for n, l in enumerate(unschd_embed_desc):
            match = re.search(r'\*\*"%s"\*\*' % map_name, l)
            if match:
                unschd_embed_desc[n] = details_string
                unschd_embed_desc[n + 1] = diff_string
                break

        else:
            unschd_embed_desc += [details_string, diff_string]

        unschd_embed = discord.Embed(title='Not yet Scheduled', description='\n'.join(unschd_embed_desc))
        await unschd_embed_msg.edit(embed=unschd_embed)

    @commands.command(pass_context=True)
    async def release(self, ctx, map_name, date):
        def suffix(d):
            return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')

        def custom_strftime(fmt, t):
            return t.strftime(fmt).replace('{S}', str(t.day) + suffix(t.day))

        ddnet_guild = self.bot.get_guild(GUILD_DDNET)
        ddnet_member = ddnet_guild.get_member(ctx.author.id)
        if not ddnet_member:
            return

        #Check role on DDNet guild since the command is expected to be executed in DMs
        if not any(r.id == ROLE_ADMIN for r in ddnet_member.roles):
            return

        message = ctx.message

        try:
            date = datetime.strptime(date, '%Y-%m-%d %H:%M')
            date_string = f'__{custom_strftime("%B {S}, %I:%M %p CEST", date)}__'
        except:
            await message.add_reaction('❌')
            return await ctx.send('Wrong date format. Correct usage: `YEAR-MONTH-DAY HOUR:MINUTES`')

        info_chan = self.bot.get_channel(CHAN_TESTING_INFO)
        async for msg in info_chan.history():
            if msg.embeds and msg.author == self.bot.user:
                embed_title = msg.embeds[0].title
                if embed_title == 'Not yet Scheduled':
                    break

                embed_desc = msg.embeds[0].description.split('\n')
                if re.search(r'\*\*"%s"\*\*' % map_name, embed_desc[1]):
                    embed_desc[0] = date_string
                    embed = discord.Embed(title=date.strftime('%A'), description='\n'.join(embed_desc), color=msg.embeds[0].color)
                    await msg.edit(embed=embed)
                    return await message.add_reaction('👌')

        unschd_embed_msg = await info_chan.get_message(MSG_UNSCHD_EMBED)
        unschd_embed_desc = unschd_embed_msg.embeds[0].description.split('\n')

        for n, l in enumerate(unschd_embed_desc):
            match = re.search(r'\*\*"%s"\*\*' % map_name, l)
            if match:
                details_string = l
                diff_string = unschd_embed_desc[n + 1]
                del unschd_embed_desc[n:n + 2]
                unschd_embed = discord.Embed(title='Not yet Scheduled', description='\n'.join(unschd_embed_desc))
                await unschd_embed_msg.edit(embed=unschd_embed)
                break

        match = re.search(r'([a-zA-Z]*) [★☆]*', diff_string)
        for server in self.server_types:
            if server['name'] == match.group(1):
                hex_int = int(server['color'], 16)
                new_int = hex_int + 0x200
                color = hex(new_int)

        rls_embed_desc = [date_string, details_string, diff_string]
        rls_embed = discord.Embed(title=date.strftime('%A'), description='\n'.join(rls_embed_desc), color=color)
        await info_chan.send(embed=rls_embed)
        await message.add_reaction('👌')


    @commands.command(pass_context=True)
    @commands.has_any_role('Admin', 'Tester')
    async def decline(self, ctx):
        if ctx.guild.id != GUILD_DDNET:
            return

        await self.decline_map(ctx.channel.id)

    @commands.command(pass_context=True)
    @commands.has_any_role('Admin', 'Tester')
    async def waiting(self, ctx):
        if ctx.guild.id != GUILD_DDNET:
            return

        channel = ctx.channel
        name = f'🕒{channel.name}'
        mrs = misc.get(ctx.guild.roles, ROLE_MRS)
        mrs_ids = [m.id for m in mrs.members]
        ratings, rater_count = testing.get_ratings(self.criteria, channel.id, mrs_ids)
        topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, -1)

        evaluated_maps = discord.utils.get(channel.guild.categories, id=CAT_EVALUATED_MAPS)
        first_declined = discord.utils.find(lambda c: c.name[0] in ['🕒', '❌'], evaluated_maps.channels)
        if first_declined:
            pos = first_declined.position - 1
        else:
            if evaluated_maps.channels:
                pos = evaluated_maps.channels[-1].position
            else:
                pos = 0

        await channel.edit(name=name, topic=topic, position=pos, category=evaluated_maps)

    async def on_member_update(self, before, after):
        if before == self.bot.user:
            return

        if not before.guild or before.guild.id != GUILD_DDNET:
            return

        roles_ids = [r.id for r in [*before.roles, *after.roles]]
        if roles_ids.count(ROLE_MRS) != 1:                                                                                      #Check if MRS role was added or removed
            return

        info_channel = self.bot.get_channel(CHAN_TESTING_INFO)
        embed_message = await info_channel.get_message(MSG_MRS_EMBED)
        embed = discord.Embed(title='Map Release Squad', description='\255', color=0xEB4444, timestamp=datetime.utcnow())      #ASCII code 255 represents a non-breaking space (empty character)
        embed.set_footer(text="Last Updated")

        mrs = discord.utils.get(before.guild.roles, id=ROLE_MRS)
        mrs_members = sorted(mrs.members, key=lambda x: x.display_name.lower())                                                 #Sort MRS members case-insensitive based on `display_name`
        mrs_members = [[m.mention for m in mrs_members][x:x + 5] for x in range(0, len(mrs_members), 5)]                        #Split list every 5 members
        for f in mrs_members:
            embed.add_field(name='\255', value='\n'.join(f), inline=True)

        await embed_message.edit(embed=embed)

        mrs_ids = [m.id for m in mrs.members]
        map_testing = discord.utils.get(before.guild.categories, id=CAT_MAP_TESTING)
        for c in map_testing.channels:
            if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                continue

            for server in self.server_types:
                if c.name[0] == server['emoji'] and server['name'] in ['DDmaX', 'Oldschool']:
                    continue

            ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
            schedule_pos = testing.get_schedule_pos(c.id)
            topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
            await c.edit(topic=topic)

    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id or payload.guild_id != GUILD_DDNET:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel.id not in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
            return

        message = await channel.get_message(payload.message_id)
        guild = message.guild
        user = guild.get_member(payload.user_id)
        if not user or user.bot:
            return

        if str(payload.emoji) != '✅':
            return await message.remove_reaction(payload.emoji, user)

        if message.id == MSG_OPT:
            return await user.add_roles(discord.Object(id=ROLE_TESTING))

        if not has_map_file(message):
            return await message.remove_reaction(payload.emoji, user)

        filename = misc.get_filename(message.attachments[0].filename)
        sanitized_name = misc.sanitize_channel_name(filename)
        evaluated_maps = discord.utils.get(guild.categories, id=CAT_EVALUATED_MAPS)
        testing_chans = [*message.channel.category.channels, *evaluated_maps.channels]
        map_channel = discord.utils.find(lambda c: sanitized_name in c.name, testing_chans)

        if map_channel:
            await map_channel.set_permissions(user, read_messages=True)

    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id or payload.guild_id != GUILD_DDNET:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel.id not in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
            return

        message = await channel.get_message(payload.message_id)
        guild = message.guild
        user = guild.get_member(payload.user_id)
        if not user or user.bot:
            return

        if str(payload.emoji) != '✅':
            return

        if message.id == MSG_OPT:
            await user.remove_roles(discord.Object(id=ROLE_TESTING))

        if not has_map_file(message):
            return

        filename = misc.get_filename(message.attachments[0].filename)
        sanitized_name = misc.sanitize_channel_name(filename)
        evaluated_maps = discord.utils.get(guild.categories, id=CAT_EVALUATED_MAPS)
        testing_chans = [*message.channel.category.channels, *evaluated_maps.channels]
        map_channel = discord.utils.find(lambda c: sanitized_name in c.name, testing_chans)

        if map_channel:
            await map_channel.set_permissions(user, overwrite=None)

    async def on_guild_channel_delete(self, channel):
        if channel.guild.id != GUILD_DDNET:
            return

        if not channel.category_id or channel.category_id != CAT_MAP_TESTING:
            return

        testing.update_schedule('remove', channel.id)

    async def on_guild_channel_update(self, before, after):
        if before.guild.id != GUILD_DDNET:
            return

        if not before.category_id or not after.category_id:
            return

        if before.category_id == CAT_MAP_TESTING and after.category_id == CAT_EVALUATED_MAPS:
            testing.update_schedule('remove', before.id)

            mrs = misc.get(before.guild.roles, ROLE_MRS)
            mrs_ids = [m.id for m in mrs.members]
            for c in before.category.channels:
                if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                    continue

                ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
                schedule_pos = testing.get_schedule_pos(c.id)
                topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
                await c.edit(topic=topic)

        if before.category_id == CAT_EVALUATED_MAPS and after.category_id == CAT_MAP_TESTING:
            now = datetime.utcnow()
            weeks_ago = now - timedelta(weeks=2)
            date = now if before.created_at >= weeks_ago else before.created_at
            testing.update_schedule('add', before.id, date)

            mrs = misc.get(before.guild.roles, ROLE_MRS)
            mrs_ids = [m.id for m in mrs.members]
            for c in after.category.channels:
                if c.id in [CHAN_TESTING_INFO, CHAN_SUBMIT_MAPS]:
                    continue

                ratings, rater_count = testing.get_ratings(self.criteria, c.id, mrs_ids)
                schedule_pos = testing.get_schedule_pos(c.id)
                topic = testing.update_ratings_prompt(self.criteria, ratings, rater_count, schedule_pos)
                await c.edit(topic=topic)

def setup(bot):
    bot.add_cog(TestingModeration(bot))
