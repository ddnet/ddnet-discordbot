#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io import BytesIO
from typing import List

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.image import save, auto_wrap_text
from utils.misc import executor

DIR = 'data/assets'


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

        font1, text1 = auto_wrap_text(font, text1, 400, 325)
        canv.text((575, 50), text1, fill='black', font=font1)
        font2, text2 = auto_wrap_text(font, text2, 400, 400)
        canv.text((575, 475), text2, fill='black', font=font2)

        return save(base)

    async def default(self, ctx: commands.Context, text1: str, text2: str):
        try:
            buf = await self.generate(ctx.command.name, text1, text2)
        except ValueError as exc:
            return await ctx.send(exc)

        file = discord.File(buf, filename=f'{ctx.command.name}.png')
        await ctx.send(file=file)

    @executor
    def generate_ohno(self, text: str) -> BytesIO:
        base = Image.open(f'{DIR}/memes/ohno.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 40)

        font1, text1 = auto_wrap_text(font, text, 400, 125)
        canv.text((575, 50), text1, fill='black', font=font1)

        return save(base)

    @commands.command()
    async def ohno(self, ctx: commands.Context, *, text: str):
        try:
            buf = await self.generate_ohno(text)
        except ValueError as exc:
            return await ctx.send(exc)
        
        file = discord.File(buf, filename='teebob.png')
        await ctx.send(file=file)

    @executor
    def generate_teebob(self, text: str) -> BytesIO:
        base = Image.open(f'{DIR}/memes/teebob.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 40)

        font1, text1 = auto_wrap_text(font, text, 260, 260)
        canv.text((100, 110), text1, fill='black', font=font1)

        return save(base)

    @commands.command()
    async def teebob(self, ctx: commands.Context, *, text: str):
        try:
            buf = await self.generate_teebob(text)
        except ValueError as exc:
            return await ctx.send(exc)
        
        file = discord.File(buf, filename='teebob.png')
        await ctx.send(file=file)

    @executor
    def generate_clown(self, text1: str, text2: str, text3: str, text4: str) -> BytesIO:
        base = Image.open(f'{DIR}/memes/clown.png')
        canv = ImageDraw.Draw(base)
        font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 30)

        font1, text1 = auto_wrap_text(font, text1, 310, 150)
        canv.text((10, 10), text1, fill='black', font=font1)
        font2, text2 = auto_wrap_text(font, text2, 310, 150)
        canv.text((10, 180), text2, fill='black', font=font2)
        font3, text3 = auto_wrap_text(font, text3, 310, 150)
        canv.text((10, 360), text3, fill='black', font=font3)
        font4, text4 = auto_wrap_text(font, text4, 310, 150)
        canv.text((10, 530), text4, fill='black', font=font4)

        return save(base)

    @commands.command()
    async def clown(self, ctx: commands.Context, text1: str, text2: str, text3: str, text4: str):
        try:
            buf = await self.generate_clown(text1, text2, text3, text4)
        except ValueError as exc:
            return await ctx.send(exc)
        
        file = discord.File(buf, filename='clown.png')
        await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Memes(bot))
