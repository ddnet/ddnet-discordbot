import json
from datetime import datetime
from functools import partial
from io import BytesIO
from typing import Dict, List, Tuple

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

def center(text_size: int, area_size: int=0) -> int:
    return int((area_size - text_size) / 2)

def humanize_points(points: int) -> str:
    if points < 1000:
        return str(points)
    else:
        points = round(points / 1000, 1)
        if points % 1 == 0:
            points = int(points)

        return f'{points}K'


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
                text = plural(points, ' POINT')
                abc.extend((
                    ['#', font_bold_36, COLOR_DEFAULT, major],
                    [str(rank), font_bold_36, COLOR_DEFAULT, major],
                    ['   ', font_bold_36, COLOR_DEFAULT, major],  # Placeholder for the border
                    [str(points), font_bold_36, colored, major],
                    [text, font_normal_24, colored, minor]
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

    @commands.command()
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

    def generate_points_image(self, players: List[str], data: List[Dict]) -> BytesIO:
        font_small = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 32)
        font_big = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 48)

        color_light = (100, 100, 100)
        color_dark = (50, 50, 50)
        colors = (
            'orange',
            'red',
            'green',
            'lightblue',
            'purple',
        )

        base = base = Image.open(f'{DIR}/assets/points_background.png')
        canv = ImageDraw.Draw(base)

        width, height = base.size
        margin = 100

        end_date = datetime.utcnow().date()
        start_date = min(t for d in data for t in d)
        start_date = min(start_date, end_date.replace(year=end_date.year - 1))

        total_points = max(sum(d.values()) for d in data)
        total_points = max(total_points, 1000)

        days_mult = (width - margin * 2) / (end_date - start_date).days
        points_mult = (height - margin * 2) / total_points

        # draw area bg
        size = (width - margin * 2, height - margin * 2)
        bg = Image.new('RGBA', size, color=(0, 0, 0, 100))
        base.alpha_composite(bg, dest=(margin, margin))

        # draw days TODO: optimize
        prev_x = margin
        for year in range(start_date.year, end_date.year + 1):
            date = datetime(year=year, month=1, day=1).date()
            if date < start_date:
                continue

            x = margin + (date - start_date).days * days_mult
            xy = ((x, margin), (x, height - margin))
            canv.line(xy, fill=color_dark, width=2)

            text = str(year - 1)
            w, h = font_small.getsize(text)
            area_width = x - prev_x
            if w < area_width:
                xy = (prev_x + center(w, area_width), height - margin + h)
                canv.text(xy, text, fill=color_light, font=font_small)

            prev_x = x

        # draw points
        thresholds = {
            15000: 5000,
            10000: 2500,
            7500:  2000,
            5000:  1000,
            1000:  500,
            0:     250,
        }

        steps = next(s for t, s in thresholds.items() if total_points > t)

        for points in range(0, total_points + 1, int(steps / 5)):
            y = height - margin - points * points_mult
            xy = ((margin, y), (width - margin, y))

            if points % steps == 0:
                canv.line(xy, fill=color_light, width=4)

                text = humanize_points(points)
                w, h = font_small.getsize(text)
                xy = (margin - w - 8, y + center(h))
                canv.text(xy, text, fill=color_light, font=font_small)
            else:
                canv.line(xy, fill=color_dark, width=2)

        # draw players
        lables = []
        for dates, color in reversed(list(zip(data, colors))):
            x = margin
            y = height - margin
            xy = [(x, y)]

            prev_date = next(iter(dates))
            if prev_date != start_date:
                x += (prev_date - start_date).days * days_mult
                xy.append((x, y))

            total = 0
            for date, points in dates.items():
                x += (date - prev_date).days * days_mult
                y -= points * points_mult
                xy.append((x, y))

                prev_date = date
                total += points

            x = width - margin
            if end_date not in dates:
                xy.append((x, y))

            canv.line(xy, fill=color, width=6)

            lables.append((y, color))

        # remove overlapping lables TODO: optimize
        _, h = font_small.getsize('0')
        offset = center(h)
        for _ in range(len(lables)):
            lables.sort()
            for i, (y1, _) in enumerate(lables):
                if i == len(lables) - 1:
                    break

                y2 = lables[i + 1][0]
                if y1 - offset >= y2 + offset and y2 - offset >= y1 + offset:
                    lables[i] = ((y1 + y2) / 2, 'white')
                    del lables[i + 1]

        # draw player points
        for y, color in lables:
            points = (height - margin - y) / points_mult
            text = humanize_points(points)
            xy = (width - margin + 8, y + offset)
            canv.text(xy, text, fill=color, font=font_small)

        # draw header
        size = 16
        x = margin
        y = center(size, margin)
        for player, color in zip(players, colors):
            xy = ((x, y), (x + size, y + size))
            canv.rectangle(xy, fill=color)
            x += size * 2

            w, _ = font_big.getsize(player)
            _, h = font_big.getsize('yA')  # needs to be hardcoded to align names
            xy = (x, center(h, margin))
            canv.text(xy, player, fill=(255, 255, 255), font=font_big)
            x += w + size * 2

        base.thumbnail((width / 2, height / 2), resample=Image.LANCZOS)  # antialiasing

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command()
    async def points(self, ctx: commands.Context, *players: str):
        await ctx.trigger_typing()

        players = set(players) or [ctx.author.display_name]
        if len(players) > 5:
            return await ctx.send('Can at most compare 5 players')

        data = []
        for player in players:
            query = 'SELECT timestamp, points FROM stats_finishes WHERE name = $1 ORDER BY timestamp;'
            records = await self.bot.pool.fetch(query, player)
            if not records:
                return await ctx.send(f'Could not find ``{player}``')

            data.append({t: p for t, p in records})

        fn = partial(self.generate_points_image, players, data)
        buf = await self.bot.loop.run_in_executor(None, fn)
        file = discord.File(buf, filename=f'points_{"_".join(players)}.png')
        await ctx.send(file=file)

    @points.error
    async def points_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.ArgumentParsingError):
            await ctx.send('<players> contain unmatched or unescaped quotation mark')


def setup(bot: commands.Bot):
    bot.add_cog(Profile(bot))
