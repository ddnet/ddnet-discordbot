#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import re
from asyncio.subprocess import PIPE
from typing import Tuple

SHELL = os.getenv('SHELL')

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

async def run_process(cmd: str, timeout: float=90.0) -> Tuple[str, str]:
    sequence = f'{SHELL} -c \'{cmd}\''
    proc = await asyncio.create_subprocess_shell(sequence, stdout=PIPE, stderr=PIPE)

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.terminate()
        await proc.wait()
        stdout = ''
        stderr = 'Process timed out'
    else:
        stdout = stdout.decode()
        stderr = stderr.decode()

    return stdout, stderr
