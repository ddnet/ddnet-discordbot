# This cog is primarily used to edit or send messages via bot

import discord
import os
import importlib

from . import dictionary
from discord.ext import commands

CHAN_WELCOME        = 1125706766999629854
CHAN_TESTING_INFO   = 1201860080463511612
GUILD_DDNET         = 252358080522747904
ROLE_ADMIN          = 293495272892399616

banners_dir = 'data/banners'


class BotMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_messages(self, ctx: commands.Context, channel_id, messages):
        channel = self.bot.get_channel(channel_id)
        await ctx.message.add_reaction("👌")
        await channel.purge()

        description = None

        for filename, message_attr in messages:
            if filename is not None:
                banner_path = os.path.join(banners_dir, filename)
                await channel.send(file=discord.File(banner_path, filename=filename))

            if message_attr is not None:
                description = getattr(dictionary, message_attr, None)

            if description is not None:
                await channel.send(content=description, allowed_mentions=discord.AllowedMentions(roles=False))


    @commands.command(hidden=True)
    async def welcome(self, ctx: commands.Context):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        await self.send_messages(ctx, CHAN_WELCOME, [
            ('welcome_main.png', 'welcome_main'),
            ('welcome_rules.png', 'welcome_rules'),
            ('welcome_channels.png', 'welcome_channel_listing'),
            ('welcome_links.png', 'welcome_ddnet_links'),
            ('welcome_roles.png', 'welcome_ddnet_roles'),
            ('welcome_communities.png', 'welcome_community_links')
        ])

    @commands.command(name='tinfo', hidden=True)
    async def testing_info(self, ctx: commands.Context):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        await self.send_messages(ctx, CHAN_TESTING_INFO, [
            ('testing_map_testing.png', None),
            ('testing_main.png', 'testing_info_header'),
            (None, 'testing_info'),
            (None, 'testing_channel_access')
        ])

        channel = self.bot.get_channel(CHAN_TESTING_INFO)
        reaction_message = None
        async for message in channel.history(limit=1):
            reaction_message = message
            break

        await reaction_message.add_reaction("✅")

    @commands.command(name='update', hidden=True)
    async def update_message(self, ctx, message_id, message_variable):
        """
        Usage: $update <message_id> <message_variable>
        The message variables can be found in 'cogs/bot_messages/dictionary.py'
        """
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        channel_ids = [CHAN_WELCOME, CHAN_TESTING_INFO]
        message_id = int(message_id)

        var = getattr(dictionary, message_variable, None)
        if var is None:
            await ctx.reply(f"Message variable not found.")
            return

        for channel_id in channel_ids:
            channel = self.bot.get_channel(channel_id)
            try:
                message_to_edit = await channel.fetch_message(message_id)
                await message_to_edit.edit(content=var)
                await ctx.message.add_reaction("👌")
                return
            except discord.NotFound:
                pass

        await ctx.send("Invalid message ID. Please provide a valid message ID.")


async def setup(bot):
    await bot.add_cog(BotMessages(bot))
