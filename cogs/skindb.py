import discord
from discord.ext import commands
import re

GUILD_DDNET               =
SKINS_SUBMIT_CHANNEL_ID   =   
ADMIN_ROLE_ID             =             
DISCORD_MODERATOR_ROLE_ID = 
SKIN_DB_CREW_ROLE_ID      =      

def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ADMIN_ROLE_ID, DISCORD_MODERATOR_ROLE_ID, SKIN_DB_CREW_ROLE_ID) for r in member.roles)

def check_if_staff(message: discord.Message):
    author = message.author
    return message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id != SKINS_SUBMIT_CHANNEL_ID or is_staff(author)

def check_if_has_attachments(message: discord.Message):
    if len(message.attachments) == 0:
        return (False, 'Your submission is missing attachments. Attach all skins to one message and follow the correct message format written in <#986941590780149780>')
    return (True, None)

def check_image_format(message: discord.Message):
    for attachment_type in message.attachments:
        if attachment_type.content_type != 'image/png':
            return (False, 'Wrong image format. Only PNGs are allowed.')
    return (True, None)

def check_image_resolution(message: discord.Message):
    for attachment in message.attachments:
        if (attachment.height != 128 or attachment.width != 256) and (attachment.height != 256 or attachment.width != 512):
            return (False, 'One of the attached skins does not have the correct image resolution. Resolution must be 256x128, and if possible provide a 512x256 along with the 256x128')
    return (True, None)

def check_text_format(message: discord.Message):
    # Regex to make licenses optional: "^(?P<skin_name>['\"].+['\"]) by (?P<creator_name>.+?)( (\((?P<license>CC0|CC-BY|CC-BY-SA)\)))?$"gm
    regex = re.compile(r"^\"(?P<skin_name>.+)\" by (?P<user_name>.+) (\((?P<license>.{3,8})\))$", re.IGNORECASE)
    re_match = regex.match(message.content)
    if not re_match:
        return (False,
                'Your message isn\'t properly formatted. Follow the message format written in <#986941590780149780>. Also keep in mind licenses are now required for every submission.')

    licenses = ["CC0", "CC-BY", "CC-BY-SA"]
    if re_match.group('license') is not None:
        if not any(lisense in re_match.group('license') for lisense in licenses):
            return (False, 'Wrong License. Possible licenses: `(CC0)`, `(CC-BY)` or `(CC-BY-SA)`'
                           '\n```md'
                           '\n# Recommended License Types'
                           '\nCC0 - skin is common property, everyone can use/edit/share it however they like'
                           '\nCC-BY - skin can be used/edited/shared, but must be credited'
                           '\nCC-BY-SA - skin can be used/edited/shared, but must be credited and derived works must also be shared under the same license```')
    return (True, None)


class SkinDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_message')
    async def message_handler(self, message: discord.Message):
        if check_if_staff(message):
            return

        check_result, check_message = check_if_has_attachments(message)
        if not check_result:
            await message.delete()
            await message.author.send(check_message)
            return

        check_result, check_message = check_image_format(message)
        if not check_result:
            await message.delete()
            await message.author.send(check_message)
            return

        check_result, check_message = check_image_resolution(message)
        if not check_result:
            await message.delete()
            await message.author.send(check_message)
            return

        check_result, check_message = check_text_format(message)
        if not check_result:
            await message.delete()
            await message.author.send(check_message)
            return

        f3_emoji = self.bot.get_emoji()
        f4_emoji = self.bot.get_emoji()

        if len(message.attachments) > 2:
            await message.author.send(
                    'Only 2 attachments per submission. '
                    'Don\'t attach any additional images or gifs, please.'
            )
            await message.delete()
        else:
            await message.add_reaction(f3_emoji)
            await message.add_reaction(f4_emoji)

def setup(bot):
    bot.add_cog(SkinDB(bot))