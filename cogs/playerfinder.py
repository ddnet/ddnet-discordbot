import discord
from discord.ext import commands, tasks
from discord.ext.commands import MissingAnyRole
from collections import defaultdict
from requests_futures.sessions import FuturesSession

import asyncio
import re
import json
import os

ROLE_MODERATOR  = 252523225810993153
ROLE_ADMIN      = 293495272892399616
CHAN_BOT_SPAM   = 1078979471761211462


class PlayerFinder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.servers_url = "https://master1.ddnet.tw/ddnet/15/servers.json"
        self.servers_info_url = 'https://info2.ddnet.tw/info'
        self.player_file = "find_players.json"
        self.players_online_filtered = {}
        self.sent_messages = []

    async def get(self, url, **kwargs):
        with FuturesSession() as s:
            return await asyncio.wrap_future(s.get(url, **kwargs))

    def in_channel(self, channel_id):
        async def channel_restriction(ctx):
            if ctx.channel.id != channel_id:
                return False
            return True

        return commands.check(channel_restriction)

    @commands.command(name='list')
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def send_players_list(self, ctx: commands.Context):
        with open(self.player_file, 'r', encoding='utf-8') as f:
            players = json.load(f)

        if not players:
            await ctx.send('No players found.')
        else:
            response = "Current List:\n"
            for i, (player, reason) in enumerate(players.items(), start=1):
                response += f"{i}. \"{player}\" for reason: {reason}\n"

            with open('player_list.txt', 'w') as f:
                f.write(response)

            with open('player_list.txt', 'rb') as f:
                await ctx.send(file=discord.File(f, 'player_list.txt'))

            os.remove('player_list.txt')

    @commands.command(name='add')
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def add_player_to_list(self, ctx: commands.Context, *, players: str):
        new_players = {}
        with open(self.player_file, 'r', encoding='utf-8') as f:
            players_list = json.load(f)

        player_info = players.split("\n")
        for i in range(0, len(player_info), 2):
            player_name = player_info[i].strip()
            reason = player_info[i + 1].strip() if i + 1 < len(player_info) else "No reason provided"
            if player_name in players_list:
                await ctx.send(f'Player {player_name} is already in the search list')
            else:
                new_players[player_name] = reason
                players_list[player_name] = reason

        with open(self.player_file, 'w', encoding='utf-8') as f:
            json.dump(players_list, f)

        if new_players:
            message = "Added players:"
            for player, reason in new_players.items():
                message += f"\n{player}: {reason}"
            await ctx.send(message)

    @commands.command(name='rm')
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def remove_player_from_list(self, ctx: commands.Context, *, player_names: str):
        removed_players = []
        with open(self.player_file, 'r', encoding='utf-8') as f:
            players = json.load(f)
        with open(self.player_file, 'w', encoding='utf-8') as f:
            for player_name in player_names.split("\n"):
                player_name = player_name.strip()
                if player_name in players:
                    removed_players.append(player_name)
                    del players[player_name]
                else:
                    await ctx.send(f'Player {player_name} not found.')
            json.dump(players, f)
        if removed_players:
            await ctx.send(f'Removed players:\n{", ".join(removed_players)}.')
            self.players_online_filtered.clear()

    @commands.command(name='clear')
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def clear_entire_players_list(self, ctx: commands.Context):
        with open(self.player_file, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        await ctx.send('Player list cleared.')

    def load_players(self):
        with open(self.player_file, 'r', encoding='utf-8') as f:
            players = json.load(f)
        return players

    async def server_filter(self):
        gamemodes = ['DDNet', 'Test', 'Tutorial', 'Block', 'Infection',
                     'iCTF', 'gCTF', 'Vanilla', 'zCatch', 'TeeWare',
                     'TeeSmash', 'Foot', 'xPanic', 'Monster']
        resp = await self.get(self.servers_info_url)
        servers = resp.json()
        data = servers.get('servers')
        ddnet_ips = []
        for i in data:
            sv_list = i.get('servers')
            for mode in gamemodes:
                server_lists = sv_list.get(mode)
                if server_lists is not None:
                    ddnet_ips += server_lists
        return ddnet_ips

    def format_address(self, address):
        address_match = re.match(r"tw-0.6\+udp://([\d\.]+):(\d+)", address)
        if address_match:
            ip, port = address_match.groups()
            return f"{ip}:{port}"
        return None

    async def players(self):
        resp = await self.get(self.servers_url)
        servers = resp.json()
        players = defaultdict(list)

        for server in servers["servers"]:
            server_addresses = []
            for address in server["addresses"]:
                formatted = self.format_address(address)
                if formatted is not None:
                    server_addresses.append(formatted)
            if "clients" in server["info"]:
                for player in server["info"]["clients"]:
                    for address in server_addresses:
                        players[player["name"]].append((server["info"]["name"], address))
        return players

    @commands.command(name='find')
    async def search_player(self, ctx, player_name):
        players_dict = await self.players()
        if player_name in players_dict:
            player_info = players_dict[player_name]
            message = f"Found {len(player_info)} server(s) with \"{player_name}\" currently playing:\n"
            for i, server in enumerate(player_info, 1):
                server_name, server_address = server
                message += f"{i}. Server: {server_name} — Link: <ddnet://{server_address}/>\n"
            await ctx.send(message)
        else:
            await ctx.send(f"No player with the name \"{player_name}\" has been found.")

    async def send_message(self, embed):
        try:
            if not self.sent_messages:
                self.sent_messages.append(await self.bot.get_channel(CHAN_BOT_SPAM).send(embed=embed))
            else:
                channel = self.bot.get_channel(CHAN_BOT_SPAM)
                async for message in channel.history(limit=1):
                    if message != self.sent_messages[-1]:
                        await self.sent_messages[-1].delete()
                        self.sent_messages[-1] = await channel.send(embed=embed)
                        return

                last_message = self.sent_messages[-1]
                await last_message.edit(embed=embed)
                """Send a new embed if someone deletes the embed for some reason"""
        except discord.NotFound:
            self.sent_messages.append(await self.bot.get_channel(CHAN_BOT_SPAM).send(embed=embed))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            if len(message.embeds) > 0 and message.id in self.sent_messages:
                try:
                    await message.delete()
                    self.sent_messages.remove(message.id)
                except Exception as error:
                    print(f"Error deleting message: {error}")

    @tasks.loop(seconds=10)
    async def find_players(self):
        players = self.load_players()
        server_filter_list = await self.server_filter()
        players_online = await self.players()

        self.players_online_filtered = {player_name: players_online[player_name] for player_name in players
                                        if players_online[player_name] and players_online[player_name][0][
                                            1] in server_filter_list}

        player_embed = discord.Embed(color=0x00ff00)
        if self.players_online_filtered:
            player_embed.title = "Found players"
            for player_name, servers in self.players_online_filtered.items():
                server_name, address = servers[0]
                reason = players.get(player_name, "No reason provided")

                player_embed.add_field(name=f"Player: {player_name}",
                                       value=f"Server: {server_name}"
                                             f"\nReason: {reason}"
                                             f"\nAddress:"
                                             f"\nNon-Steam <ddnet://{address}/>"
                                             f"\nSteam <steam://run/412220//{address}/>",
                                       inline=False)
        else:
            player_embed.title = "No players found in current iteration."

        await self.send_message(player_embed)

    @commands.command(name="stop_search")
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def stop_player_search(self, ctx: commands.Context):
        if not self.find_players.is_running():
            await ctx.send("The player search process is not currently running.")
        else:
            if self.sent_messages:
                last_message = self.sent_messages[-1]
                await last_message.delete()
                self.sent_messages.clear()
            self.find_players.stop()
            self.players_online_filtered.clear()
            await ctx.send("Process stopped.")

    @commands.command(name='start_search')
    @commands.has_any_role(ROLE_ADMIN, ROLE_MODERATOR)
    @in_channel(CHAN_BOT_SPAM)
    async def start_player_search(self, ctx: commands.Context):
        if self.find_players.is_running():
            await ctx.send("The player search process is already running.")
        else:
            self.find_players.start()
            await ctx.send("Initializing search...")

    @send_players_list.error
    @add_player_to_list.error
    @remove_player_from_list.error
    @stop_player_search.error
    @start_player_search.error
    async def playerfinder_error_handler(self, ctx, error):
        if isinstance(error, MissingAnyRole):
            await ctx.send("You don't have the required roles to use this command.")
        else:
            raise error

    @find_players.before_loop
    async def before_find_players(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.search_player.stop()


def setup(bot: commands.Bot):
    bot.add_cog(PlayerFinder(bot))
