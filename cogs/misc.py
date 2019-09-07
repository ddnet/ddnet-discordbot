#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional, Union

import discord
import psutil
from discord.ext import commands

from utils.misc import run_process

log = logging.getLogger(__name__)

GH_URL = 'https://github.com/12pm/ddnet-discordbot'

def get_weather_emoji(condition: int) -> str:
    # https://openweathermap.org/weather-conditions
    if 200 <= condition < 300:
        # Thunderstorm
        return '\N{CLOUD WITH LIGHTNING}'
    elif 300 <= condition < 400:
        # Drizzle
        return '\N{CLOUD WITH RAIN}'
    elif 500 <= condition < 600:
        # Rain
        return '\N{CLOUD WITH RAIN}'
    elif 600 <= condition < 700:
        # Snow
        return '\N{SNOWFLAKE}'
    elif 700 <= condition < 800:
        # Atmosphere
        return '\N{DASH SYMBOL}'
    elif condition == 800:
        # Clear
        return '\N{BLACK SUN WITH RAYS}'
    elif 801 <= condition < 810:
        # Clouds
        return '\N{CLOUD}'

def get_time_emoji(now: int, sunrise: int, sunset: int) -> str:
    return '\N{SUN WITH FACE}' if sunrise <= now < sunset else '\N{FULL MOON WITH FACE}'


