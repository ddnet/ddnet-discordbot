import re
import os
import json
import datetime
import shutil

import requests
import discord
from discord.ext import commands

from .utils.misc import format_size

GUILD_DDNET = 252358080522747904
DIR = '/var/www/testing-log/resources/logs'
FILE_DIR = f'{DIR}/files'


def download_file(url, path):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


class Archiving:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @commands.has_role('Admin')
    async def archive(self, ctx):
        def process_multiline_codeblock(groups):
            return {
                'multiline-codeblock': {
                    'text': groups[0]
                }
            }

        def process_inline_codeblock(groups):
            return {
                'inline-codeblock': {
                    'text': groups[0]
                }
            }

        def process_reaction(reaction):
            return {
                'emoji': reaction.emoji,
                'count': reaction.count
            }

        def process_custom_reaction(name, id, count):
            if not os.path.isfile(str(id) + '.png'):
                download_file(f'https://cdn.discordapp.com/emojis/{id}.png', f'{FILE_DIR}/emojis/{str(id)}.png')

            return {
                'name': name,
                'id': int(id),
                'count': count
            }

        def process_file(attachment: discord.Attachment):
            basename, extension = os.path.splitext(attachment.filename)
            filesize, units = format_size(attachment.size)
            return {
                'attachment': {
                    'id': attachment.id,
                    'basename': basename,
                    'extension': extension,
                    'filesize': filesize,
                    'filesize-units': units
                }
            }

        def process_image(image: discord.Attachment):
            basename, extension = os.path.splitext(image.filename)
            return {
                'image': {
                    'id': image.id,
                    'basename': basename,
                    'extension': extension
                }
            }

        def process_custom_emoji(groups):
            name = groups[0]
            id = groups[1]

            if not os.path.isfile(id + '.png'):
                download_file(f'https://cdn.discordapp.com/emojis/{id}.png', f'{FILE_DIR}/emojis/{str(id)}.png')

            return {
                'custom-emoji': {
                    'name': name,
                    'id': int(id)
                }
            }

        def process_user_mention(groups):
            user = guild.get_member(int(groups[0]))
            try:
                # Replace '@everyone' role with 'generic'. Reverse list so that the highest role is on top
                roles = ['generic' if r.name == '@everyone' else r.name for r in user.roles][::-1]
            except:
                roles = ['generic']

            if user and user.avatar and not os.path.isfile(user.avatar + '.png'):
                download_file(user.avatar_url_as(format='png', static_format='png'),
                              f'{FILE_DIR}/avatars/{str(user.avatar)}.png')

            return {
                'user-mention': {
                    'name': user.name if user else groups[0],
                    'discriminator': user.discriminator if user else 0,
                    'avatar': {
                        'id': user.avatar if user and user.avatar else "0"
                    },
                    'roles': roles
                }
            }

        def process_channel_mention(groups):
            channel = self.bot.get_channel(int(groups[0]))
            return {
                'channel-mention': {
                    'name': channel.name
                }
            }

        def process_role_mention(groups):
            role = discord.utils.get(guild.roles, id=int(groups[0]))
            return {
                'role-mention': {
                    'name': role.name
                }
            }

        def process_url(groups):
            url_string = groups[0]
            return {
                'url': url_string
            }

        def process_markdown(groups):
            regex = r'(~~|__|\*\*|_|\*)'
            left_markdown = re.findall(regex, groups[0])
            left_markdown = list(filter(None, left_markdown))
            left_revers = list(reversed(left_markdown))
            right_markdown = re.split(regex, groups[2])
            right_markdown = list(filter(None, right_markdown))

            if left_revers == right_markdown:
                out = {'text': groups[1]}
                if '~~' in left_markdown:
                    out['strikethrough'] = True
                if '__' in left_markdown:
                    out['underline'] = True
                if '**' in left_markdown:
                    out['bold'] = True
                if '_' in left_markdown or '*' in left_markdown:
                    out['italics'] = True

                return out

            return False

        regexes = [
            {
                'processor': process_multiline_codeblock,
                'regex': r'```(?:[^`]*?\n)?([^`]+)\n?```'
            },
            {
                'processor': process_inline_codeblock,
                'regex': r'(?:`|``)([^`]+)(?:`|``)'
            },
            {
                'processor': process_custom_emoji,
                'regex': r'<(:.*?:)(\d*)>'
            },
            {
                'processor': process_user_mention,
                'regex': r'<@!?(\d+)>'
            },
            {
                'processor': process_channel_mention,
                'regex': r'<#(\d+)>'
            },
            {
                'processor': process_role_mention,
                'regex': r'<@&(\d+)>'
            }
        ]

        if not ctx.message.guild or ctx.message.guild.id != 252358080522747904:
            return

        await ctx.message.delete()

        guild = ctx.guild
        channel = ctx.channel
        # Strip the first 2 characters since they are status symbols, which aren't needed in the log list
        channel_name = channel.name[2:]
        channel_topic = str(channel.topic).replace('**', '')
        options = [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:']

        for n, s in enumerate(options):
            if s in channel_topic:
                channel_topic = channel_topic.replace(s, str(n))

        output = {
            'protocol': {
                'version': 1.0
            },
            'name': channel_name,
            'topic': channel_topic
        }

        channel_messages = await channel.history(limit=None).flatten()
        # Sort messages based on creation date since it doesn't seem to realiably do so by default
        channel_messages = sorted(channel_messages, key=lambda m: m.created_at)
        messages = []
        txt_output = ''
        for message in channel_messages:
            user = message.author
            try:
                # Replace '@everyone' role with 'generic'. Reverse list so that the highest role is on top
                roles = ['generic' if r.name == '@everyone' else r.name for r in user.roles][::-1]
            except:
                roles = ['generic']

            if user.avatar and not os.path.isfile(user.avatar + '.png'):
                download_file(user.avatar_url_as(format='png', static_format='png'),
                              f'{FILE_DIR}/avatars/{str(user.avatar)}.png')

            current_message = {
                'author': {
                    'name': user.name,
                    'discriminator': user.discriminator,
                    'avatar': {
                        'id': user.avatar if user.avatar else "0"
                    },
                    'roles': roles
                },
                'timestamp': message.created_at.isoformat(),
                'content': []
            }

            if message.content:
                message_content = [{'text': message.content}]

                for regex in regexes:
                    for key, message_chunk in enumerate(message_content):
                        if 'text' in message_chunk:
                            match = re.search(regex['regex'], message_content[key]['text'])
                            if match:
                                text = message_content[key]['text']

                                text_before_match = text[:match.start()]
                                if text_before_match:
                                    message_content[key] = {'text': text_before_match}
                                    key += 1
                                else:
                                    del message_content[key]

                                # If there are capturing groups, send those. If not, send the whole matched string
                                processed_match = regex['processor'](
                                    match.groups() if match.groups() else match.group(0)
                                )
                                # False positives or fails if someone used a weird, unsymmetrical markdown combination.
                                # Either add an exception or add it manually
                                if not processed_match:
                                    return await ctx.message.author.send(
                                        match.groups() if match.groups() else match.group(0)
                                    )

                                message_content.insert(key, processed_match)
                                key += 1

                                text_after_match = text[match.end():]
                                if text_after_match:
                                    message_content.insert(key, {'text': text_after_match})

                current_message['content'].append({'text': message_content})

            if message.attachments:
                attachment = message.attachments[0]
                extension = os.path.splitext(attachment.filename)
                await attachment.save(f'{FILE_DIR}/attachments/{str(attachment.id)}.{extension[1][1:]}')

                # Only images have a `height` attribute (also `witdh`)
                if attachment.height:
                    current_message['content'].append(process_image(attachment))
                else:
                    current_message['content'].append(process_file(attachment))

            if message.reactions:
                reactions = {'reactions': []}

                for reaction in message.reactions:
                    emoji = str(reaction.emoji)
                    match = re.search(r'<(:.*?:)(\d*)>', emoji)

                    if match:
                        reactions['reactions'].append(process_custom_reaction(match.group(1),
                                                                              match.group(2),
                                                                              reaction.count))
                    else:
                        reactions['reactions'].append(process_reaction(reaction))

                current_message['content'].append(reactions)

            messages.append(current_message)

            txt_content = message.content
            if message.attachments:
                if txt_content:
                    txt_content += f'\n{message.attachments[0].url}'
                else:
                    txt_content += message.attachments[0].url

            txt_output += f'[{message.created_at.strftime("%m/%d/%Y %I:%M %p")}] {user}: {txt_content}\n\n'

        output['messages'] = messages

        with open(f'{DIR}/json/{channel_name}.json', 'w', encoding='utf-8') as jsonfile:
            output = json.dumps(output, indent=4, cls=SetEncoder)
            jsonfile.write(output)

        txt_output = ('================================================'
                      f'\nMap Testing - #{channel_name}'
                      f'\n{channel_topic}'
                      f'\n{datetime.datetime.utcnow()}'
                      '\n================================================'
                      f'\n\n{txt_output}')

        with open(f'{DIR}/txt/{channel_name}.txt', 'w', encoding='utf-8') as txtfile:
            txtfile.write(txt_output)


def setup(bot):
    bot.add_cog(Archiving(bot))
