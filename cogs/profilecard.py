from html import escape
import gc
import subprocess
import os
import asyncio
import re
from datetime import datetime
import urllib
from math import sqrt

from colorthief import ColorThief
import msgpack
from fuzzywuzzy import fuzz
import discord
from discord.ext import commands

from .utils.misc import load_json, write_json

# DDNet guild IDs
GUILD_DDNET = 252358080522747904
CHAN_ANNOUNCEMENTS = 420565311863914496

DIR_PATH = 'ddnet-profile-card'
MSGPACK_FILE_PATH = f'{DIR_PATH}/msgpack/players.msgpack'


def reload_data():
    with open(MSGPACK_FILE_PATH, 'rb') as inp:
        unpacker = msgpack.Unpacker(inp, use_list=False)
        server_types = unpacker.unpack()  # `(type, ..)`
        stats_maps = unpacker.unpack()  # `{type: ((map, points, finishes), ..), ..}`
        total_points = unpacker.unpack()  # `points`
        stats_points = unpacker.unpack()  # `((player, points), ..)`
        stats_weekly_points = unpacker.unpack()  # `((player, points), ..)`
        stats_monthly_points = unpacker.unpack()  # `((player, points), ..)`
        stats_teamranks = unpacker.unpack()  # `((player, points), ..)`
        stats_ranks = unpacker.unpack()  # `((player, points), ..)`
        stats_servers = unpacker.unpack()  # `{type: (points, ((player, points), ..)), ..}`
        stats_players = unpacker.unpack()  # `{player: ({map: (teamrank, rank, finishes, timestamp,
        # time in sec), ..}, {location: finishes, ..}), ..}`

    del server_types
    del total_points
    del stats_weekly_points
    del stats_monthly_points
    del stats_servers
    gc.collect()

    return stats_maps, stats_points, stats_teamranks, stats_ranks, stats_players


def normalize_name(name):
    name = re.sub(r'\W', '_', name)
    return re.sub(r'[^\x00-\x7F]', '__', name)