class MemberBestMatch(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        if not ctx.guild:
            raise commands.BadArgument('Not in a guild context')

        argument = argument.lower()
        matches = {}

        # lookup by nickname first
        for member in ctx.guild.members:
            if not member.nick:
                continue

            nick = member.nick.lower()
            if argument in nick and nick not in matches:
                matches[nick] = member

        for member in ctx.guild.members:
            name = member.name.lower()
            if argument in name and name not in matches:
                matches[name] = member

        if not matches:
            raise commands.BadArgument('Could not find a matching member')

        matches = sorted(matches.items(), key=lambda m: (m[0].index(argument), m[0]))
        return matches[0][1]


def human_timedelta(delta: timedelta, accuracy=4) -> str:
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

    units = (
        ('d', days),
        ('h', hours),
        ('m', minutes),
        ('s', seconds),
    )

    return ' '.join([f'{v}{u}' for u, v in units if v > 0][:accuracy])


class Misc(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.gays = ('gay', 'ur gay', 'you\'re gay', 'you are gay')
        self.process = psutil.Process()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.lower() in self.gays:
            await message.add_reaction('<:no:389587856093478915>')
            await message.add_reaction('🇺')

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content.lower() not in self.gays and after.content.lower() in self.gays:
            await after.add_reaction('<:no:389587856093478915>')
            await after.add_reaction('🇺')

    def get_uptime(self) -> str:
        return human_timedelta(datetime.utcnow() - self.bot.start_time)

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

        latency = self.bot.latency * 1000
        embed.add_field(name='Bot', value=f'{self.get_uptime()} Uptime\n{latency:.2f}ms Latency')

        commits = await self.get_latest_commits()
        embed.add_field(name='Latest commits', value=commits)

        embed.set_footer(text='Made by jao#3750 with Python')

        await ctx.send(embed=embed)

    @commands.command()
    async def commandstats(self, ctx: commands.Context):
        """Shows command stats"""
        query = 'SELECT command, count(*) AS uses FROM stats_commands GROUP BY command ORDER BY uses DESC;'
        stats = await self.bot.pool.fetch(query)

        prefix = self.bot.command_prefix
        width = len(max((s['command'] for s in stats[:20]), key=len))
        desc = '\n'.join(f'`{prefix}{c}{"." * (width - len(c))}:` {u}' for c, u in stats[:20])
        total = sum(s['uses'] for s in stats)

        embed = discord.Embed(title='Command Stats', description=desc, color=discord.Color.blurple())
        embed.set_footer(text=f'{total} total')

        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx: commands.Context, *, user: Union[discord.Member, discord.User]=None):
        """Shows the avatar of a user"""
        await ctx.trigger_typing()

        user = user or ctx.author
        avatar = user.avatar_url_as(static_format='png')
        buf = BytesIO()
        await avatar.save(buf)

        ext = 'gif' if user.is_avatar_animated() else 'png'
        file = discord.File(buf, filename=f'avatar_{user.name}.{ext}')
        await ctx.send(file=file)

    @avatar.error
    async def avatar_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BadUnionArgument):
            await ctx.send('Could not find that user')

    async def fetch_weather_data(self, city: str) -> dict:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': city,
            'APPID': self.bot.config.get('WEATHER_API', 'KEY')
        }

        async with self.bot.session.get(url, params=params) as resp:
            js = await resp.json()
            if resp.status == 200:
                return js
            elif resp.status == 404:
                raise RuntimeError('Could not find that city')
            else:
                fmt = 'Failed to fetch weather data for %r: %s (status code: %d %s)'
                log.error(fmt, city, js['message'], resp.status, resp.reason)
                raise RuntimeError('Could not fetch weather information')

    @commands.command()
    async def weather(self, ctx: commands.Context, *, city: str):
        """Shows weather information of a city"""
        try:
            data = await self.fetch_weather_data(city)
        except RuntimeError as exc:
            return await ctx.send(exc)

        city = data['name']
        country = data['sys']['country']
        condition = data['weather'][0]['id']
        description = data['weather'][0]['description']
        temp = data['main']['temp']  # K
        celcius = temp - 273.15
        rankine = temp * 9/5
        fahrenheit = temp * 9/5 - 459.67
        wind = data['wind']['speed']  # m/s
        humidity = data['main']['humidity']  # %
        cloudiness = data['clouds']['all']  # %
        emoji = get_weather_emoji(condition)

        msg = f':flag_{country.lower()}: |  **Weather for {city}, {country}**\n' \
              f'**Weather:** {emoji} ({description})\n' \
              f'**Temp:** {celcius:0.1f} °C / {fahrenheit:0.1f} °F / {rankine:0.1f} °R\n' \
              f'**Wind:** {wind} m/s **Humidity:** {humidity}% **Cloudiness:** {cloudiness}%'

        await ctx.send(msg)

    @commands.command()
    async def time(self, ctx: commands.Context, *, city: str):
        """Shows the time and date of a city"""
        now = datetime.utcnow()

        try:
            data = await self.fetch_weather_data(city)
        except RuntimeError as exc:
            return await ctx.send(exc)

        offset = data['timezone']
        utc = offset / 60 / 60
        utc = int(utc) if utc % 1 == 0 else round(utc, 1)
        time = now + timedelta(seconds=offset)
        sunrise = data['sys']['sunrise']
        sunset = data['sys']['sunset']
        emoji = get_time_emoji(now.timestamp(), sunrise, sunset)

        await ctx.send(f'{emoji} **{time.strftime("%d/%m/%Y %H:%M:%S")}** (UTC {utc:+})')

    @commands.command(aliases=['c'])
    async def cringe(self, ctx: commands.Context, *, user: Optional[MemberBestMatch]):
        """Shows a message by the cringe lord"""
        content = user.mention if user else None
        file = discord.File('data/cringe.png')
        await ctx.send(content, file=file)

    @commands.command()
    @commands.guild_only()
    async def emojis(self, ctx: commands.Context):
        """Return a zip file with all guild emojis"""
        guild = ctx.guild

        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for emoji in guild.emojis:
                ext = 'gif' if emoji.animated else 'png'
                bytes_ = await emoji.url.read()
                zf.writestr(f'{emoji.name}.{ext}', bytes_)

        buf.seek(0)

        file = discord.File(buf, f'emojis_{guild}.zip')
        await ctx.send(file=file)


def setup(bot: commands.Bot):
    bot.add_cog(Misc(bot))
