import json
import os
import asyncio
import re
import discord


def load_json(path):
    with open(path, 'r', encoding='utf8') as f:
        return json.loads(f.read())


def write_json(path, inp):
    with open(path, 'w', encoding='utf8') as f:
        f.write(json.dumps(inp, indent=4))


def get_filename(path):
    if len(path.split('.')) > 2:
        return path.split('.')[0]

    return os.path.splitext(path)[0]


def get_extension(path):
    if len(path.split('.')) > 2:
        return '.'.join(path.split('.')[-2:])

    return os.path.splitext(path)[1]


def sanitize_channel_name(name):
    name = re.sub(r'[\^<>{}"/|;:.,~!?@#$%^=&*\]\\()\[+]', '', name)  # Channel names can't contain special characters
    name = name.lower()  # Characters are transformed to lower case
    name = name.replace(' ', '_')  # Space is transformed to underscore
    return name


def escape_markdown(name):
    return re.sub(r'([`~_\*])', r'\\\1', name)  # Codeblock, strikethrough, underline, bold, italics


def format_size(size):
    for unit in ['', 'K', 'M']:  # Discord only accepts files up to 50MB (8MB without Nitro)
        if abs(size) < 1024.0:
            return '%3.1f' % size, unit + 'B'

        size /= 1024.0


def round_properly(num: float):
    if num % 1 >= 0.5:
        return int(num) + 1

    return int(num)


def num_to_emoji(num: int):
    shortcuts = [':zero:', ':one:', ':two:', ':three:', ':four:',
                 ':five:', ':six:', ':seven:', ':eight:', ':nine:']
    return ''.join(shortcuts[int(n)] for n in str(num))


def emoji_to_num(emoji: str):
    emoji = list(filter(None, emoji.split(':')))
    shortcuts = ['zero', 'one', 'two', 'three', 'four',
                 'five', 'six', 'seven', 'eight', 'nine']
    return int(''.join(str(shortcuts.index(e)) for e in emoji))


async def render_thumbnail(path):
    cmd = f'map_testing/render_map/render_map {path} --size 1280'
    os.popen(cmd).read()

    while not os.path.exists(f'{path}.png'):
        await asyncio.sleep(1)

    if os.path.isfile(f'{path}.png'):
        return True

    return False


def get(iterable, attribute):
    return discord.utils.get(iterable, id=attribute)
