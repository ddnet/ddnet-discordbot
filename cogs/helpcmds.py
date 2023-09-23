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
    async def kog(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="King of Gores / KoG",
            description="DDNet and KoG aren't affiliated."
                        "\n\nIf you require assistance on a server within the KoG tab, "
                        "join their Discord server by clicking on the link below.",
            colour=discord.Colour.random())
        embed.add_field(
            name="URL:",
            value="https://discord.kog.tw/")

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

    @commands.command(name='login')
    async def kog_login(self, ctx: commands.Context):
        file = discord.File('data/avatar.png', filename='avatar.png')

        embed = discord.Embed(
            title="KoG Login and Account Migration",
            description="",
            colour=discord.Colour.random())
        embed.add_field(
            name='',
            value='If you already had an account on KoG, watch the following video: [www.youtube.com](https://www.youtube.com/watch?v=d1kbt-srlac)',
            inline=False
        )
        embed.add_field(
            name=f'For new Players:',
            value=f'First create an Account:'
                  f'\n1. Click on the following link: [kog.tw](https://kog.tw/register.php)'
                  f'\n2. Enter your in-game name, your e-mail address and a password'
                  f'\n3. If the name is not already registered, you should now receive a message that the "name has been pre-claimed"'
                  f'\n4. Join the KoG discord server: [KoG Discord](https://discord.kog.tw)'
                  f'\n5. Create a ticket in KoG\'s discord by clicking on the registration button in #create-a-ticket channel, so a moderator can confirm you.'
                  f'\n6. Now go to the login page: [kog.tw](https://kog.tw/login.php) and login with the credentials you have used to register.'
                  f'\n7. Click on your name in the top right-hand corner of the website and select "Dashboard"'
                  f'\n8. Scroll down to accept the ToS (Terms of Service)'
        )
        embed.add_field(
            name='Migration Guide:',
            value='1. Click on the following link: [kog.tw](https://auth.kog.tw/)'
                  '\n2. Click the register button and fill in all your information (Note: You can put anything in First name and Surname. Does not need to be your real information)'
                  '\n3. After clicking the next button you should receive an e-mail with a code.'
                  '\n4. Open the e-mail and click the blue button or copy the code'
                  '\n5. You should now see "User activated" - click next and login'
                  '\n6. Now you can choose if you want to use two factor authentication (Optional, but recommended)'
                  '\n7. Navigate back to this link [kog.tw](https://kog.tw/) login and click the start migration button'
                  '\n8. Now there should be a blue "next" button - click that button then click the blue start migration button.'
                  '\n9. You should now receive an e-mail from KoG - click on the "migrate now" button.'
                  '\n10. Now click the blue "login to kog one" button and then login with your zitadel account.'
                  '\n11. It should now say: "Account successfully queued for migration."'
                  '\n12. You\'re done.',
            inline=True
        )
        embed.add_field(
            name='How to Login:',
            value='1. Click on the following link: [kog.tw](https://kog.tw/login.php) and log in.'
                  '\n2. Click on your name in the top right-hand corner and select "Ingame login".'
                  '\n3. Click on the yellow button saying "generate a login".'
                  '\n4. Join any KoG server and paste the /login command',
            inline=False
        )
        embed.add_field(
            name=f'This is not required on DDNet.',
            value=f'',
            inline=False)
        embed.set_thumbnail(url='attachment://avatar.png')

        await ctx.send(file=file, embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCommands(bot))
