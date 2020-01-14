#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from typing import List

import discord
from discord.ext import commands


class clean_content(commands.clean_content):
    def __init__(self):
        super().__init__(fix_channel_mentions=True)

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument = re.sub(r'<a?(:[a-zA-Z0-9_]+:)[0-9]{17,21}>', r'\1', argument)
        return await super().convert(ctx, argument)


def escape_backticks(text: str) -> str:
    return text.replace('`', '`\u200b')

def escape_custom_emojis(text: str) -> str:
    return re.sub(r'<(a)?:([a-zA-Z0-9_]+):([0-9]{17,21})>', r'<%s\1:\2:\3>' % '\u200b', text)

def escape(text: str, markdown: bool=True, mentions: bool=True, custom_emojis: bool=True) -> str:
    if markdown:
        text = discord.utils.escape_markdown(text)
    if mentions:
        text = discord.utils.escape_mentions(text)
    if custom_emojis:
        text = escape_custom_emojis(text)

    return text

def truncate(text: str, *, length: int) -> str:
    return f'{text[:length - 3]}...' if len(text) > length else text

def human_join(seq: List[str], delim: str=', ', final: str=' & ') -> str:
    size = len(seq)
    if size == 0:
        return ''
    elif size == 1:
        return seq[0]
    elif size == 2:
        return seq[0] + final + seq[1]
    else:
        return delim.join(seq[:-1]) + final + seq[-1]

def sanitize(text: str) -> str:
    return re.sub(r'[\^<>{}"/|;:,.~!?@#$%^=&*\]\\()\[+]', '', text.replace(' ', '_'))

def plural(value: int, singular: str) -> str:
    return singular if abs(value) == 1 else singular + 's'
