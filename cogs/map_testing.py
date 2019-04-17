import re
from datetime import datetime
from io import BytesIO
from sys import platform

import discord
from discord.ext import commands

from utils.misc import humanize_list, sanitize, shell

DIR = 'data/map-testing'

SERVER_TYPES = {
    'Novice':       '👶',
    'Moderate':     '🌸',
    'Brutal':       '💪',
    'Insane':       '💀',
    'Dummy':        '♿',
    'Oldschool':    '👴',
    'Solo':         '⚡',
    'Race':         '🏁',
}


class MapTesting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild = self.bot.guild


    @property
    def mt_cat(self):
        return discord.utils.get(self.guild.categories, name='Map Testing')


    @property
    def em_cat(self):
        return discord.utils.get(self.guild.categories, name='Evaluated Maps')

    @property
    def announce_chan(self):
        return discord.utils.get(self.guild.channels, name='announcements')


    @property
    def log_chan(self):
        return discord.utils.get(self.guild.channels, name='logs')


    @property
    def tinfo_chan(self):
        return discord.utils.get(self.guild.channels, name='📌info')


    @property
    def submit_chan(self):
        return discord.utils.get(self.guild.channels, name='📬submit-maps')


    @property
    def testing_role(self):
        return discord.utils.get(self.guild.roles, name='testing')


    async def upload_file(self, asset_type, file, filename):
        url = self.bot.config.get('DDNET_UPLOAD', 'URL')

        if asset_type == 'map':
            name = 'map_name'
        elif asset_type == 'log':
            name = 'channel_name'
        elif asset_type in ('attachment', 'avatar', 'emoji'):
            name = 'asset_name'
        else:
            return -1

        data = {
            'asset_type': asset_type,
            'file': file,
            name: filename
        }

        headers = {'X-DDNet-Token': self.bot.config.get('DDNET_UPLOAD', 'TOKEN')}

        async with self.bot.session.post(url, data=data, headers=headers) as resp:
            return None if resp.status == 200 else await resp.text()


    def has_map_file(self, message: discord.Message):
        return message.attachments and message.attachments[0].filename.endswith('.map')


    def is_staff(self, channel: discord.TextChannel, user: discord.Member):
        return channel.permissions_for(user).manage_channels


    def is_testing_channel(self, channel: discord.TextChannel, map_channel=False):
        testing_channel = isinstance(channel, discord.TextChannel) and channel.category in (self.mt_cat, self.em_cat)
        if map_channel:
            testing_channel = testing_channel and channel not in (self.tinfo_chan, self.submit_chan)

        return testing_channel


    def format_map_details(self, details):
        # Format: `"<name>" by <mapper> [<server>]`
        format_re = r'^\"(.+)\" +by +(.+) +\[(.+)\]$'
        match = re.search(format_re, details)
        if not match:
            return None

        name, mapper, server = match.groups()
        mapper = re.split(r', | , | & | and ', mapper)
        server = server.capitalize() if server.capitalize() in SERVER_TYPES else server

        return (name, mapper, server)


    def get_map_channel(self, name):
        name = name.lower()
        return discord.utils.find(lambda c: name == c.name[1:], self.mt_cat.channels) \
            or discord.utils.find(lambda c: name == c.name[2:], self.em_cat.channels)


    def check_map_submission(self, message: discord.Message):
        details = self.format_map_details(message.content)
        filename = message.attachments[0].filename[:-4]
        duplicate_chan = self.get_map_channel(filename)

        if not details:
            return 'Your map submission doesn\'t cointain correctly formated details.'
        elif sanitize(details[0], True, False) != filename:
            return 'Name and filename of your map submission don\'t match.'
        elif details[2] not in SERVER_TYPES:
            return 'The server type of your map submission is not valid.'
        elif duplicate_chan:
            return f'A channel for the map you submitted already exists: {duplicate_chan.mention}'
        else:
            return ''


    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if channel == self.submit_chan:
            # Handle map submissions
            if self.has_map_file(message):
                error = self.check_map_submission(message)
                if error:
                    await author.send(error)

                await message.add_reaction('❗' if error else '☑')

            # Delete messages that aren't submissions
            elif not self.is_staff(channel, author):
                await message.delete()

        if self.is_testing_channel(channel, map_channel=True):
            # Accept map updates
            if self.has_map_file(message):
                if author != self.bot.user:
                    await message.add_reaction('☑')

                await message.pin()

            # Delete spammy bot system messages
            if message.type is discord.MessageType.pins_add and author == self.bot.user:
                await message.delete()

        # Webhooks are separate with a distinct discriminator of 0000
        if channel == self.announce_chan and author.discriminator == '0000':
            # Process map channels on release
            map_url_re = r'\[(.+)\]\(<https://ddnet\.tw/maps/\?map=.+?>\)'
            match = re.search(map_url_re, message.content)
            name = sanitize(match.group(1), channel_name=True)
            map_chan = self.get_map_channel(name)
            if map_chan:
                await self.move_map_channel(map_chan, emoji='🔥')


    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        data = payload.data

        # Handle edits to initial map submissions
        if int(data['channel_id']) != self.submit_chan.id:
            return

        if not ('attachments' in data and data['attachments'][0]['filename'].endswith('.map')):
            return

        message = await self.submit_chan.fetch_message(payload.message_id)
        # Ignore already approved submissions
        # TODO: Implement this with discord.utils.get
        if any(str(r.emoji) == '✅' for r in message.reactions):
            return

        error = self.check_map_submission(message)
        if error:
            await message.author.send(error)

        await message.clear_reactions()
        await message.add_reaction('❗' if error else '☑')


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        if not self.is_testing_channel(channel):
            return

        guild = channel.guild
        user = guild.get_member(payload.user_id)
        emoji = payload.emoji
        message = await channel.fetch_message(payload.message_id)
        if message.attachments:
            attachment = message.attachments[0]
            filename = attachment.filename

        # Handle map submissions
        if str(emoji) == '☑' and self.is_staff(channel, user) and self.has_map_file(message) and user != self.bot.user:
            # TODO: Implement this with discord.utils.get
            if channel == self.submit_chan and not any(str(r.emoji) == '☑' for r in message.reactions):
                return

            users = [await r.users().flatten() for r in message.reactions if str(r.emoji) == '☑'][0]
            await message.clear_reactions()
            await message.add_reaction('🔄')

            buf = BytesIO()
            await attachment.save(buf)

            # Initial map submissions
            if channel == self.submit_chan:
                name, mapper, server = self.format_map_details(message.content)
                emoji = SERVER_TYPES[server]
                mapper = [f'**{m}**' for m in mapper]
                topic = f'**"{name}"** by {humanize_list(mapper)} [{server}]'

                map_chan = await self.mt_cat.create_text_channel(name=emoji + filename[:-4], topic=topic)

                # Remaining initial permissions are set via category synchronisation:
                # - @everyone role: read_messages=False
                # - Tester role:    manage_channels=True, read_messages=True,
                #                   manage_messages=True, manage_roles=True
                # - testing role:   read_messages = True
                # - Bot user:       read_messages=True, manage_messages=True
                await map_chan.set_permissions(message.author, read_messages=True)
                for _user in users:
                    if not map_chan.permissions_for(_user).read_messages:
                        await map_chan.set_permissions(_user, read_messages=True)

                await message.clear_reactions()
                await message.add_reaction('✅')

                file = discord.File(buf.getbuffer(), filename=filename)
                message = await map_chan.send(message.author.mention, file=file)

                # Generate the thumbnail
                if platform == 'linux':
                    await attachment.save(f'{DIR}/maps/{filename}')

                    _, err = await shell(f'{DIR}/generate_thumbnail.sh {filename}', self.bot.loop)
                    if err:
                        print('[map_thumbnail]', err)
                    else:
                        thumbnail = discord.File(f'{DIR}/thumbnails/{filename[:-4]}.png')
                        await map_chan.send(file=thumbnail)

                await message.add_reaction('🔄')

            # Upload the map to DDNet test servers
            resp = await self.upload_file('map', buf, filename[:-4])
            if resp is not None:
                print('[map_upload]', resp)

            await message.clear_reactions()
            await message.add_reaction('🆙' if resp is None else '❌')

            # Log it
            desc = f'[{filename}]({message.jump_url})'
            embed = discord.Embed(title='Map approved', description=desc, color=0x77B255, timestamp=datetime.utcnow())
            embed.set_author(name=f'{user} → #{channel}', icon_url=user.avatar_url_as(format='png'))
            await self.log_chan.send(embed=embed)

        # Handle adding map testing user permissions
        if str(emoji) == '✅':
            # General permissions
            if channel == self.tinfo_chan and self.testing_role not in user.roles:
                await user.add_roles(self.testing_role)

            # Individual channel permissions
            if channel == self.submit_chan:
                map_chan = self.get_map_channel(filename[:-4])
                if map_chan:
                    if not map_chan.permissions_for(user).read_messages:
                        await map_chan.set_permissions(user, read_messages=True)
                else:
                    await message.remove_reaction(emoji, user)


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        # Handle removing map testing user permissions
        if str(payload.emoji) != '✅':
            return

        channel = self.bot.get_channel(payload.channel_id)
        user = channel.guild.get_member(payload.user_id)

        # General permissions
        if channel == self.tinfo_chan and self.testing_role in user.roles:
            await user.remove_roles(self.testing_role)

        # Individual channel permissions
        if channel == self.submit_chan:
            message = await channel.fetch_message(payload.message_id)
            map_chan = self.get_map_channel(message.attachments[0].filename[:-4])
            if map_chan and map_chan.permissions_for(user).read_messages:
                await map_chan.set_permissions(user, overwrite=None)


    async def move_map_channel(self, channel: discord.TextChannel, emoji = ''):
        VALID_EMOJIS = ('📆', '🔥', '❌')

        prev_emoji = channel.name[0] if channel.name[0] in VALID_EMOJIS else ''
        if emoji and emoji == prev_emoji or not emoji and prev_emoji not in VALID_EMOJIS:
            return

        name = channel.name[1:] if prev_emoji else channel.name

        if emoji:
            name = emoji + name
            category = self.em_cat
            pos = 0
        else:
            category = self.mt_cat
            pos = -1

        await channel.edit(name=name, position=pos, category=category)


    # TODO: Implement this using the commands.check interface
    def testing_mod_check(self, ctx):
        return self.is_testing_channel(ctx.channel, map_channel=True) and self.is_staff(ctx.channel, ctx.author)


    async def cog_command_error(self, ctx, error):
        await ctx.author.send(error)


    @commands.command()
    async def reset(self, ctx):
        if not self.testing_mod_check(ctx):
            return

        await self.move_map_channel(ctx.channel)


    @commands.command()
    async def ready(self, ctx):
        if not self.testing_mod_check(ctx):
            return

        await self.move_map_channel(ctx.channel, emoji='📆')


    @commands.command()
    async def decline(self, ctx):
        if not self.testing_mod_check(ctx):
            return

        await self.move_map_channel(ctx.channel, emoji='❌')


def setup(bot):
    bot.add_cog(MapTesting(bot))
