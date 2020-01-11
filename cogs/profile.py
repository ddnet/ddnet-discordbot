from datetime import datetime
from functools import partial
from io import BytesIO
from typing import Dict, List

import asyncpg
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from utils.image import center, round_rectangle
from utils.text import escape_backticks, plural

DIR = 'data/ddnet-stats'


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

    def generate_profile_image(self, data: asyncpg.Record) -> BytesIO:
        font_normal = ImageFont.truetype(f'{DIR}/fonts/normal.ttf', 24)
        font_bold = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 34)
        font_big = ImageFont.truetype(f'{DIR}/fonts/bold.ttf', 48)

        thresholds = {
            18000: ('justice_2', (184, 81, 50)),
            16000: ('back_in_the_days_3', (156, 162, 142)),
            14000: ('heartcore', (86, 79, 81)),
            12000: ('aurora', (55, 103, 156)),
            10000: ('narcissistic', (122, 32, 43)),
            9000:  ('aim_10', (93, 128, 144)),
            8000:  ('barren', (196, 172, 140)),
            7000:  ('back_in_time', (148, 156, 161)),
            6000:  ('nostalgia', (161, 140, 148)),
            5000:  ('sweet_shot', (229, 148, 166)),
            4000:  ('chained', (183, 188, 198)),
            3000:  ('intothenight', (60, 76, 89)),
            2000:  ('darkvine', (145, 148, 177)),
            1000:  ('crimson_woods', (108, 12, 12)),
            1:     ('kobra_4', (148, 167, 75)),
            0:     ('stronghold', (156, 188, 220)),
        }

        img, color = next(e for t, e in thresholds.items() if data['total_points'] >= t)
        base = Image.open(f'{DIR}/assets/backgrounds/{img}.png')

        canv = ImageDraw.Draw(base)

        width, height = base.size
        outer = 32
        inner = int(outer / 2)
        margin = outer + inner

        # draw bg
        size = (width - outer * 2, height - outer * 2)
        bg = round_rectangle(size, 12, color=(0, 0, 0, 150))
        base.alpha_composite(bg, dest=(outer, outer))

        # draw name
        try:
            flag = Image.open(f'{DIR}/assets/flags/{data["country"]}.png')
        except FileNotFoundError:
            flag = Image.open(f'{DIR}/assets/flags/UNK.png')

        flag_w, flag_h = flag.size

        name = ' ' + data['name']
        w, _ = font_bold.getsize(name)
        _, h = font_bold.getsize('yA')  # hardcoded to align names

        name_height = 50
        radius = int(name_height / 2)

        size = (flag_w + w + radius * 2, name_height)
        name_bg = round_rectangle(size, radius, color=(150, 150, 150, 75))
        base.alpha_composite(name_bg, dest=(margin, margin))

        x = margin + radius
        dest = (x, margin + center(flag_h, name_height))
        base.alpha_composite(flag, dest=dest)

        xy = (x + flag_w, margin + center(h, name_height))
        canv.text(xy, name, fill='white', font=font_bold)

        # draw points
        points_width = (width - margin * 2) / 3 + inner * 2

        x = margin + points_width + inner
        y = margin + name_height + inner

        xy = ((x, y), (x, height - margin))
        canv.line(xy, fill='white', width=3)

        text = f'#{data["total_rank"]}'
        w, h = font_big.getsize(text)
        xy = (margin + center(w, points_width - outer), y)
        canv.text(xy, text, fill='white', font=font_big)

        offset = h * 0.25  # true drawn height is only 3 / 4

        text = str(data['total_points'])
        w, h = font_bold.getsize(text)
        suffix = plural(data['total_points'], ' point').upper()
        w2, h2 = font_normal.getsize(suffix)

        x = margin + center(w + w2, points_width - outer)
        y = height - margin - offset

        canv.text((x, y - h), text, fill=color, font=font_bold)
        canv.text((x + w, y - h2), suffix, fill=color, font=font_normal)

        # draw ranks
        types = {
            'TEAM RANK ': (data['team_rank'], data['team_points']),
            'RANK ': (data['solo_rank'], data['solo_points'])
        }

        _, h = font_bold.getsize('A')
        yy = (margin + name_height + inner + h * 1.25, height - margin - h * 0.5)

        for (type_, (rank, points)), y in zip(types.items(), yy):
            line = [(type_, 'white', font_normal)]
            if rank is None:
                line.append(('UNRANKED', (150, 150, 150), font_bold))
            else:
                line.extend((
                    (f'#{rank}', 'white', font_bold),
                    ('   ', 'white', font_bold),  # border placeholder
                    (str(points), color, font_bold),
                    (plural(points, ' point').upper(), color, font_normal),
                ))

            x = width - margin
            for text, color_, font in line[::-1]:
                w, h = font.getsize(text)
                x -= w  # adjust x before drawing since we're drawing reverse
                if text == '   ':
                    xy = ((x + w / 2, y - h * 0.75), (x + w / 2, y - 1))  # fix line width overflow
                    canv.line(xy, fill=color_, width=1)
                else:
                    canv.text((x, y - h), text, fill=color_, font=font)

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
        extra = 2
        size = (plot_width * 2, (plot_height + extra * 2) * 2)
        plot = Image.new('RGBA', size, color=(0, 0, 0, 0))
        plot_canv = ImageDraw.Draw(plot)

        labels = []
        for dates, color in reversed(list(zip(data.values(), colors))):
            x = 0
            y = (plot_height + extra) * 2
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

            labels.append((margin - extra + y / 2, color))

        size = (plot_width, plot_height + extra * 2)
        plot = plot.resize(size, resample=Image.LANCZOS, reducing_gap=1.0)  # antialiasing
        base.alpha_composite(plot, dest=(margin, margin - extra))

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

        players = [p for p in players if p] or [ctx.author.display_name]
        if len(players) > 10:
            return await ctx.send('Can at most compare 10 players')

        data = {}
        query = 'SELECT timestamp, points FROM stats_finishes WHERE name = $1 ORDER BY timestamp;'
        for player in players:
            if player in data:
                continue

            records = await self.bot.pool.fetch(query, player)
            if not records:
                return await ctx.send(f'Could not find player ``{escape_backticks(player)}``')

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
