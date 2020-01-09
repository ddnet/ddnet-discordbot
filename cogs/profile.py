import json
from datetime import datetime
from functools import partial
from io import BytesIO
from typing import Dict, List, Tuple

import asyncpg
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.image import center, round_rectangle

DIR = 'data/ddnet-stats'

COLOR_DEFAULT = (255, 255, 255)
COLOR_GREY = (150, 150, 150)


def get_background(points: int) -> Tuple[Image.Image, Tuple[int, int, int]]:
    with open(f'{DIR}/assets/backgrounds/thresholds.json', 'r', encoding='utf-8') as f:
        thresholds = json.loads(f.read())

    for threshold, (background, color) in thresholds.items():
        if points <= int(threshold):
            break

    image = Image.open(f'{DIR}/assets/backgrounds/{background}.png').convert('RGBA')
    color = tuple(color)
    return image, color

def get_flag(country: str) -> Image.Image:
    with open(f'{DIR}/assets/flags/valid_flags.json', 'r', encoding='utf-8') as f:
        flags = json.loads(f.read())

    country = country.strip()
    flag = country if country in flags else 'UNK'
    return Image.open(f'{DIR}/assets/flags/{flag}.png')

def plural(value: int, name: str) -> str:
    if abs(value) == 1:
        return name

    if name.isupper():
        return f'{name}S'
    else:
        return f'{name}s'

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
        # Fonts
        font_normal_24 = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 24)
        font_bold_38 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 38)
        font_bold_48 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 48)
        font_bold_36 = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 36)

        base, colored = get_background(stats['total_points'])
        canv = ImageDraw.Draw(base)

        bg = round_rectangle((736, 192), 12, color=(0, 0, 0, 175))
        base.alpha_composite(bg, dest=(32, 32))

        # Name field
        name = stats['name']
        w, _ = font_bold_38.getsize(name)
        size = (16 + w + 39 + 25 * 2, 50)
        name_bg = round_rectangle(size, 26, color=(150, 150, 150, 75))
        base.alpha_composite(name_bg, dest=(48, 48))

        flag = get_flag(stats['country'])
        base.alpha_composite(flag, (73, 59))

        canv.text((124, 48), name, COLOR_DEFAULT, font_bold_38)

        # Points field

        # First row
        rank = stats['total_rank']

        text_width = font_bold_48.getsize(f'#{rank}')[0]
        width = center(text_width, 284) + 24
        canv.text((width, 112), f'#{rank}', fill=COLOR_DEFAULT, font=font_bold_48)

        # Second row
        points = stats['total_points']
        suffix = plural(points, ' POINT')

        text_width = font_bold_36.getsize(str(points))[0] + font_normal_24.getsize(suffix)[0]
        width = center(text_width, 284) + 24
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

    def generate_points_image(self, data: Dict[str, List[asyncpg.Record]]) -> BytesIO:
        font_small = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 16)

        color_light = (100, 100, 100)
        color_dark = (50, 50, 50)
        colors = (
            'orange',
            'red',
            'forestgreen',
            'dodgerblue',
            'orangered',
            'orchid',
            'burlywood',
            'darkcyan',
            'royalblue',
            'olive',
        )

        base = Image.open(f'{DIR}/assets/points_background.png')
        canv = ImageDraw.Draw(base)

        width, height = base.size
        margin = 50

        plot_width = width - margin * 2
        plot_height = height - margin * 2

        end_date = datetime.utcnow().date()
        start_date = min(r['timestamp'] for d in data.values() for r in d)
        start_date = min(start_date, end_date.replace(year=end_date.year - 1))

        total_points = max(sum(r['points'] for r in d) for d in data.values())
        total_points = max(total_points, 1000)

        days_mult = plot_width / (end_date - start_date).days
        points_mult = plot_height / total_points

        # draw area bg
        bg = Image.new('RGBA', (plot_width, plot_height), color=(0, 0, 0, 100))
        base.alpha_composite(bg, dest=(margin, margin))

        # draw days TODO: optimize
        prev_x = margin
        for year in range(start_date.year, end_date.year + 1):
            date = datetime(year=year, month=1, day=1).date()
            if date < start_date:
                continue

            x = margin + (date - start_date).days * days_mult
            xy = ((x, margin), (x, height - margin))
            canv.line(xy, fill=color_dark, width=1)

            text = str(year - 1)
            w, h = font_small.getsize(text)
            area_width = x - prev_x
            if w <= area_width:
                xy = (prev_x + center(w, area_width), height - margin + h)
                canv.text(xy, text, fill=color_light, font=font_small)

            prev_x = x

        # draw points
        thresholds = {
            15000: 5000,
            10000: 2500,
            5000:  2000,
            3000:  1000,
            1000:  500,
            0:     250,
        }

        steps = next(s for t, s in thresholds.items() if total_points > t)
        w, _ = font_small.getsize('00.0K')  # max points label width
        points_margin = center(w, margin)
        for points in range(0, total_points + 1, int(steps / 5)):
            y = height - margin - points * points_mult
            xy = ((margin, y), (width - margin - 1, y))

            if points % steps == 0:
                canv.line(xy, fill=color_light, width=2)

                text = humanize_points(points)
                w, h = font_small.getsize(text)
                xy = (margin - points_margin - w, y + center(h))
                canv.text(xy, text, fill=color_light, font=font_small)
            else:
                canv.line(xy, fill=color_dark, width=1)

        # draw players
        size = (plot_width * 2, (plot_height + 2) * 2)
        plot = Image.new('RGBA', size, color=(0, 0, 0, 0))
        plot_canv = ImageDraw.Draw(plot)

        labels = []
        for dates, color in reversed(list(zip(data.values(), colors))):
            x = 0
            y = plot_height * 2
            xy = [(x, y)]

            prev_date = start_date
            for date, points in dates:
                delta = (date - prev_date).days * days_mult * 2
                x += delta
                if delta / (plot_width * 2) > 0.1:
                    xy.append((x, y))

                y -= points * points_mult * 2
                xy.append((x, y))

                prev_date = date

            if prev_date != end_date:
                xy.append((plot_width * 2, y))

            plot_canv.line(xy, fill=color, width=6)

            labels.append((margin + y / 2, color))

        size = (plot_width, plot_height + 2)
        plot = plot.resize(size, resample=Image.LANCZOS, reducing_gap=1.0)  # antialiasing
        base.alpha_composite(plot, dest=(margin, margin))

        # remove overlapping labels TODO: optimize
        _, h = font_small.getsize('0')
        offset = center(h)
        for _ in range(len(labels)):
            labels.sort()
            for i, (y1, _) in enumerate(labels):
                if i == len(labels) - 1:
                    break

                y2 = labels[i + 1][0]
                if y1 - offset >= y2 + offset and y2 - offset >= y1 + offset:
                    labels[i] = ((y1 + y2) / 2, 'white')
                    del labels[i + 1]

        # draw player points
        for y, color in labels:
            points = int((height - margin - y) / points_mult)
            text = humanize_points(points)
            xy = (width - margin + points_margin, y + offset)
            canv.text(xy, text, fill=color, font=font_small)

        # draw header
        size = 24
        space = size / 3
        while True:
            font = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', size)
            combined = sum(font.getsize(p)[0] for p in data) + space * (4 * len(data) - 2)
            if combined <= plot_width:
                break

            size -= 1
            space -= 1 / 3

        x = margin
        for player, color in zip(data, colors):
            y = center(space, margin)
            xy = ((x, y), (x + space, y + space))
            canv.rectangle(xy, fill=color)
            x += space * 2

            w, _ = font.getsize(player)
            _, h = font.getsize('yA')  # max name height, needs to be hardcoded to align names
            xy = (x, center(h, margin))
            canv.text(xy, player, fill='white', font=font)
            x += w + space * 2

        buf = BytesIO()
        base.save(buf, format='png')
        buf.seek(0)
        return buf

    @commands.command()
    async def points(self, ctx: commands.Context, *players: str):
        await ctx.trigger_typing()

        players = players or [ctx.author.display_name]
        if len(players) > 10:
            return await ctx.send('Can at most compare 10 players')

        data = {}
        query = 'SELECT timestamp, points FROM stats_finishes WHERE name = $1 ORDER BY timestamp;'
        for player in players:
            if player in data:
                continue

            records = await self.bot.pool.fetch(query, player)
            if not records:
                return await ctx.send(f'Could not find player ``{player}``')

            data[player] = records

        fn = partial(self.generate_points_image, data)
        buf = await self.bot.loop.run_in_executor(None, fn)
        file = discord.File(buf, filename=f'points_{"_".join(players)}.png')
        await ctx.send(file=file)

    @points.error
    async def points_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.ArgumentParsingError):
            await ctx.send('<players> contain unmatched or unescaped quotation mark')


def setup(bot: commands.Bot):
    bot.add_cog(Profile(bot))
