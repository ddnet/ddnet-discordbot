#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import discord


def escape_single_backquote(text: str) -> str:
    if re.search(r'[^`]`[^`]', text) is not None:
        return f'`{escape_double_backquote(text)}`'
    if text[:2] == '``':
        text = f'\u200b{text}'
    if text[-1] == '`':
        text += '\u200b'

    return escape_custom_emojis(text)

def escape_double_backquote(text: str) -> str:
    text = text.replace('``', '`\u200b`')
    if text[0] == '`':
        text = f'\u200b{text}'
    if text[-1] == '`':
        text += '\u200b'

    return escape_custom_emojis(text)

def escape_triple_backquote(text: str) -> str:
    if not text:
        return text

    i = 0
    n = 0
    while i < len(text):
        if text[i] == '`':
            n += 1
        if n == 3:
            text = f'{text[:i]}\u200b{text[i:]}'
            n = 1
            i += 1
        i += 1

    if text[-1] == '`':
        text += '\u200b'

    return escape_custom_emojis(text)

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

def unescape_markdown(text: str) -> str:
    return re.sub(r'\\([*`_~\\])', r'\1', text)

def unescape_mentions(text: str) -> str:
    return text.replace(f'@\u200b', '@')

def unescape_custom_emojis(text: str) -> str:
    return re.sub(r'<%s(a)?:([a-zA-Z0-9_]+):([0-9]{17,21})>' % '\u200b', r'<\1:\2:\3>', text)

def unescape(text: str, markdown: bool=True, mentions: bool=True, custom_emojis: bool=True) -> str:
    if markdown:
        text = unescape_markdown(text)
    if mentions:
        text = unescape_mentions(text)
    if custom_emojis:
        text = unescape_custom_emojis(text)

    return text

def truncate(text: str, *, length: int) -> str:
    return f'{text[:length - 3]}...' if len(text) > length else text
