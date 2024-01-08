"""
This script is used to create a poll with the best maps in a given year.

1. (Python2) Run `update_psql_tables.py` in data/tools to update the postgres record_maps database
2. Add this script to the initial_extensions tuple in bot.py
3. Use the `$load cogs.ddnet_map_awards` to load this script
3.5. Optional: Use the `$set_year <year> command to set the year manually, otherwise it'll just run last year's releases.
4. Use the `$export_maps` command to export all maps in given self.year to a file
5. Use the `$poll` command to generate the selects for the poll
6. Wait 1 week
7. Use the `$results` to generate the results of the poll, preferably in a new channel labeled 'ddnet-map-awards-<year>
8. Remove this script from initial_extensions in bot.py, the selects menu (or the channel with the poll) and the generated data/user_selections.json
"""

import discord
import json

from discord.ext import commands
from datetime import datetime, timedelta, timezone
from collections import Counter
from itertools import groupby

GUILD_DDNET = 252358080522747904
ROLE_ADMIN  = 293495272892399616


# taken from ddnet.py
def slugify2(name):
    x = '[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+'
    string = ""
    for c in name:
        if c in x or ord(c) >= 128:
            string += "-%s-" % ord(c)
        else:
            string += c
    return string


def get_mapper_urls(maps_data, map_name):
    for map_info in maps_data:
        if map_info['map'] == map_name:
            mappers = [mapper for mapper in map_info['mapper'].replace(' & ', ', ').split(', ')]
            print(mappers)
            return [f"[{mapper}](https://ddnet.org/mappers/{slugify2(mapper)})" for mapper in mappers]


class DDNetMapAwards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_selections = {}
        self.year = datetime.now().year - 1

    @commands.command(name='set_year', hidden=True)
    async def set_year(self, ctx, year):
        try:
            self.year = int(year)
        except ValueError:
            await ctx.send("Invalid year format. Please provide a valid integer.")

    @commands.command(name='export_maps', hidden=True)
    async def export_maps(self, ctx):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        query = (
            f"SELECT * FROM record_maps "
            f"WHERE \"Timestamp\" BETWEEN '{self.year}-01-01' AND '{self.year + 1}-01-01' "
            f"ORDER BY \"Timestamp\" ASC;"
        )

        records = await self.bot.pool.fetch(query)

        if not records:
            await ctx.send("No records found.")
            return

        all_maps = {}
        for record in records:
            server = record['server']
            if server not in all_maps:
                all_maps[server] = []
            all_maps[server].append(dict(record))

        with open('data/all_maps.json', 'w', encoding='utf-8') as f:
            json.dump(all_maps, f, indent=2, default=str)

        await ctx.send(
            f"Exported all maps released maps between {self.year} and {self.year + 1} to `data/all_maps.json`.")

    @commands.command(name='poll', hidden=True)
    async def generate_poll_menu(self, ctx):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return
        with open('data/all_maps.json', 'r', encoding='utf-8') as json_file:
            all_maps_data = json.load(json_file)

        if not all_maps_data:
            await ctx.send("No data found.")
            return

        views = []
        order = ['Novice', 'Moderate', 'Brutal', 'Insane', 'Dummy', 'Solo', 'Oldschool', 'Race', 'Fun']

        for server in order:
            if server in all_maps_data:
                maps = all_maps_data[server]
                mapper = maps[0]['mapper']
                create_selects = CreateSelects(self.bot, server, maps, mapper)
                view = await create_selects.create_view()
                views.append(view)

        now = datetime.now(timezone.utc)
        future_time_utc = now + timedelta(days=7)
        unix_timestamp = int(future_time_utc.timestamp())

        await ctx.send(f'# Which map did you enjoy the most in {self.year}? \n Make your selections down below! '
                       f'Only **one map per server difficulty can be selected**, so choose wisely. \n'
                       f' The poll will run for **1 week** and will end on **<t:{unix_timestamp}:F>**')

        for view, server in zip(views, order):
            await ctx.send(content=f'## {server}:', view=view)

    @commands.command(name='results', hidden=True)
    async def poll_results(self, ctx):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        with open('data/user_selections.json', 'r') as file:
            user_selections = json.load(file)

        with open('data/all_maps.json', 'r') as file:
            all_maps = json.load(file)

        category_counts = {}
        for user_id, categories in user_selections.items():
            for category, maps in categories.items():
                category_counts.setdefault(category, Counter())[maps[0]] += 1

        order = ['Novice', 'Moderate', 'Brutal', 'Insane', 'Dummy', 'Solo', 'Oldschool', 'Race', 'Fun']
        sorted_categories = sorted(category_counts.keys(), key=lambda x: order.index(x))

        await ctx.send(f'# DDNet Map Awards {self.year}:')

        for category in sorted_categories:
            counter = category_counts[category]
            sorted_counter = sorted(counter.items(), key=lambda x: x[1], reverse=True)
            grouped_counter = [list(group) for key, group in groupby(sorted_counter, key=lambda x: x[1])]

            message = f"## {category}: \n"

            for rank, group in enumerate(grouped_counter[:3], start=1):
                ranks = []

                for map_name, votes in group:
                    mappers = get_mapper_urls(all_maps[category], map_name)
                    ranks.append(
                        f"**[{map_name}](https://ddnet.org/maps/?map={slugify2(map_name)})** "
                        f"— Mapper(s): {', '.join(mappers)}"
                    )

                map_names = ' | '.join(ranks)
                message += f"{rank}. {map_names} **with {group[0][1]} votes**\n"

            for rank in range(len(grouped_counter[:3]), 3):
                pass

            message += "\n"
            await ctx.send(message)

    @commands.Cog.listener()
    async def on_ready(self):
        with open('data/all_maps.json', 'r', encoding='utf-8') as json_file:
            all_maps_data = json.load(json_file)

        views = []
        for server, maps in all_maps_data.items():
            mapper = maps[0]['mapper']
            create_selects = CreateSelects(self.bot, server, maps, mapper)
            view = await create_selects.create_view()
            views.append(view)

        for view in views:
            self.bot.add_view(view=view)


