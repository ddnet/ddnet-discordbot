#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from io import StringIO

from discord.ext import commands

from utils.misc import run_process
from utils.text import plural, render_table

log = logging.getLogger(__name__)

CONFIRM = '👌'


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def load(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.load_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def unload(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.unload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def reload(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.reload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)

    async def hastebin_upload(self, content: str) -> str:
        data = content.encode('utf-8')
        async with self.bot.session.post('https://hastebin.com/documents', data=data) as resp:
            js = await resp.json()
            if resp.status != 200:
                fmt = 'Failed uploading to hastebin.com: %s (status code: %d %s)'
                log.error(fmt, js['message'], resp.status, resp.reason)
                raise RuntimeError('Could not upload to hastebin')

            return f'<https://hastebin.com/{js["key"]}.py>'

    @commands.command(name='eval')
    async def _eval(self, ctx: commands.Context, *, body: str):
        env = {
            'self': self,
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }

        env.update(globals())

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as exc:
            content = f'{exc.__class__.__name__}: {exc}'
        else:
            stdout = StringIO()
            func = env['func']
            try:
                with redirect_stdout(stdout):
                    ret = await func()
            except Exception:
                content = stdout.getvalue() + traceback.format_exc()
            else:
                content = stdout.getvalue()
                if ret is not None:
                    self._last_result = ret
                    content += str(ret)

        if not content:
            return await ctx.message.add_reaction(CONFIRM)

        msg = f'```py\n{content}\n```'
        if len(msg) > 2000:
            try:
                msg = await self.hastebin_upload(content)
            except RuntimeError as exc:
                msg = exc

        await ctx.send(msg)

    @commands.command()
    async def sh(self, ctx: commands.Context, *, cmd: str):
        await ctx.trigger_typing()

        content = []
        try:
            stdout, stderr = await run_process(cmd)
        except RuntimeError as exc:
            content.append(str(exc))
        else:
            if stdout:
                content.append(stdout)
            if stderr:
                content.append(f'stderr:\n{stderr}')

        if not content:
            return await ctx.message.add_reaction(CONFIRM)

        content = '\n'.join([f'$ {cmd}'] + content)
        msg = f'```sh\n{content}\n```'
        if len(msg) > 2000:
            try:
                msg = await self.hastebin_upload(content)
            except RuntimeError as exc:
                msg = exc

        await ctx.send(msg)

    @commands.command()
    async def sql(self, ctx: commands.Context, *, query: str):
        try:
            start = time.perf_counter()
            records = await self.bot.pool.fetch(query)
            duration = (time.perf_counter() - start) * 1000.0
        except Exception:
            return await ctx.send(f'```py\n{traceback.format_exc()}\n```')

        if not records:
            return await ctx.message.add_reaction(CONFIRM)

        header = list(records[0].keys())
        rows = [[str(v) for v in r.values()] for r in records]
        table = render_table(header, rows)
        num = len(records)
        footer = f'{num} {plural(num, "row")} in {duration:.2f}ms'

        msg = f'```\n{table}\n```\n*{footer}*'
        if len(msg) > 2000:
            try:
                msg = await self.hastebin_upload(f'{table}\n{footer}')
            except RuntimeError as exc:
                msg = exc

        await ctx.send(msg)

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        await self.bot.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Admin(bot))
