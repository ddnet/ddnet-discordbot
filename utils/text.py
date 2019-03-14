import re

import emoji


def escape_single_backquote(text):
    if re.search(r'[^`]`[^`]', text) is not None:
        return f'`{escape_double_backquote(text)}`'
    if text[:2] == '``':
        text = f'\u200b{text}'
    if text[-1] == '`':
        text += '\u200b'

    return escape_custom_emojis(text)


def escape_double_backquote(text):
    text = text.replace('``', '`\u200b`')
    if text[0] == '`':
        text = f'\u200b{text}'
    if text[-1] == '`':
        text += '\u200b'

    return escape_custom_emojis(text)


def escape_triple_backquote(text):
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


def escape_markdown(text):
    return re.sub(r'([*`_~\\])', r'\\\1', text)


def escape_mentions(text):
    return text.replace('@', '@\u200b')


def escape_emojis(text):
    return ''.join(f'\\{c}' if c in emoji.UNICODE_EMOJI else c for c in text)


def escape_custom_emojis(text):
    return re.sub(r'<(a)?:([a-zA-Z0-9_]+):([0-9]+)>', r'<%s\1:\2:\3>' % '\u200b', text)


def escape(text, markdown=True, mentions=True, emojis=True, custom_emojis=True):
    if markdown:
        text = escape_markdown(text)
    if mentions:
        text = escape_mentions(text)
    if emojis:
        text = escape_emojis(text)
    if custom_emojis:
        text = escape_custom_emojis(text)

    return text


def unescape_markdown(text):
    return re.sub(r'\\([*`_~\\])', r'\1', text)


def unescape_mentions(text):
    return text.replace(f'@\u200b', '@')


def unescape_custom_emojis(text):
    return re.sub(r'<%s(a)?:([a-zA-Z0-9_]+):([0-9]+)>' % '\u200b', r'<\1:\2:\3>', text)


def unescape(text, markdown=True, mentions=True, custom_emojis=True):
    if markdown:
        text = unescape_markdown(text)
    if mentions:
        text = unescape_mentions(text)
    if custom_emojis:
        text = unescape_custom_emojis(text)

    return text
