import discord
from discord.ext import commands


class HelpCommands(commands.Cog, name='Help Commands'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def staff(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="DDNet Staff List",
            description="The link below will give you a full list of all DDNet staff members.",
            colour=discord.Colour.random())
        embed.add_field(
            name="URL:",
            value="https://ddnet.org/staff/")
        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def configdir(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="DDNet config directory & settings_ddnet.cfg location:",
            description="\n\n__**On Windows:**__"
                        "\nOld: `%appdata%\Teeworlds`"
                        "\nNew: `%appdata%\DDNet`"
                        "\n\n__**On Linux:**__"
                        "\nOld: `~/.teeworlds`"
                        "\nNew: `~/.local/share/ddnet`"
                        "\n\n__**On macOS:**__"
                        "\nOld: `~/Library/Application Support/Teeworlds`"
                        "\nNew: `~/Library/Application Support/DDNet`"
                        "\n\nThe settings_ddnet.cfg file contains all your friends, control, player & game settings.",
            colour=discord.Colour.random())

        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def deepfly(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')
        bindconfig = discord.File('data/deepfly.txt', filename='deepfly.txt')
        embed = discord.Embed(
            title="How to bind and configure deepfly:",
            description="It is __highly recommended to read__ the article below thoroughly, "
                        "you may learn a bunch of useful things."
                        "\n\n**URL:**"
                        "\nhttps://wiki.ddnet.org/wiki/Binds#Deepfly"
                        "\n\nIf you prefer to not read the article:"
                        "\n\nMove the attached text file to your config directory, "
                        "and then type: `exec deepfly.txt` into the ingame console (F1)."
                        "\nTo toggle deepfly on/off, press \"C\" on your keyboard.",
            colour=discord.Colour.random())

        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)
        await ctx.send(file=bindconfig)

    @commands.command()
    async def skins(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="How can I get other players to see the skin that I created?",
            description="\nThere are two ways to get other players to see your custom skin:"
                        "\n\n**Method 1:**"
                        "\nThey need to manually add your skin to their game files by pasting it in the skins "
                        "folder in the config directory."
                        "\n\n**Method 2:**"
                        "\nYour skin gets added to the official SkinDB."
                        f"\n\n For more info on how to get your skin uploaded to the SkinDB, "
                        f"visit this channel: <#{985554143525601350}>",
            colour=discord.Colour.random())

        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def binds(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="How do I bind x ?",
            description="",
            colour=discord.Colour.random())
        embed.add_field(
            name="wiki.ddnet.org",
            value="\nContent: \nThorough explanation how binds work, Deepfly, 45° Aim bind, Rainbow Tee"
                  "\n\n**URL:**"
                  "\n[wiki.ddnet.org](https://wiki.ddnet.org/wiki/Binds)")
        embed.add_field(
            name="DDNet Forums",
            value="\nContent: \nClient-, Chat-, Dummy-, Mouse-, Player- and RCON settings"
                  "\n\n**URL:**"
                  "\n[forum.ddnet.org](https://forum.ddnet.org/viewtopic.php?f=16&t=2537)")

        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def crash(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="Crash Logs",
            description="To help us debug the cause for your crash, provide the following information:"
                        "\n* Operating System"
                        "\n - Windows, Linux or macOS?"
                        "\n - 32Bit or 64Bit?"
                        "\n* Client version"
                        "\n* Steam or Standalone?"
                        "\n - Steam: Stable, Nightly or releasecandidate beta?"
                        "\n* Upload the most recent crash log file from your dumps folder in the config directory "
                        "(drag and drop it here).",
            colour=discord.Colour.random())

        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)

    @commands.command(aliases=['kog', 'login', 'registration'])
    async def kog_login(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="KoG registration and login",
            description="First and foremost: DDNet and KoG aren't affiliated.\n"
                        "You are not required to log-in on a DDNet server.\n\n"
                        "If you need help on a server related to KoG, "
                        "join their Discord server by clicking on the link below.",
            colour=discord.Colour.random())

        embed.add_field(
            name="URL:",
            value="https://discord.kog.tw/",
            inline=False)

        embed.add_field(
            name="Registration process:",
            value="https://discord.com/channels/342003344476471296/941355528242749440/1129043200527569018",
            inline=True)

        embed.add_field(
            name="Migration process:",
            value="https://discord.com/channels/342003344476471296/941355528242749440/1129043332211945492",
            inline=True)

        embed.add_field(
            name="How to login on KoG servers:",
            value="https://discord.com/channels/342003344476471296/941355528242749440/1129043447517564978",
            inline=True)

        embed.add_field(
            name="Video Guide:",
            value="https://www.youtube.com/watch?v=d1kbt-srlac",
            inline=False)
        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCommands(bot))
