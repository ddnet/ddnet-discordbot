# ddnet-discordbot

### Setup

Note: these steps will barely get the bot running, many more steps are required to enable everything the bot has to offer

1. Clone this repository with git
   - install the required python dependencies
2. Create a discord bot https://discord.com/developers/applications
   - in the 'Bot' tab, enable 'Presence Intent' and 'Server Members Intent'
   - in the 'Bot' tab, copy the token
3. Create the file `config.ini` in the repository source using the `config_example.ini`
   - insert the discord bot token
4. Install Postgresql
   - create a user with your os username
   - create a database with your os username as its name
   - import `data/schema.psql` into that database (`psql -U <user-name> <database-name> -f data/schema.psql`)
5. Create a discord server with all the required channels and categories
   - overwrite the channel and category ids in `cogs/map_testing/__init__.py`
   - to copy an id in discord, first enable Settings > Advanced > Developer Mode and then rightclick on the channel/category and select 'Copy ID'
6. Get external binaries
   - copy the `render_map` binary (originally from [libtw2/render_map](https://github.com/heinrich5991/libtw2/tree/master/render_map)) from `data/tools/render_map/render_map` and place it in `data/map-testing`
7. Create directories
   - `logs` directory in the repository root
   - `tmp` directory in `data/map-testing`
8. Edit code that interact with ddnet-owned servers
   - in `cogs/map_testing/__init__.py`, comment out parts of the function bodies of the functions `ddnet_upload`, `ddnet_delete`, `archive_testlog`
   - in `bot.py`, comment out the `'cogs.status',` line
9. Execute the file `run.py` with python
