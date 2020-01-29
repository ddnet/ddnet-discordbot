#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import textwrap
import traceback
from contextlib import redirect_stdout
from io import StringIO

import discord
from discord.ext import commands

from utils.misc import run_process

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

    async def mystbin_upload(self, content: str) -> str:
        data = content.encode('utf-8')
        async with self.bot.session.post('https://mystb.in/documents', data=data) as resp:
            js = await resp.json()
            if resp.status != 200:
                log.error('Failed uploading to mystb.in: %s (status code: %d %s)', js['message'], resp.status, resp.reason)
                raise RuntimeError('Could not upload result to mystb.in')

            return f'<https://mystb.in/{js["key"]}.py>'

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

        content = None
        stdout = StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as exc:
            return await ctx.send(f'```py\n{exc.__class__.__name__}: {exc}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            content = value + traceback.format_exc()
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction(CONFIRM)
            except discord.HTTPException:
                pass

            if ret is None:
                if value:
                    content = value
            else:
                self._last_result = ret
                content = value + str(ret)

        if content:
            if len(content) <= 1990:
                msg = f'```py\n{content}\n```'
            else:
                try:
                    msg = await self.mystbin_upload(content)
                except RuntimeError as exc:
                    msg = exc

            await ctx.send(msg)

    @commands.command()
    async def sh(self, ctx: commands.Context, *, cmd: str):
        await ctx.trigger_typing()

        try:
            stdout, stderr = await run_process(cmd)
        except RuntimeError as exc:
            return await ctx.send(exc)

        content = []
        if stdout:
            content.append(stdout)
        if stderr:
            content.append(f'stderr:\n{stderr}')

        if not content:
            return await ctx.message.add_reaction(CONFIRM)

        content = '\n'.join([f'$ {cmd}'] + content)
        if len(content) <= 1990:
            msg = f'```sh\n{content}\n```'
        else:
            try:
                msg = await self.mystbin_upload(content)
            except RuntimeError as exc:
                msg = exc

        await ctx.send(msg)

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        await self.bot.close()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Admin(bot))
