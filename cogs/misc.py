#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import zipfile
from datetime import datetime, timedelta
from io import BytesIO

import discord
import psutil
from discord.ext import commands

from data.countryflags import FLAG_UNK
from utils.misc import run_process
from utils.text import human_timedelta

log = logging.getLogger(__name__)

GH_URL = 'https://github.com/12pm/ddnet-discordbot'


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process = psutil.Process()

    @commands.command()
    async def invite(self, ctx: commands.Context):
        perms = discord.Permissions.none()
        perms.send_messages = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_messages = True
        perms.attach_files = True
        perms.read_message_history = True
        perms.external_emojis = True
        perms.add_reactions = True
        perms.manage_webhooks = True
        invite = discord.utils.oauth_url(self.bot.user.id, permissions=perms)
        await ctx.send(f'<{invite}>')

    async def get_latest_commits(self, num: int=3) -> str:
        fmt = fr'[\`%h\`]({GH_URL}/commit/%H) %s (%ar)'
        cmd = f'git log master -{num} --no-merges --format="{fmt}"'
        stdout, _ = await run_process(cmd)
        return stdout

    @commands.command()
    async def about(self, ctx: commands.Context):
        """Shows information about the bot"""
        title = 'Discord bot for DDraceNetwork'
        embed = discord.Embed(title=title, color=0xFEA500, url='https://ddnet.tw')

        embed.set_author(name=self.bot.user, icon_url=self.bot.user.avatar_url_as(format='png'))

        channels = sum(len(g.voice_channels + g.text_channels) for g in self.bot.guilds)
        stats = f'{len(self.bot.guilds)} Guilds\n{channels} Channels\n{len(self.bot.users)} Users'
        embed.add_field(name='Stats', value=stats)

        memory = self.process.memory_full_info().uss / 1024 ** 2
        cpu = self.process.cpu_percent() / psutil.cpu_count()
        threads = self.process.num_threads()
        embed.add_field(name='Process', value=f'{memory:.2f} MiB\n{cpu:.2f}% CPU\n{threads} Threads')

        delta = datetime.utcnow() - self.bot.start_time
        uptime = human_timedelta(delta.total_seconds(), brief=True)
        latency = self.bot.latency * 1000
        embed.add_field(name='Bot', value=f'{uptime} Uptime\n{latency:.2f}ms Latency')

        commits = await self.get_latest_commits()
        embed.add_field(name='Latest commits', value=commits)

        embed.set_footer(text=f'Made by jao#3750 with Python (discord.py {discord.__version__})')

        await ctx.send(embed=embed)

    @commands.command()
    async def commandstats(self, ctx: commands.Context):
        """Shows command stats"""
        query = 'SELECT command, COUNT(*) AS uses FROM stats_commands GROUP BY command ORDER BY uses DESC;'
        stats = await self.bot.pool.fetch(query)
        stats = [s for s in stats if self.bot.get_command(s['command']) is not None]

        prefix = self.bot.command_prefix
        width = len(max((s['command'] for s in stats[:20]), key=len))
        desc = '\n'.join(f'`{prefix}{c}{"." * (width - len(c))}:` {u}' for c, u in stats[:20])
        total = sum(s['uses'] for s in stats)

        embed = discord.Embed(title='Command Stats', description=desc, color=discord.Color.blurple())
        embed.set_footer(text=f'{total} total')

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx: commands.Context, *, user: discord.User=None):
        """Shows the avatar of a user"""
        await ctx.trigger_typing()

        user = user or ctx.author
        avatar = user.avatar_url_as(static_format='png')
        buf = BytesIO()
        try:
            await avatar.save(buf)
        except discord.NotFound:
            return await ctx.send('Could not get that user\'s avatar')

        ext = 'gif' if user.is_avatar_animated() else 'png'
        file = discord.File(buf, filename=f'avatar_{user.name}.{ext}')
        await ctx.send(file=file)

    @avatar.error
    async def avatar_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Could not find that user')

    async def fetch_weather_data(self, city: str) -> dict:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'APPID': self.bot.config.get('WEATHER_API', 'KEY'),
            'q': city,
            'units': 'metric'
        }

        async with self.bot.session.get(url, params=params) as resp:
            js = await resp.json()
            if resp.status == 200:
                return js
            elif resp.status == 404:
                raise RuntimeError('Could not find that city')
            else:
                fmt = 'Failed to fetch weather data for city %r: %s (status code: %d %s)'
                log.error(fmt, city, js['message'], resp.status, resp.reason)
                raise RuntimeError('Could not fetch weather information')

    @commands.command()
    async def weather(self, ctx: commands.Context, *, city: str):
        """Show weather information of a city"""
        try:
            data = await self.fetch_weather_data(city)
        except RuntimeError as exc:
            return await ctx.send(exc)

        city = data['name']
        country = data['sys'].get('country')
        condition = data['weather'][0]['id']
        description = data['weather'][0]['description']
        temp = data['main']['temp']  # °C
        feels_like = data['main']['feels_like']  # °C
        wind = data['wind']['speed']  # m/s
        humidity = data['main']['humidity']  # %
        cloudiness = data['clouds']['all']  # %

        if country is None:
            flag = FLAG_UNK
        else:
            flag = f':flag_{country.lower()}:'
            city += f', {country}'

        # https://openweathermap.org/weather-conditions
        conditions = {
            (200, 299): '🌩️',  # thunderstorm
            (300, 399): '🌧️',  # drizzle
            (500, 599): '🌧️',  # rain
            (600, 699): '❄️',  # snow
            (700, 799): '💨',  # atmosphere
            (800, 800): '☀️',  # clear
            (801, 809): '☁️',  # clouds
        }

        emoji = next((e for c, e in conditions.items() if c[0] <= condition <= c[1]), '')

        msg = f'{flag} |  **Weather for {city}**\n' \
              f'**Weather:** {emoji} ({description})\n' \
              f'**Temp:** {temp} °C **Feels like:** {feels_like} °C\n' \
              f'**Wind:** {wind} m/s **Humidity:** {humidity}% **Cloudiness:** {cloudiness}%'

        await ctx.send(msg)

    @commands.command()
    async def time(self, ctx: commands.Context, *, city: str):
        """Show the date and time of a city"""
        try:
            data = await self.fetch_weather_data(city)
        except RuntimeError as exc:
            return await ctx.send(exc)

        now = datetime.utcnow()

        offset = data['timezone']
        sunrise = data['sys']['sunrise']
        sunset = data['sys']['sunset']

        emoji = '🌞' if sunrise <= now.timestamp() < sunset else '🌝'
        timestamp = (now + timedelta(seconds=offset)).strftime('%d/%m/%Y %H:%M:%S')
        hours, minutes = divmod(offset / 60, 60)

        await ctx.send(f'{emoji} **{timestamp}** (UTC {hours:+03.0f}:{minutes:02.0f})')

    @commands.command()
    @commands.guild_only()
    async def emojis(self, ctx: commands.Context):
        """Returns a zip file with all guild emojis"""
        guild = ctx.guild
        if not guild.emojis:
            return await ctx.send('This guild doesn\'t own any emojis')

        async with ctx.typing():
            count = [0, 0]
            emojis = []  # can't be a dict since emoji names aren't unique
            for emoji in guild.emojis:
                count[emoji.animated] += 1
                ext = 'gif' if emoji.animated else 'png'
                data = await emoji.url.read()
                emojis.append((f'{emoji.name}.{ext}', data))

            limit = guild.emoji_limit
            msg = f'Static: {count[0]}/{limit} Animated: {count[1]}/{limit}'

            buf = BytesIO()
            with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for emoji in emojis:
                    zf.writestr(*emoji)

            buf.seek(0)
            file = discord.File(buf, f'emojis_{guild}.zip')

            await ctx.send(msg, file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))
