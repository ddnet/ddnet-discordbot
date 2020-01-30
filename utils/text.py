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
        argument = argument.replace('\ufe0f', '')  # remove VS16
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

def normalize(text: str) -> str:
    return re.sub(br'[^a-zA-Z0-9]', br'_', text.encode()).decode()

def plural(value: int, singular: str) -> str:
    return singular if abs(value) == 1 else singular + 's'

def render_table(header: List[str], rows: List[List[str]]) -> str:
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(len(header))]

    out = [
        ' | '.join(c.center(w) for c, w in zip(header, widths)),
        '-+-'.join('-' * w for w in widths)
    ]

    for row in rows:
        columns = []
        for column, width in zip(row, widths):
            try:
                float(column)
            except ValueError:
                columns.append(column.ljust(width))
            else:
                columns.append(column.rjust(width))

        out.append(' | '.join(columns))

    return '\n'.join(out)
