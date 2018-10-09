import json
import asyncio
from datetime import datetime
import socket

import discord
from discord.ext import commands
from twstatus import ServerHandler

CHAN_INFO = 392853737099624449
MSG_STATUS = 421364843161976833

def format_time(seconds):
    return '%02d:%02d' % divmod(seconds, 60)

def format_score(score, pure=False):
    if pure:
        return str(score)

    if score == -9999:
        return '00:00'

    return format_time(abs(score))

class TwStatus:
    def __init__(self, bot):
        self.bot = bot
        with open('tw-status/info', 'r', encoding='utf-8') as inp:
            self.info = json.load(inp)
        self.country_codes = {
            'GER': 'de',
            'RUS': 'ru',
            'CHL': 'cl',
            'BRA': 'br',
            'ZAF': 'za',
            'USA': 'us',
            'CAN': 'ca',
            'CHN': 'cn'
        }

    async def on_ready(self):
        await self.ddnet_status()

    async def get_ddnet_servers(self, servers):
        out = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for name, addresses in servers.items():
            count = 0
            player_count = 0
            for addr in addresses:
                ip, port = addr.split(':')
                server = ServerHandler(ip, int(port), False, 2)
                request = await server.get_info(sock, False)
                if request:
                    count += 1
                    player_count += request.client_count

            out.append((name, (count, len(addresses)), player_count))
        sock.close()
        return out

    async def ddnet_status(self):
        info_chan = None
        while info_chan is None:
            try:
                info_chan = self.bot.get_channel(CHAN_INFO)
                embed_msg = await info_chan.get_message(MSG_STATUS)
            except:
                pass

        while not self.bot.is_closed():
            servers = {s['name']: s['servers']['DDNet'] for s in self.info['servers']}
            status = await self.get_ddnet_servers(servers)
            total_servers = sum([s[1][0] for s in status])
            max_servers = sum([s[1][1] for s in status])
            total_players = sum([s[2] for s in status])
            desc = f'**Total servers:** {total_servers}/{max_servers} — **Total players:** {total_players}'
            embed = discord.Embed(description=desc, timestamp=datetime.utcnow())
            ddnet_emoji = 'https://cdn.discordapp.com/emojis/391727274824826880.png?v=1'
            embed.set_author(name=f'DDNet Servers', icon_url=ddnet_emoji)
            embed.set_footer(text='Last updated')

            for stats in status:
                name, servers, players = stats
                flag = f':flag_{self.country_codes[name]}:'
                name = f'{flag} {name}'
                count, max_count = servers
                content = f'**Servers:** {count}/{max_count}\n**Players:** {players}'
                embed.add_field(name=name, value=content)

            while len(embed.fields) % 3 != 0:
                embed.add_field(name='\255', value='\255')

            await embed_msg.edit(embed=embed)
            await asyncio.sleep(360)


def setup(bot):
    bot.add_cog(TwStatus(bot))
