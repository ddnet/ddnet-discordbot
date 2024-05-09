import discord
from discord.ext import commands

from config import CHAN_VOICE_HIDDEN


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_channel = self.bot.get_channel(CHAN_VOICE_HIDDEN)

        if before.channel != voice_channel and after.channel == voice_channel:
            overwrite = discord.PermissionOverwrite(view_channel=True)
            await voice_channel.set_permissions(member, overwrite=overwrite)

        elif before.channel == voice_channel and after.channel != voice_channel:
            overwrite = discord.PermissionOverwrite(view_channel=False)
            await voice_channel.set_permissions(member, overwrite=overwrite)


async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
