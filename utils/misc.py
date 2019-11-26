#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from asyncio.subprocess import PIPE
from typing import Tuple

SHELL = os.getenv('SHELL')

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
