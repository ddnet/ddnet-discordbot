#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import BytesIO
from typing import List

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.image import wrap_new
from utils.misc import executor

DIR = 'data/assets'


def wrap(font: ImageFont, text: str, line_width: int) -> List[str]:
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
        # register default layout memes
        for name in ('angry', 'drake', 'happy', 'sleep', 'teeward'):
            command = commands.Command(name=name, func=Memes.default)
            command.cog = self
            bot.add_command(command)

    @executor
    def generate(self, name: str, text1: str, text2: str=None) -> BytesIO:
        base = Image.open(f'{DIR}/memes/{name}.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 46)

        canv.text((600, 100), wrap(font, text1, 400), fill='black', font=font)
        if text2 is not None:
            canv.text((600, 500), wrap(font, text2, 400), fill='black', font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    async def default(self, ctx: commands.Context, text1: str, text2: str):
        buf = await self.generate(ctx.command.name, text1, text2)
        file = discord.File(buf, filename=f'{ctx.command.name}.png')
        await ctx.send(file=file)

    @commands.command()
    async def ohno(self, ctx: commands.Context, *, text: str):
        buf = await self.generate('ohno', text)
        file = discord.File(buf, filename='ohno.png')
        await ctx.send(file=file)

    @executor
    def generate_teebob(self, text: str) -> BytesIO:
        base = Image.open(f'{DIR}/memes/teebob.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 40)

        xy = ((100, 110), (360, 370))
        wrap_new(canv, xy, text, font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command()
    async def teebob(self, ctx: commands.Context, *, text: str):
        buf = await self.generate_teebob(text)
        file = discord.File(buf, filename='teebob.png')
        await ctx.send(file=file)

    @executor
    def generate_clown(self, text1: str, text2: str, text3: str, text4: str) -> BytesIO:
        base = Image.open(f'{DIR}/memes/clown.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 30)

        canv.text((10, 10), wrap(font, text1, 310), fill='black', font=font)
        canv.text((10, 180), wrap(font, text2, 310), fill='black', font=font)
        canv.text((10, 360), wrap(font, text3, 310), fill='black', font=font)
        canv.text((10, 530), wrap(font, text4, 310), fill='black', font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command()
    async def clown(self, ctx: commands.Context, text1: str, text2: str, text3: str, text4: str):
        buf = await self.generate_clown(text1, text2, text3, text4)
        file = discord.File(buf, filename='clown.png')
        await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Memes(bot))
