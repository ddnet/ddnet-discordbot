#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands


class Records(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild = self.bot.guild
        self.adapter = discord.AsyncWebhookAdapter(self.bot.session)

    @property
    def records_chan(self) -> discord.TextChannel:
        return discord.utils.get(self.guild.text_channels, name='records')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel != self.records_chan:
            return

        if message.webhook_id is None:
            return

        query = 'SELECT id, token FROM records_webhooks;'
        webhooks = await self.bot.pool.fetch(query)

        for id_, token in webhooks:
            try:
                webhook = discord.Webhook.partial(id=id_, token=token, adapter=self.adapter)
                await webhook.send(content=message.content)
            except discord.NotFound:
                query = 'DELETE FROM records_webhooks WHERE id = $1;'
                await self.bot.pool.execute(query, webhook.id)

    @commands.group()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def records(self, ctx: commands.Context):
        """Keep track of top 1 ranks and finishes on hard maps"""
        pass

    @records.command(name='register')
    async def records_register(self, ctx: commands.Context):
        """Register a channel as a records channel"""
        channel = ctx.channel
        webhooks = await channel.webhooks()

        for webhook in webhooks:
            query = 'SELECT TRUE FROM records_webhooks WHERE id = $1;'
            exists = await self.bot.pool.fetchrow(query, webhook.id)
            if exists:
                return await ctx.send('This channel is already registered as a records channel')

        avatar = self.bot.user.avatar_url_as(format='png')
        webhook = await channel.create_webhook(name='DDNet', avatar=await avatar.read())

        query = 'INSERT INTO records_webhooks (id, token) VALUES ($1, $2);'
        await self.bot.pool.execute(query, webhook.id, webhook.token)

        await ctx.send(f'Registered {channel.mention} as a records channel')

    @records.command(name='unregister')
    async def records_unregister(self, ctx: commands.Context):
        """Unregister a channel as a records channel"""
        channel = ctx.channel
        webhooks = await channel.webhooks()

        for webhook in webhooks:
            query = 'DELETE FROM records_webhooks WHERE id = $1 RETURNING TRUE;'
            exists = await self.bot.pool.fetchrow(query, webhook.id)
            if exists:
                try:
                    await webhook.delete()
                except discord.NotFound:
                    pass

                # don't break here as the channel could have multiple record webhooks

        await ctx.send(f'Unregistered {channel.mention} as a records channel')


def setup(bot: commands.Bot):
    bot.add_cog(Records(bot))
