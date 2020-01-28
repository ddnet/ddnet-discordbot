#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from asyncio.subprocess import PIPE
from functools import partial
from typing import Awaitable, Callable, Tuple, Union

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

async def run_in_executor(func: Callable, *args, **kwargs):
    loop = asyncio.get_event_loop()
    fn = partial(func, *args, **kwargs)
    return await loop.run_in_executor(None, fn)

async def maybe_coroutine(func: Union[Awaitable, Callable], *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
