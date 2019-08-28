#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import re
from asyncio.subprocess import PIPE
from sys import platform
from typing import Optional, Tuple


def sanitize(name: str, channel_name: bool=False, case_insensitive: bool=True) -> str:
    name = re.sub(r'[\^<>{}"/|;:,~!?@#$%^=&*\]\\()\[+]', '', name)
    if channel_name:
        name = name.replace(' ', '_')
    if case_insensitive:
        name = name.lower()

    return name

def human_join(seq: list, delim: str=', ', final: str=' & ') -> str:
    size = len(seq)
    if size == 0:
        return ''
    elif size == 1:
        return seq[0]
    elif size == 2:
        return seq[0] + final + seq[1]
    else:
        return delim.join(seq[:-1]) + final + seq[-1]

async def run_process(cmd: str) -> Tuple[Optional[str], Optional[str]]:
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode()
