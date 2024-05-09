#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import textwrap
import traceback
from contextlib import redirect_stdout
from io import StringIO
from discord.ext import commands
from discord.ext.commands import ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed, \
    ExtensionNotLoaded

log = logging.getLogger(__name__)

CONFIRM = '👌'


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id == int(self.bot.config.get('DDNET', 'ADMIN'))

    async def paste_upload(self, content: str) -> str:
        url = 'https://paste.pr0.tips/'
        data = content.encode('utf-8')
        async with self.bot.session.post(url, data=data) as resp:
            return await resp.text()

    async def send_or_paste(self, ctx: commands.Context, msg: str, paste_msg: str = None):
        # TODO implement this in a subclass of Context
        if len(msg) > 2000:
            msg = await self.paste_upload(paste_msg or msg)

        await ctx.send(msg)

    @commands.command()
    async def load(self, ctx: commands.Context, *, extension: str):
        try:
            await self.bot.load_extension(extension)
        except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed):
            trace = traceback.format_exc()
            await self.send_or_paste(ctx, f'```py\n{trace}\n```', trace)
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def unload(self, ctx: commands.Context, *, extension: str):
        try:
            await self.bot.unload_extension(extension)
        except (ExtensionNotFound, ExtensionNotLoaded):
            trace = traceback.format_exc()
            await self.send_or_paste(ctx, f'```py\n{trace}\n```', trace)
        else:
            await ctx.message.add_reaction(CONFIRM)

    @commands.command()
    async def reload(self, ctx: commands.Context, *, extension: str):
        try:
            await self.bot.reload_extension(extension)
        except (ExtensionNotLoaded, ExtensionNotFound, NoEntryPointError, ExtensionFailed):
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
    async def shutdown(self, _: commands.Context):
        await self.bot.close()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
