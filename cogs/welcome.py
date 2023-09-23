import discord
import asyncio
import os
import importlib

from discord.ext import commands

CHAN_WELCOME = 1125706766999629854
GUILD_DDNET  = 252358080522747904
ROLE_ADMIN   = 293495272892399616


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='uwu', hidden=True)
    async def update_welcome(self, ctx: commands.Context):
        if ctx.guild is None or ctx.guild.id != GUILD_DDNET or ROLE_ADMIN not in [role.id for role in ctx.author.roles]:
            return

        channel = self.bot.get_channel(CHAN_WELCOME)

        async for old_msg in channel.history(limit=None):
            await old_msg.delete()
            await asyncio.sleep(1)

        welcome_banners_dir = 'data/welcome_banners'
        welcome_banners = []

        for filename in sorted(os.listdir(welcome_banners_dir)):
            if filename.endswith('.png'):
                variable_name = filename.split('.png')[0]
                welcome_banner = discord.File(os.path.join(welcome_banners_dir, filename), filename=filename)
                welcome_banners.append((variable_name, welcome_banner))

        welcome_text_module = importlib.import_module('data.welcome_banners.welcome_text')

        messages = [
            (welcome_banners[0][1], getattr(welcome_text_module, 'main')),
            (welcome_banners[1][1], getattr(welcome_text_module, 'rules')),
            (welcome_banners[2][1], getattr(welcome_text_module, 'channel_listing')),
            (welcome_banners[3][1], getattr(welcome_text_module, 'ddnet_links')),
            (welcome_banners[4][1], getattr(welcome_text_module, 'ddnet_roles')),
            (welcome_banners[5][1], getattr(welcome_text_module, 'community_links'))
        ]

        for message in messages:
            await channel.send(file=message[0])
            await channel.send(message[1], allowed_mentions=discord.AllowedMentions(roles=False))

    @commands.command(name='update', hidden=True)
    async def update_welcome_message(self, ctx, message_id, message_variable):
        channel = self.bot.get_channel(CHAN_WELCOME)

        try:
            welcome_text_module = importlib.import_module('data.welcome_banners.welcome_text')
            message_variable = getattr(welcome_text_module, message_variable, None)

            if message_variable is None:
                await ctx.reply(f"Invalid variable name.")
                return

            message_id = int(message_id)
            message_to_edit = await channel.fetch_message(message_id)
            await message_to_edit.edit(content=message_variable)
            await ctx.message.add_reaction("👌")

        except (ValueError, discord.NotFound):
            await ctx.send("Invalid message ID. Please provide a valid message ID sent by the bot.")


async def setup(bot):
    await bot.add_cog(Welcome(bot))
