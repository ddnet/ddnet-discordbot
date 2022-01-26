#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import textwrap
import time
import traceback
from contextlib import redirect_stdout
from io import StringIO

import asyncpg
from discord.ext import commands

from utils.misc import run_process_shell
from utils.text import plural, render_table

log = logging.getLogger(__name__)

CONFIRM = '👌'


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        admin_id = self.bot.config.get('DDNET', 'ADMIN')
        return ctx.author.id == int(admin_id)

    async def paste_upload(self, content: str) -> str:
        url = 'https://paste.pr0.tips/'
        data = content.encode('utf-8')
        async with self.bot.session.post(url, data=data) as resp:
            return await resp.text()

    async def send_or_paste(self, ctx: commands.Context, msg: str, paste_msg: str=None):
        # TODO implement this in a subclass of Context
        if len(msg) > 2000:
            msg = await self.paste_upload(paste_msg or msg)

        await ctx.send(msg)

    @commands.command()
    async def load(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.load_extension(extension)
        except Exception:
            trace = traceback.format_exc()
            await self.send_or_paste(ctx, f'```py\n{trace}\n```', trace)
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def unload(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.unload_extension(extension)
        except Exception:
            trace = traceback.format_exc()
            await self.send_or_paste(ctx, f'```py\n{trace}\n```', trace)
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def reload(self, ctx: commands.Context, *, extension: str):
        try:
            self.bot.reload_extension(extension)
        except Exception:
            trace = traceback.format_exc()
            await self.send_or_paste(ctx, f'```py\n{trace}\n```', trace)
        else:
            await ctx.message.add_reaction(CONFIRM)

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

        await self.send_or_paste(ctx, f'```py\n{content}\n```', content)

    @commands.command()
    async def sh(self, ctx: commands.Context, *, cmd: str):
        await ctx.trigger_typing()

        content = []
        try:
            stdout, stderr = await run_process_shell(cmd)
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
        await self.send_or_paste(ctx, f'```sh\n{content}\n```', content)

    @commands.command()
    async def sql(self, ctx: commands.Context, *, query: str):
        try:
            start = time.perf_counter()
            records = await self.bot.pool.fetch(query)
            duration = (time.perf_counter() - start) * 1000.0
        except asyncpg.PostgresError as exc:
            return await ctx.send(f'``{exc}``')

        if not records:
            return await ctx.message.add_reaction(CONFIRM)

        header = list(records[0].keys())
        rows = [['' if v is None else str(v) for v in r.values()] for r in records]
        table = render_table(header, rows)
        num = len(records)
        footer = f'{num} {plural(num, "row")} in {duration:.2f}ms'

        await self.send_or_paste(ctx, f'```\n{table}\n```\n*{footer}*', f'{table}\n{footer}')

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        await self.bot.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Admin(bot))
