import asyncio
import re
from asyncio.subprocess import PIPE
from sys import platform
from typing import Tuple


def sanitize(name: str, channel_name: bool=False, case_insensitive: bool=True) -> str:
    name = re.sub(r'[\^<>{}"/|;:,~!?@#$%^=&*\]\\()\[+]', '', name)
    if channel_name:
        name = name.replace(' ', '_')
    if case_insensitive:
        name = name.lower()

    return name


def humanize_list(seq: list, delim: str=', ', final: str=' & ') -> str:
    size = len(seq)
    if size == 0:
        return ''
    elif size == 1:
        return seq[0]
    elif size == 2:
        return f'{seq[0]} {final} {seq[1]}'
    else:
        return f'{delim.join(seq[:-1])} {final} {seq[-1]}'


async def shell(cmd: str, loop: asyncio.AbstractEventLoop=None) -> Tuple[str]:
    if platform == 'win32':
        loop = asyncio.ProactorEventLoop()  # Subprocess pipes only work with this under Windows
        asyncio.set_event_loop(loop)
    elif not loop:
        loop = asyncio.get_event_loop()

    proc = await asyncio.create_subprocess_shell(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, loop=loop)

    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode()