class Profilecard:
    def __init__(self, bot):
        self.bot = bot
        self.map_details = load_json(f'{DIR_PATH}/map_details.json')
        self.stats_maps = None
        self.stats_points = None
        self.stats_teamranks = None
        self.stats_ranks = None
        self.stats_players = None
        self._cached_stamp = 0
        self.SERVER_TYPES = {
            'Novice': {
                'multiplier': 1,
                'offset': 0
            },
            'Moderate': {
                'multiplier': 2,
                'offset': 5
            },
            'Brutal': {
                'multiplier': 3,
                'offset': 15
            },
            'Insane': {
                'multiplier': 4,
                'offset': 30
            },
            'Dummy': {
                'multiplier': 5,
                'offset': 5
            },
            'DDmaX': {
                'multiplier': 4,
                'offset': 0
            },
            'Oldschool': {
                'multiplier': 6,
                'offset': 0
            },
            'Solo': {
                'multiplier': 4,
                'offset': 0
            },
            'Race': {
                'multiplier': 2,
                'offset': 0
            }
        }

    async def on_ready(self):
        await self.reload_msgpack()

    async def reload_msgpack(self):
        while not self.bot.is_closed():
            stamp = os.stat(MSGPACK_FILE_PATH).st_mtime
            # msgpack file is updated every 30 minutes
            if stamp != self._cached_stamp:
                self._cached_stamp = stamp
                (
                    self.stats_maps,
                    self.stats_points,
                    self.stats_teamranks,
                    self.stats_ranks,
                    self.stats_players,
                ) = reload_data()
                print('msgpack reloaded')

            await asyncio.sleep(600)

    def get_player_rank_stats(self, player):
        stats_types = [
            ('points', self.stats_points),
            ('teamrank', self.stats_teamranks),
            ('rank', self.stats_ranks)
        ]

        player = player.encode()
        player_stats = {}
        similar_names = []
        for stats_type, data in stats_types:
            rank = 0
            skips = 1
            previous_points = 0
            for name, points in data:
                if points != previous_points:
                    previous_points = points
                    rank += skips
                    skips = 1
                else:
                    skips += 1

                if name == player:
                    type_stats = (rank, points)
                    break

                if name not in similar_names and len(similar_names) <= 7:  # Don't spam name suggestions
                    if name.lower() == player.lower():
                        similar_names.append(name.decode())
                        continue

                    if sorted(name) == sorted(player):
                        similar_names.append(name.decode())
                        continue

                    ratio = fuzz.ratio(name, player)
                    if ratio >= 85:
                        similar_names.append(name.decode())

            else:
                if stats_type == 'points':
                    return False, similar_names

                type_stats = (-1, 0)

            player_stats[stats_type] = type_stats

        return True, player_stats

    def get_player_flag(self, player):
        locations = self.stats_players[player.encode()][1]
        if not locations:
            return 'UNK'

        eur_locations = [b'GER', b'GER2', b'FRA']
        eur_finishes = 0
        for l in eur_locations:
            if l in locations:
                eur_finishes += locations[l]
                del locations[l]

        if eur_finishes:
            locations[b'EUR'] = eur_finishes

        # Sort alphabetically to have consistent results
        locations = {l.decode(): f for l, f in sorted(locations.items())}
        max_location = max(locations, key=locations.get)

        # There are rare cases of really old ranks not having a server location code
        if not max_location:
            return 'UNK'

        available_flags = os.listdir('ddnet-profile-card/flags')
        if f'{max_location}.svg' not in available_flags:
            return 'UNK'

        return max_location

    def generate_player_profile(self, player, stats, flag):
        def get_background(score):
            backgrounds = load_json(f'{DIR_PATH}/backgrounds/thresholds.json')
            backgrounds = [(t['points'], t['background']) for t in backgrounds]
            return [b for p, b in backgrounds if score >= p][-1]

        def get_rank_span(rank_type, rank, score):
            span = f'<span class="type">{rank_type.upper()}</span> '
            if rank == -1:
                span += '<span class="score unranked">UNRANKED</span>'
            else:
                span += f'<span class="rank score">#{rank} | ' \
                        f'</span><span class="score">{score}</span> points'

            return span

        points_rank, points_score = stats['points']
        teamrank_rank, teamrank_score = stats['teamrank']
        rank_rank, rank_score = stats['rank']

        background = get_background(points_score)
        teamrank_span = get_rank_span('team rank', teamrank_rank, teamrank_score)
        rank_span = get_rank_span('rank', rank_rank, rank_score)

        html = ('<html>'
                '<head>'
                '<meta charset="utf-8"/>'
                '<link rel="stylesheet" type="text/css" href="style/style.css" media="screen">'
                '</head>'
                '<body>'
                f'<div id="card" class="background-{background}">'
                '<div class="box">'
                '<div class="badges name">'
                f'<img src="flags/{flag}.svg" class="flag"/> {escape(player)}</div>'
                '<div class="stats">'
                '<div class="global-points">'
                f'<span class="rank points">#{points_rank}</span>'
                '</br>'
                f'<span class="score">{points_score}</span> points'
                '</div>'
                '<div class="ranks">'
                f'<div class="team-rank">{teamrank_span}</div>'
                f'<div class="rank">{rank_span}</div>'
                '</div>'
                '</div>'
                '</div>'
                '</div>'
                '</body>'
                '</html>')

        with open(f'{DIR_PATH}/profile.html', 'w', encoding='utf-8') as html_file:
            html_file.write(html)

    @commands.command(pass_context=True)
    async def profile(self, ctx, *player):
        await ctx.trigger_typing()

        player = ' '.join(player) if player else ctx.message.author.display_name
        match = re.search(r'<@!?([0-9]+)>', player)
        if match:
            if ctx.guild:
                user = ctx.guild.get_member(int(match.group(1)))
            else:
                user = self.bot.get_user(int(match.group(1)))

            if user:
                player = player.replace(match.group(0), user.display_name)
            else:
                return await ctx.send('Can\'t see the mentioned user <:oop:395753983379243028>')

        found, stats = self.get_player_rank_stats(player)
        if not found:
            msg = 'Can\'t find player `{}` <:oop:395753983379243028>'.format(player.replace('`', '\`'))
            if stats:
                names = ['`{}`'.format(name.replace('`', '\`')) for name in stats]
                msg += ' Did you mean..\n' + ', '.join(names)

            return await ctx.send(msg)

        flag = self.get_player_flag(player)

        self.generate_player_profile(player, stats, flag)
        cmd = f'/root/.nvm/versions/node/v10.6.0/bin/node /root/discordbot/{DIR_PATH}/render_profile.js 800 266 profile'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        p_status = p.wait()

        img = discord.File(fp=f'{DIR_PATH}/profile.png', filename=f'profile_{normalize_name(player)}.png')
        await ctx.channel.send(file=img)

    def get_difficulty(self, server_type, points):
        multiplier = self.SERVER_TYPES[server_type]['multiplier']
        offset = self.SERVER_TYPES[server_type]['offset']
        return int((points - offset) / multiplier)

    def get_map_details(self, map_name):
        map_name = map_name.lower()
        similar_names = []
        for name, details in self.map_details.items():
            if name.lower() == map_name:
                map_name = name
                mapper = details['mapper']
                release_date = details['release_date']
                break

            if name not in similar_names and len(similar_names) <= 7:  # Don't spam name suggestions
                if sorted(name.lower()) == sorted(map_name):
                    similar_names.append(name)
                    continue

                ratio = fuzz.ratio(name.lower(), map_name)
                if ratio >= 85:
                    similar_names.append(name)

        else:
            return False, similar_names

        map_name_formated = map_name.encode()
        similar_names = []
        for server_type, data in self.stats_maps.items():
            for name, points, finishes in data:
                if name == map_name_formated:
                    return True, (map_name, mapper, release_date, server_type.decode(), points, finishes)

        return None, None

    def get_map_top_ranks(self, map_name):
        map_name = map_name.encode()
        ranks = []
        teamrank = []
        for player, map_stats in self.stats_players.items():
            for name, data in map_stats[0].items():
                if name == map_name:
                    if 1 <= data[1] <= 30:  # There are actually invalid rank 0s
                        ranks.append((player.decode(), data[4]))

                    if data[0] == 1:
                        teamrank.append((player.decode(), data[4]))

        team_time = None
        team_players = []
        if teamrank and all(t[1] == teamrank[0][1] for t in teamrank):
            team_time = teamrank[0][1]
            team_players = [t[0] for t in teamrank]

        ranks = sorted(ranks, key=lambda x: x[0])  # Sort based on name
        ranks = sorted(ranks, key=lambda x: x[1])  # Sort based on finish time

        out = []
        rank = 0
        skips = 1
        previous_time = 0
        for player, time in ranks:
            if time != previous_time:
                previous_time = time
                rank += skips
                skips = 1
            else:
                skips += 1

            out.append((rank, time, player))

        out = [o for o in out if o[2] not in team_players]
        return (team_time, sorted(team_players)), out[0:20]

    def get_map_tiles(self, map_name):
        if 'tiles' not in self.map_details[map_name]:
            return None

        map_tiles = self.map_details[map_name]['tiles']
        tiles_negative = ['NPH_START', 'NPC_START', 'HIT_START']  # no-player-hook|no-player-colission|no-hammer-hit
        tiles_special = ['EHOOK_START', 'SUPER_START', 'JETPACK_START',
                         'WALLJUMP']  # endless-hook|super-jump|jetpack|walljump
        tiles_weapon = ['WEAPON_SHOTGUN', 'WEAPON_GRENADE', 'WEAPON_RIFLE', 'POWERUP_NINJA']
        map_tiles_negative = [t for t in tiles_negative if t in map_tiles]
        map_tiles_special = [t for t in tiles_special if t in map_tiles]
        map_tiles_weapon = [t for t in tiles_weapon if t in map_tiles]

        return [*map_tiles_negative, *map_tiles_special, *map_tiles_weapon]

    def generate_map_profile(self, map_name, mapper, release_date, server_type, points, finishes, top_teamranks,
                             top_ranks, tiles=None):
        def get_stars(difficulty):
            return '★' * difficulty + '☆' * max(5 - difficulty, 0)

        def get_ranks_table(top_teamranks, top_ranks):
            div = '<div class="top-ranks">'
            table = '<table id="ranks-table">'

            if top_teamranks[0]:
                time = top_teamranks[0]
                names = ''
                for n, p in enumerate(top_teamranks[1]):
                    if n > 0:
                        if n == len(top_teamranks[1]) - 1:
                            names += '<span class="delimiter"> &amp; </span>'
                        else:
                            names += '<span class="delimiter">, </span>'

                    names += f'{escape(p)}'

                table += ('<tr>'
                          '<td class="rank colored">#1T</td>'
                          f'<td class="time">{"%02d:%02d" % divmod(time, 60)}</td>'
                          f'<td class="playername"><div id="team-rank">{names}</div></td>'
                          '</tr>')

            for rank, time, name in top_ranks:
                table += f'<tr><td class="rank colored">#{rank}</td><td class="time">{"%02d:%02d" % divmod(time, 60)}</td>' \
                         f'<td class="playername">{escape(name)}</td></tr>'

            table += '</table>'
            div += f'{table}</div>'

            return div

        def get_color(thumbnail_url):
            def rgb_to_hsp(r, g, b):
                Pr = .299
                Pg = .587
                Pb = .114

                p = sqrt(Pr * r ** 2 + Pg * g ** 2 + Pb * b ** 2)

                if r == g and r == b:
                    h = 0
                    s = 0
                    return h, s, p

                if r >= g and r >= b:  # r is largest
                    if b >= g:
                        h = 6 / 6 - 1 / 6 * (b - g) / (r - g)
                        s = 1 - g / r
                    else:
                        h = 0 / 6 + 1 / 6 * (g - b) / (r - b)
                        s = 1 - b / r

                elif g >= r and g >= b:  # g is largest
                    if r >= b:
                        h = 2 / 6 - 1 / 6 * (r - b) / (g - b)
                        s = 1 - b / g
                    else:
                        h = 2 / 6 + 1 / 6 * (b - r) / (g - r)
                        s = 1 - r / g

                else:  # b is largest
                    if g >= r:
                        h = 4 / 6 - 1 / 6 * (g - r) / (b - r)
                        s = 1 - r / b
                    else:
                        h = 4 / 6 + 1 / 6 * (r - g) / (b - g)
                        s = 1 - g / b

                return h, s, p

            def hsp_to_rgb(H, S, P):
                Pr = .299
                Pg = .587
                Pb = .114

                minOverMax = 1 - S

                if minOverMax > 0:
                    if H < 1 / 6:  # R>G>B
                        H = 6 * (H - 0 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        B = P / sqrt(Pr / minOverMax / minOverMax + Pg * part ** 2 + Pb)
                        R = (B) / minOverMax
                        G = (B) + H * ((R) - (B))
                    elif H < 2 / 6:  # G>R>B
                        H = 6 * (-H + 2 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        B = P / sqrt(Pg / minOverMax / minOverMax + Pr * part ** 2 + Pb)
                        G = (B) / minOverMax
                        R = (B) + H * ((G) - (B))
                    elif H < 3 / 6:  # G>B>R
                        H = 6 * (H - 2 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        R = P / sqrt(Pg / minOverMax / minOverMax + Pb * part ** 2 + Pr)
                        G = (R) / minOverMax
                        B = (R) + H * ((G) - (R))
                    elif H < 4 / 6:  # B>G>R
                        H = 6 * (-H + 4 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        R = P / sqrt(Pb / minOverMax / minOverMax + Pg * part ** 2 + Pr)
                        B = (R) / minOverMax
                        G = (R) + H * ((B) - (R))
                    elif H < 5 / 6:  # B>R>G
                        H = 6 * (H - 4 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        G = P / sqrt(Pb / minOverMax / minOverMax + Pr * part ** 2 + Pg)
                        B = (G) / minOverMax
                        R = (G) + H * ((B) - (G))
                    else:  # R>B>G
                        H = 6 * (-H + 6 / 6)
                        part = 1 + H * (1 / minOverMax - 1)
                        G = P / sqrt(Pr / minOverMax / minOverMax + Pb * part ** 2 + Pg)
                        R = (G) / minOverMax
                        B = (G) + H * ((R) - (G))

                return R, G, B

            color_thief = ColorThief(f'{DIR_PATH}/{thumbnail_url}')
            r, g, b = color_thief.get_color(quality=1)  # Get dominant color
            h, s, p = rgb_to_hsp(r, g, b)

            if p < 150:
                r, g, b = hsp_to_rgb(h, s, 150)

            return (r, g, b)

        def get_tiles_div(tiles):
            out = ''
            for tile in tiles:
                out += f'<img class="tile" src="tiles/{tile}.png" />'

            return out

        def get_title(map_name, mapper):
            title = f'<div id="name">{escape(map_name)}'
            if mapper:
                mapper = re.split(r', | & ', mapper)
                mappers = ' <div class="mapper"><span class="delimiter">by</span> '
                for n, m in enumerate(mapper):
                    if n > 0:
                        if n == len(mapper) - 1:
                            mappers += '<span class="delimiter"> &amp; </span>'
                        else:
                            mappers += '<span class="delimiter">, </span>'

                    mappers += f'{escape(m)}'

                title += f'{mappers}</div>'

            title += '</div>'
            return title

        def get_finish_span(finishes):
            text = 'FINISH' if finishes == 1 else 'FINISHES'
            return f'<span class="finishes">{finishes}</span><span class="finishes-text"> {text}</span>'

        def format_release_date(release_date):
            date = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S')
            return f'</br><span class="released-text">RELEASED</span> <span class="released">{date.strftime("%b %d %Y").upper()}</span>'

        thumbnail_url = f'map_thumbnails/{normalize_name(map_name)}.png'
        colors = get_color(thumbnail_url)
        title = get_title(map_name, mapper)
        difficulty = self.get_difficulty(server_type, points)
        stars = get_stars(difficulty)
        finish_span = get_finish_span(finishes)
        release_span = format_release_date(release_date) if release_date else ''
        tiles_div = get_tiles_div(tiles) if tiles else ''
        ranks = get_ranks_table(top_teamranks, top_ranks)

        html = ('<html>'
                '<head>'
                '<meta charset="UTF-8">'
                '<link rel="stylesheet" type="text/css" href="style/map_stats.css" media="screen">'
                '<style>'
                '.background {'
                f'background-image: url({thumbnail_url}); background-size: cover;'
                '}\n'
                '.colored {'
                f'color: rgb{colors};'
                '}'
                '</style>'
                '</head>'
                '<body>'
                '<div id="card" class="background">'
                '<div class="content-wrapper">'
                f'{title}'
                '<div id="stats-wrapper">'
                f'<div class="info-wrapper">'
                '<div class="details">'
                f'{server_type.upper()}</br>'
                f'<span class="difficulty">{stars}</span>'
                '</div>'
                f'<div class="extra-details colored">{finish_span}{release_span}</div>'
                f'<div id="tiles" class="tiles">{tiles_div}</div>'
                '</div>'
                f'{ranks}'
                '</div>'
                '<script src="adjust_font_size.js"></script>'
                '</body>'
                '</html>')

        with open(f'{DIR_PATH}/map_profile.html', 'w', encoding='utf-8') as html_file:
            html_file.write(html)

    @commands.command(name='map', pass_context=True)
    async def map_profile(self, ctx, *map_name):
        if not map_name:
            return await ctx.send('You need to specify a map')

        await ctx.trigger_typing()

        map_name = ' '.join(map_name)

        found, stats = self.get_map_details(map_name)
        if not found:
            msg = 'Can\'t find map `{}` <:oop:395753983379243028>'.format(map_name.replace('`', '\`'))
            if stats:
                names = ['`{}`'.format(name.replace('`', '\`')) for name in stats]
                msg += ' Did you mean..\n' + ', '.join(names)

            return await ctx.send(msg)

        if found is None:
            return await ctx.send('Error')

        map_name = stats[0]
        top_ranks = self.get_map_top_ranks(map_name)
        tiles = self.get_map_tiles(map_name)

        self.generate_map_profile(*stats, *top_ranks, tiles)
        cmd = f'/root/.nvm/versions/node/v10.6.0/bin/node /root/discordbot/{DIR_PATH}/' \
              'render_profile.js 800 500 map_profile'
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        p_status = p.wait()

        img = discord.File(fp=f'{DIR_PATH}/map_profile.png', filename=f'map_profile_{normalize_name(map_name)}.png')
        await ctx.channel.send(file=img)

    async def on_message(self, message):
        if message.channel.id != CHAN_ANNOUNCEMENTS:
            return

        match = re.search(r'New map \[(.+)\]\(.+\) by (.+) released on .+\.', message.content)
        if not match:
            return

        map_name = match.group(1)
        mapper = re.split(r'(, | & )', match.group(2))
        mapper_deformated = []
        for m in mapper:
            match = re.search(r'\[(.+)\].+', m)
            mapper_deformated.append(match.group(1) if match else m)

        insert = {'mapper': ''.join(mapper_deformated), 'release_date': message.created_at.isoformat()}

        try:
            urllib.request.urlretrieve(f'https://ddnet.tw/ranks/maps/{normalize_name(map_name)}.png',
                                       f'{DIR_PATH}/map_thumbnails/{normalize_name(map_name)}.png')
            urllib.request.urlretrieve(f'https://ddnet.tw/ranks/maps/{map_name}.msgpack',
                                       f'{DIR_PATH}/msgpack/{map_name}.msgpack')
            with open(f'{DIR_PATH}/msgpack/{map_name}.msgpack', 'rb') as inp:
                unpacker = msgpack.Unpacker(inp)
                width = unpacker.unpack()
                height = unpacker.unpack()
                tiles = unpacker.unpack()

            if tiles:
                insert['tiles'] = {name.decode(): bol for name, bol in tiles.items()}
        except Exception as e:
            print(f'downloading files for map {map_name} failed: `{e}`')

        self.map_details[map_name] = insert
        write_json(f'{DIR_PATH}/map_details.json')


def setup(bot):
    bot.add_cog(Profilecard(bot))
