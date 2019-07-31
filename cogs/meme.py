#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from functools import partial
from typing import List

import discord
from discord.ext import commands


def wrap(line_width: int, text: str, font: ImageFont) -> List[str]:
    words = text.split()

    lines = []
    line = []

    for word in words:
        newline = ' '.join(line + [word])

        w, _ = font.getsize(newline)

        if w > line_width:
            lines.append(' '.join(line))
            line = [word]
        else:
            line.append(word)

    if line:
        lines.append(' '.join(line))

    return ('\n'.join(lines)).strip()


class Memes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def generate(self, type_: str, text1: str, text2: str) -> BytesIO:
        base = Image.open(f'data/memes/{type_}.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype('data/ddnet-stats/fonts/normal.ttf', 46)

        canv.text((600, 100), wrap(font, text1, 400), fill='black', font=font)
        if text2 is not None:
            canv.text((600, 500), wrap(font, text2, 400), fill=(0, 0, 0), font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    async def executor(self, type_: str, text1: str, text2: str=None) -> discord.File:
        fn = partial(self.generate, 'angry', text1, text2)
        buf = await self.bot.loop.run_in_executor(None, fn)
        return discord.File(buf, filename='angry.png')

    @commands.command()
    async def angry(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('angry', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def happy(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('happy', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def sleep(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('sleep', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def angryjao(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('angryjao', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def teeward(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('teeward', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def drake(self, ctx: commands.Context, text1: str, text2: str):
        file = await self.executor('drake', text1, text2)
        await ctx.send(file=file)

    @commands.command()
    async def ohno(self, ctx: commands.Context, *, text: str):
        file = await self.executor('ohno', text)
        await ctx.send(file=file)

    def generate_teebob(self, text: str):
        base = Image.open('data/memes/teebob.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype('data/ddnet-stats/fonts/normal.ttf', 40)

        canv.text((100, 120), wrap(font, text, 250), fill='black', font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command()
    async def teebob(self, ctx: commands.Context, *, text: str):
        fn = partial(self.generate_teebob, text)
        buf = await self.bot.loop.run_in_executor(None, fn)
        file = discord.File(buf, filename='teebob.png')
        await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Memes(bot))
