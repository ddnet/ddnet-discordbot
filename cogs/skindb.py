import discord
from discord.ext import commands
import re
import logging
import asyncio
from io import BytesIO
from PIL import Image

from config import GUILD_DDNET, CHAN_SKIN_SUBMIT, CHAN_SKIN_INFO, ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_SKIN_DB_CREW, \
    f3_emoji, f4_emoji
from utils.discord_utils import check_if_staff, is_staff
from utils.image import crop_and_generate_image


def check_image_format(message: discord.Message):
    for attachment_type in message.attachments:
        if attachment_type.content_type != 'image/png':
            return False
    return True


def check_image_resolution(message: discord.Message):
    for attachment in message.attachments:
        if attachment.height in (128, 256) and attachment.width in (128, 256):
            return f'- At least one of the attached skins must have a resolution of 256x128', 'Missing 256x128px skin'

        if attachment.height not in (128, 256) or attachment.width not in (256, 512):
            return f'- One of the attached skins does not have the correct image resolution. Resolution must be 256x128, ''and if possible provide a 512x256 along with the 256x128', 'Bad image resolution'
    return None, None


def check_message_structure(message: discord.Message):
    # Regex to make licenses optional:
    # "^(?P<skin_name>['\"].+['\"]) by (?P<creator_name>.+?)( (\((?P<license>CC0|CC-BY|CC-BY-SA)\)))?$"gm
    regex = re.compile(r"^\"(?P<skin_name>.+)\" by (?P<user_name>.+) (\((?P<license>.{3,8})\))$", re.IGNORECASE)
    re_match = regex.match(message.content)
    if not re_match:
        return f'- Your message isn\'t properly formatted. Follow the message structure written in <#{CHAN_SKIN_INFO}>. Also keep in mind licenses are now required for every submission.', 'Bad message structure'

    licenses = ["CC0", "CC BY", "CC BY-SA"]
    if re_match.group('license'):
        if not re_match.group('license') in licenses:
            return ('- Bad License. Possible licenses: `(CC0)`, `(CC BY)` or `(CC BY-SA)`\n'
                    '```md\n'
                    '# Recommended License Types\n'
                    'CC0 - skin is common property, everyone can use/edit/share it however they like\n'
                    'CC BY - skin can be used/edited/shared, but must be credited\n'
                    'CC BY-SA - skin can be used/edited/shared, but must be credited and '
                    'derived works must also be shared under the same license```'), 'License Missing or invalid'

    if len(re_match.group('skin_name')) >= 24:
        return 'The skin name should not exceed 23 characters in length. Spaces count as characters too.', 'Skin name too long, 23 characters max.'

    return None, None


class SkinDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.f3_emoji = self.bot.get_emoji(f3_emoji)
        self.f4_emoji = self.bot.get_emoji(f4_emoji)
        # im using a dict to store all message ids for now
        self.original_message_id_and_preview_message_id = {}
        self.roles = (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_SKIN_DB_CREW)

    @commands.Cog.listener('on_message')
    async def check_message_format_and_render(self, message: discord.Message):
        if check_if_staff(message, self.roles) or message.author.bot:
            return

        error_messages = []
        log_errors = []
        if len(message.attachments) == 0:
            error_messages.append(
                f'- Your submission is missing attachments. Attach all skins to your submission message.')
            log_errors.append('Missing attachments')

        if not check_image_format(message):
            error_messages.append(f'- Wrong image format. Only PNGs are allowed.')
            log_errors.append('Incorrect image format')

        check_message, error = check_image_resolution(message)
        if check_message is not None:
            error_messages.append(check_message)
            log_errors.append(error)

        check_message, error = check_message_structure(message)
        if check_message is not None:
            error_messages.append(check_message)
            log_errors.append(error)

        if not len(message.attachments) > 2:
            error_messages.append(
                '- Only 2 attachments per submission. Don\'t attach any additional images or gifs, please.')
            log_errors.append('Exceeded upload limit')

        if error_messages:
            await message.delete()
            log_errors = f'Skin submit errors by {message.author}: {", ".join(log_errors)}'
            logging.info(log_errors)

            try:
                error_messages.insert(0, "Submit Errors: ")
                await message.author.send("\n".join(error_messages))
            except discord.Forbidden:
                logging.info(f'Skin submit: Unable to DM {message.author} due to their privacy settings.')
                privacy_err = (f'Skin submission failed. Unable to DM {message.author.mention}. '
                               f'Change your privacy settings to allow direct messages from this server.')
                privacy_err_msg = await message.channel.send(content=privacy_err)
                await asyncio.sleep(120)  # 2 min
                await privacy_err_msg.delete()
        else:
            attachments = message.attachments
            images = []
            for attachment in attachments:
                img_bytes = await attachment.read()
                img = Image.open(BytesIO(img_bytes))
                images.append(img)

            image_to_process = None
            for img in images:
                if img.size == (256, 128):
                    image_to_process = img
                    break

            processed_images = crop_and_generate_image(image_to_process)

            final_image = Image.new('RGBA', (512, 64))

            x_offset = 0
            y_offset = 0
            for name, processed_img in processed_images.items():
                final_image.paste(processed_img, (x_offset, y_offset))
                x_offset += processed_img.size[0]
                if x_offset >= final_image.size[0]:
                    x_offset = 0
                    y_offset += processed_img.size[1]

            byte_io = BytesIO()
            final_image.save(byte_io, 'PNG')
            byte_io.seek(0)
            file = discord.File(byte_io, filename='final_image.png')

            image_preview_message = await message.channel.send(file=file)
            self.original_message_id_and_preview_message_id[message.id] = image_preview_message.id

            await message.add_reaction(self.f3_emoji)
            await message.add_reaction(self.f4_emoji)

    @commands.Cog.listener('on_message_delete')
    async def message_delete_handler(self, message: discord.Message):
        if message.id in self.original_message_id_and_preview_message_id:
            preview_message_id = self.original_message_id_and_preview_message_id[message.id]
            preview_message = await message.channel.fetch_message(preview_message_id)
            await preview_message.delete()
            del self.original_message_id_and_preview_message_id[message.id]

    @commands.Cog.listener('on_message_edit')
    async def message_edit_handler(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.guild.id != GUILD_DDNET or before.channel.id != CHAN_SKIN_SUBMIT or before.author.bot or is_staff(before.author, self.roles):
            return

        if before.content != after.content:
            await after.delete()
            await after.author.send('Editing submissions is not allowed. Please re-submit your submissions.')


async def setup(bot: commands.Bot):
    await bot.add_cog(SkinDB(bot))