class CreateSelects(discord.ui.View):
    def __init__(self, bot, server, maps, mapper):
        self.bot = bot
        self.server = server
        self.maps = maps
        self.user_selections = {}
        self.mapper = mapper
        super().__init__(timeout=None)

    async def interaction_callback(self, interaction: discord.Interaction):
        with open('data/user_selections.json', 'r', encoding='utf-8') as f:
            self.user_selections = json.load(f)

        user_id = str(interaction.user.id)

        if user_id not in self.user_selections:
            self.user_selections[user_id] = {}

        custom_id = interaction.data['custom_id']
        custom_id_parts = custom_id.split('_')
        server = custom_id_parts[1]

        selected_map_label = interaction.data['values'][0]
        selected_map = selected_map_label.split(' by ')[0]

        if server not in self.user_selections[user_id]:
            self.user_selections[user_id][server] = []

        old_selection = self.user_selections[user_id][server]

        if old_selection:
            old_selection = old_selection[0]
            self.user_selections[user_id][server] = [selected_map]

            await interaction.response.send_message(  # noqa
                f"## {server} Server: \n"
                f"Replaced your old selection: [{old_selection}](https://ddnet.org/maps/{slugify2(old_selection)}) "
                f"with map: [{selected_map}](https://ddnet.org/maps/{slugify2(selected_map)})",
                ephemeral=True
            )
        else:
            self.user_selections[user_id][server].append(selected_map)

            await interaction.response.send_message(  # noqa
                f"## {server} Server: \n"
                f"Map [{selected_map}](https://ddnet.org/maps/{slugify2(selected_map)}) selected.",
                ephemeral=True
            )

        with open('data/user_selections.json', 'w', encoding='utf-8') as json_file:
            json.dump(self.user_selections, json_file, indent=2)

    async def create_view(self):
        options = sorted([discord.SelectOption(
            label=f"{map_data['map']} by {map_data['mapper']}",
            value=map_data['map']
        ) for map_data in self.maps], key=lambda x: x.label)

        options = [options[i:i + 25] for i in range(0, len(options), 25)]

        for i, chunk in enumerate(options):
            option_desc = f"Select a map on {self.server} server"
            if len(options) > 1:
                option_desc += f" (Page {i + 1})"

            custom_id = f'select_{self.server}_{i}'

            select_menu = discord.ui.Select(
                custom_id=custom_id,
                options=chunk,
                placeholder=option_desc
            )

            select_menu.callback = self.interaction_callback
            self.add_item(select_menu)

        return self


async def setup(bot):
    await bot.add_cog(DDNetMapAwards(bot))
