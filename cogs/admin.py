#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import textwrap
import traceback
from contextlib import redirect_stdout
from io import StringIO

import discord
from discord.ext import commands

CONFIRM = '\N{OK HAND SIGN}'


def cleanup_code(content: str) -> str:
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])

    # remove `foo`
    return content.strip('` \n')


class Admin(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._last_result = None


    async def cog_check(self, ctx: commands.Context) -> bool:
        return await self.bot.is_owner(ctx.author)


    @commands.command()
    async def load(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.load_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)


    @commands.command()
    async def unload(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.unload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)


    @commands.command()
    async def reload(self, ctx: commands.Context, *, extension: str) -> None:
        try:
            self.bot.reload_extension(extension)
        except Exception:
            await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        else:
            await ctx.message.add_reaction(CONFIRM)


    @commands.command(name='eval')
    async def _eval(self, ctx: commands.Context, *, body: str) -> None:
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

        body = cleanup_code(body)
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
            content = f'```py\n{value}{traceback.format_exc()}\n```'
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction(CONFIRM)
            except discord.HTTPException:
                pass

            if ret is None:
                if value:
                    content = f'```py\n{value}\n```'
            else:
                self._last_result = ret
                content = f'```py\n{value}{ret}\n```'

        if content:
            if len(content) > 2000:
                url = 'https://mystb.in/documents'
                data = cleanup_code(content)
                async with self.bot.session.post(url, data=data) as resp:
                    js = await resp.json()

                await ctx.send(f'Content too big: https://mystb.in/{js["key"]}.py')
            else:
                await ctx.send(content)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Admin(bot))
