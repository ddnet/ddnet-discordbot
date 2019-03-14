import re
from datetime import datetime, timedelta
from io import BytesIO
from sys import platform
from typing import Union

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
    'DDmaX':        '🌈',
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
        return discord.utils.get(self.bot.guild.roles, name='testing')


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
            return resp.status


    def has_map_file(self, obj: Union[discord.Message, dict]):
        if isinstance(obj, discord.Message):
            return obj.attachments and obj.attachments[0].filename.endswith('.map')
        if isinstance(obj, dict):
            return obj['attachments'] and obj['attachments'][0]['filename'].endswith('.map')


    def is_staff(self, channel: discord.TextChannel, user: discord.Member):
        return channel.permissions_for(user).manage_channels and not user.bot


    def is_testing_chan(self, channel: discord.TextChannel):
        return isinstance(channel, discord.TextChannel) \
            and channel.category in (self.mt_cat, self.em_cat)


    def format_map_details(self, details):
        # Format: `"<name>" by <mapper> [<server>]`
        format_re = r'^([\"\'])(.+)\1 +by +(.+) +\[(.+)\]$'
        match = re.search(format_re, details)
        if not match:
            return None

        _, name, mapper, server = match.groups()
        mapper = re.split(r', | , | & | and ', mapper)
        try:
            server = [s for s in SERVER_TYPES.keys() if s.lower() == server.lower()][0]
        except IndexError:
            pass

        return name, mapper, server


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
        elif not details[2] in SERVER_TYPES:
            return 'The server type of your map submission is not valid.'
        elif duplicate_chan:
            return f'A channel for the map you submitted already exists: {duplicate_chan.mention}'
        else:
            return ''


    async def send_error(self, user: discord.User, error):
        # Only message users if they weren't already notified recently
        history = await user.history(after=datetime.utcnow() - timedelta(days=1)).flatten()
        if not any(m.author.bot and m.content == error for m in history):
            await user.send(error)


    @commands.Cog.listener()
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if channel == self.submit_chan:
            # Handle map submissions
            if self.has_map_file(message):
                error = self.check_map_submission(message)
                if error:
                    await self.send_error(author, error)

                await message.add_reaction('❗' if error else '☑')

            # Delete messages that aren't submissions
            elif not self.is_staff(channel, author):
                await message.delete()

        elif self.is_testing_chan(channel):
            # Accept map updates
            if self.has_map_file(message):
                await message.add_reaction('☑')
                await message.pin()

            # Delete spammy bot system messages
            if message.type is discord.MessageType.pins_add and author == self.bot.user:
                await message.delete()


    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        data = payload.data

        # Handle edits to initial map submissions
        if not (int(data['channel_id']) == self.submit_chan.id and self.has_map_file(data)):
            return

        message = await self.submit_chan.get_message(payload.message_id)
        # Ignore already approved submissions
        # TODO: Implement this with discord.utils.get
        if any(str(r.emoji) == '✅' for r in message.reactions):
            return

        error = self.check_map_submission(message)
        if error:
            await self.send_error(message.author, error)

        await message.clear_reactions()
        await message.add_reaction('❗' if error else '☑')


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        if not self.is_testing_chan(channel):
            return

        guild = channel.guild
        user = guild.get_member(payload.user_id)
        emoji = payload.emoji
        message = await channel.get_message(payload.message_id)
        if message.attachments:
            attachment = message.attachments[0]
            filename = attachment.filename

        # Handle map submissions
        if str(emoji) == '☑' and self.is_staff(channel, user) and self.has_map_file(message):
            # TODO: Implement this with discord.utils.get
            if channel == self.submit_chan and not any(str(r.emoji) == '☑' for r in message.reactions):
                return

            await message.clear_reactions()
            await message.add_reaction('🔄')

            buf = BytesIO()
            await attachment.save(buf)

            # Initial map submissions
            if channel == self.submit_chan:
                name, mapper, server = self.format_map_details(message.content)
                emoji = SERVER_TYPES[server]
                mapper = [f"**{m}**" for m in mapper]
                topic = f'**"{name}"** by {humanize_list(mapper)} [{server}]'

                map_chan = await self.mt_cat.create_text_channel(name=emoji + filename[:-4], topic=topic)

                # Remaining initial permissions are set via category synchronisation:
                # - @everyone role: read_messages=False
                # - Tester role:    manage_channels=True, read_messages=True,
                #                   manage_messages=True, manage_roles=True
                # - testing role:   read_messages = True
                # - Bot user:       read_messages=True, manage_messages=True
                await map_chan.set_permissions(message.author, read_messages=True)

                await message.clear_reactions()
                await message.add_reaction('✅')

                file = discord.File(buf.getvalue(), filename=filename)
                message = await map_chan.send(message.author.mention, file=file)

                # Generate the thumbnail
                if platform == 'linux':
                    await attachment.save(f'{DIR}/maps/{filename}')

                    _, err = await shell(f'{DIR}/generate_thumbnail.sh {filename}', self.bot.loop)
                    if err:
                        print(err)
                    else:
                        thumbnail = discord.File(f'{DIR}/thumbnails/{filename[:-4]}.png')
                        await map_chan.send(file=thumbnail)

                await message.add_reaction('🔄')

            # Upload the map to DDNet test servers
            resp = await self.upload_file('map', buf, filename[:-4])
            await message.clear_reactions()
            await message.add_reaction('🆙' if resp == 200 else '❌')

            # Log it
            desc = f'``{filename}`` | {message.id}'
            embed = discord.Embed(title='Map approved', description=desc, color=0x77B255, timestamp=datetime.utcnow())
            embed.set_author(name=f'{user} → #{channel}', icon_url=user.avatar_url_as(format='png'))
            await self.log_chan.send(embed=embed)

        # Handle adding map testing user permissions
        if str(emoji) == '✅':
            # General permissions
            if channel == self.tinfo_chan:
                await user.add_roles(self.testing_role)

            # Individual channel permissions
            if channel == self.submit_chan:
                map_chan = self.get_map_channel(filename[:-4])
                if map_chan:
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
        if channel == self.tinfo_chan:
            await user.remove_roles(self.testing_role)

        # Individual channel permissions
        if channel == self.submit_chan:
            message = await channel.get_message(payload.message_id)
            map_chan = self.get_map_channel(message.attachments[0].filename[:-4])
            if map_chan:
                await map_chan.set_permissions(user, overwrite=None)


def setup(bot):
    bot.add_cog(MapTesting(bot))
