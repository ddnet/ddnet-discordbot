import json
from functools import partial
from io import BytesIO
from typing import Tuple

import asyncpg
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

DIR = 'data/ddnet-stats'

COLOR_DEFAULT = (255, 255, 255)
COLOR_GREY = (150, 150, 150)


def get_background(points: int) -> Tuple[Image.Image, Tuple[int, int, int]]:
    with open(f'{DIR}/assets/backgrounds/thresholds.json', 'r', encoding='utf-8') as f:
        thresholds = json.loads(f.read())

    for threshold, (background, color) in thresholds.items():
        if points <= int(threshold):
            break

    image = Image.open(f'{DIR}/assets/backgrounds/{background}.png')
    color = tuple(color)
    return image, color

def get_flag(country: str) -> Image.Image:
    with open(f'{DIR}/assets/flags/valid_flags.json', 'r', encoding='utf-8') as f:
        flags = json.loads(f.read())

    country = country.strip()
    flag = country if country in flags else 'UNK'
    return Image.open(f'{DIR}/assets/flags/{flag}.png')

def center_text(width_context: int, width_text: int) -> int:
    return (width_context - width_text) / 2

def plural(value: int, name: str) -> str:
    if abs(value) == 1:
        return name

    if name.isupper():
        return f'{name}S'
    else:
        return f'{name}s'


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def generate_profile_image(self, stats: asyncpg.Record) -> BytesIO:
        base = Image.new('RGBA', (800, 256))
        # Fonts
        font_normal_24 = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 24)
        font_bold_38 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 38)
        font_bold_48 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 48)
        font_bold_36 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 36)

        background, colored = get_background(stats['total_points'])
        base.paste(background)
        box = Image.open(f'{DIR}/assets/box.png').convert('RGBA')  # Context field
        base.alpha_composite(box, (32, 32))
        canv = ImageDraw.Draw(base)

        # Name field
        name = stats['name']
        name_bg_corner = Image.open(f'{DIR}/assets/name_badge.png').convert('RGBA')

        rect_width = 124 + font_bold_38.getsize(name)[0]
        base.alpha_composite(name_bg_corner, (48, 48))
        name_bg = Image.new('RGBA', (abs(73 - rect_width), 50), (150, 150 , 150, 74))
        base.alpha_composite(name_bg, (73, 48))
        base.alpha_composite(name_bg_corner.rotate(180), (rect_width, 48))

        flag = get_flag(stats['country'])
        base.alpha_composite(flag, (73, 59))

        canv.text((124, 48), name, COLOR_DEFAULT, font_bold_38)

        # Points field

        # First row
        rank = stats['total_rank']

        text_width = font_bold_48.getsize(f'#{rank}')[0]
        width = center_text(284, text_width) + 24
        canv.text((width, 112), f'#{rank}', fill=COLOR_DEFAULT, font=font_bold_48)

        # Second row
        points = stats['total_points']
        suffix = plural(points, ' POINT')

        text_width = font_bold_36.getsize(str(points))[0] + font_normal_24.getsize(suffix)[0]
        width = center_text(284, text_width) + 24
        canv.text((width, 163), str(points), fill=colored, font=font_bold_36)
        width += font_bold_36.getsize(str(points))[0]
        canv.text((width, 174), suffix, fill=colored, font=font_normal_24)

        # Border
        canv.line(((312, 112), (312, 207)), fill=COLOR_DEFAULT, width=3)

        # Ranks field
        # TODO: clean this up
        borders = ((125, 154), (165, 194))

        conf = (
            ('TEAM RANK', stats['team_rank'], stats['team_points'], (119, 130)),
            ('RANK', stats['solo_rank'], stats['solo_points'], (159, 170))
        )

        tmp_abc = []
        for rank_type, rank, points, heights in conf:
            major, minor = heights
            abc = [[f'{rank_type} ', font_normal_24, COLOR_DEFAULT, minor]]
            if rank:
                points_, text = plural(points, 'POINT').split(' ')
                abc.extend((
                    ['#', font_bold_36, COLOR_DEFAULT, major],
                    [str(rank), font_bold_36, COLOR_DEFAULT, major],
                    ['   ', font_bold_36, COLOR_DEFAULT, major],  # Placeholder for the border
                    [points_, font_bold_36, colored, major],
                    [f' {text}', font_normal_24, colored, minor]
                ))
            else:
                abc.append(['UNRANKED', font_bold_36, COLOR_GREY, major])

            tmp_abc.append(abc)

        teamrank_abc, rank_abc = tmp_abc
        for n, abc in enumerate((teamrank_abc, rank_abc)):
            width = 752
            for text, font, color, height in abc[::-1]:  # Draw from right to left
                # Account for drawn text width before drawing since text is drawn left to right
                width -= font.getsize(text)[0]
                if text == '   ':
                    # Add half the width again since the border should be in the middle
                    x = width + font.getsize(text)[0] / 2
                    canv.line(((x, borders[n][0]), (x, borders[n][1])), fill=COLOR_DEFAULT, width=1)
                else:
                    canv.text((width, height), text, color, font=font)

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command(aliases=['player', 'points'])
    async def profile(self, ctx: commands.Context, *, player: str=None):
        await ctx.trigger_typing()

        player = player or ctx.author.display_name
        for user in ctx.message.mentions:
            player = player.replace(user.mention, user.display_name)

        query = 'SELECT * FROM stats_players WHERE name = $1;'
        record = await self.bot.pool.fetchrow(query, player)
        if not record:
            return await ctx.send('Could not find that player')

        fn = partial(self.generate_profile_image, record)
        buf = await self.bot.loop.run_in_executor(None, fn)
        file = discord.File(buf, filename=f'profile_{player}.png')
        await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Profile(bot))
