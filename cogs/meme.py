#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import BytesIO
from typing import List

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.image import save, wrap_new

DIR = 'data/assets'


def wrap(font: ImageFont, text: str, line_width: int) -> str:
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

    wrapped_text = '\n'.join(lines)
    return wrapped_text.strip()


def check_text_length(text1: str, text2: str = None, max_chars: int = 110) -> List[str]:
    errors = []
    if text1 and len(text1) > max_chars:
        errors.append('Text-1 has too many characters')
    if text2 and len(text2) > max_chars:
        errors.append('Text-2 has too many characters')
    return errors


async def render(name: str, text1: str, text2: str = None) -> BytesIO:
    base = Image.open(f'{DIR}/memes/{name}.png')
    canv = ImageDraw.Draw(base)
    font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 46)

    canv.text((570, 70), wrap(font, text1, 400), fill='black', font=font)
    if text2 is not None:
        canv.text((570, 540), wrap(font, text2, 400), fill='black', font=font)

    return save(base)


async def render_teebob(text: str) -> BytesIO:
    base = Image.open(f'{DIR}/memes/teebob.png')
    canv = ImageDraw.Draw(base)
    font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 40)

    box = ((100, 110), (360, 370))
    wrap_new(canv, box, text, font=font)

    return save(base)


async def render_clown(text1: str, text2: str, text3: str, text4: str) -> BytesIO:
    base = Image.open(f'{DIR}/memes/clown.png')
    canv = ImageDraw.Draw(base)
    font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 30)

    canv.text((10, 10), wrap(font, text1, 310), fill='black', font=font)
    canv.text((10, 180), wrap(font, text2, 310), fill='black', font=font)
    canv.text((10, 360), wrap(font, text3, 310), fill='black', font=font)
    canv.text((10, 530), wrap(font, text4, 310), fill='black', font=font)

    return save(base)


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='angry')
    async def angry_command(self, ctx: commands.Context, text1: str, text2: str = None):
        errors = check_text_length(text1, text2)
        if errors:
            for error in errors:
                await ctx.send(error)
            return
        buf = await render('angry', text1, text2)
        file = discord.File(buf, filename='angry.png')
        await ctx.send(file=file)

    @commands.command(name='drake')
    async def drake_command(self, ctx: commands.Context, text1: str, text2: str):
        errors = check_text_length(text1, text2)
        if errors:
            for error in errors:
                await ctx.send(error)
            return
        buf = await render('drake', text1, text2)
        file = discord.File(buf, filename='drake.png')
        await ctx.send(file=file)

    @commands.command(name='happy')
    async def happy_command(self, ctx: commands.Context, text1: str, text2: str = None):
        errors = check_text_length(text1, text2)
        if errors:
            for error in errors:
                await ctx.send(error)
            return
        buf = await render('happy', text1, text2)
        file = discord.File(buf, filename='happy.png')
        await ctx.send(file=file)

    @commands.command(name='sleep')
    async def sleep_command(self, ctx: commands.Context, text1: str, text2: str = None):
        """Usage: "Text1" "Text2\""""
        errors = check_text_length(text1, text2)
        if errors:
            for error in errors:
                await ctx.send(error)
            return
        buf = await render('sleep', text1, text2)
        file = discord.File(buf, filename='sleep.png')
        await ctx.send(file=file)

    @commands.command(name='teeward')
    async def teeward_command(self, ctx: commands.Context, text1: str, text2: str):
        errors = check_text_length(text1, text2)
        if errors:
            for error in errors:
                await ctx.send(error)
            return
        buf = await render('teeward', text1, text2)
        file = discord.File(buf, filename='teeward.png')
        await ctx.send(file=file)

    @commands.command()
    async def teebob(self, ctx: commands.Context, *, text: str):
        buf = await render_teebob(text)
        file = discord.File(buf, filename='teebob.png')
        await ctx.send(file=file)

    @commands.command()
    async def clown(self, ctx: commands.Context, text1: str, text2: str, text3: str, text4: str):
        buf = await render_clown(text1, text2, text3, text4)
        file = discord.File(buf, filename='clown.png')
        await ctx.send(file=file)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memes(bot))
