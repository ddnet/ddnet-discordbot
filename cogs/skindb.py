import discord
from discord.ext import commands
import re
import logging
import asyncio
from io import BytesIO
from PIL import Image, ImageOps

GUILD_DDNET       = 252358080522747904
CHAN_SKIN_SUBMIT  = 985717921600929872
ROLE_ADMIN        = 293495272892399616
ROLE_DISCORD_MOD  = 737776812234506270
ROLE_SKIN_DB_CREW = 390516461741015040


def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_SKIN_DB_CREW) for r in member.roles)


def check_if_staff(message: discord.Message):
    author = message.author
    return (message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id != CHAN_SKIN_SUBMIT
            or is_staff(author))


def check_if_has_attachments(message: discord.Message):
    if len(message.attachments) == 0:
        return (False, f'- Your submission is missing attachments. Attach all skins to your submission message.',
                'Missing attachments')
    return True, None, None


def check_image_format(message: discord.Message):
    for attachment_type in message.attachments:
        if attachment_type.content_type != 'image/png':
            return (
                False,
                f'- Wrong image format. Only PNGs are allowed.',
                'Incorrect image format'
            )
    return True, None, None


def check_image_resolution(message: discord.Message):
    has_256x128 = False
    for attachment in message.attachments:
        if ((attachment.height == 256 and attachment.width == 128) or
                (attachment.height == 128 and attachment.width == 256)):
            has_256x128 = True

        if ((attachment.height != 128 or attachment.width != 256) and
                (attachment.height != 256 or attachment.width != 512)):
            return (
                False,
                (f'- One of the attached skins does not have the correct image resolution. Resolution must be 256x128, '
                 'and if possible provide a 512x256 along with the 256x128'),
                'Bad image resolution'
            )
    if not has_256x128:
        return (
            False,
            f'- At least one of the attached skins must have a resolution of 256x128',
            'Missing 256x128px skin'
        )
    return True, None, None

def check_attachment_amount(message: discord.Message):
    if len(message.attachments) > 2:
        return (
            False,
            f'- Only 2 attachments per submission. Don\'t attach any additional images or gifs, please.',
            'Exceeded upload limit'
        )
    return True, None, None

def check_message_structure(message: discord.Message):
    # Regex to make licenses optional:
    # "^(?P<skin_name>['\"].+['\"]) by (?P<creator_name>.+?)( (\((?P<license>CC0|CC-BY|CC-BY-SA)\)))?$"gm
    regex = re.compile(r"^\"(?P<skin_name>.+)\" by (?P<user_name>.+) (\((?P<license>.{3,8})\))$", re.IGNORECASE)
    re_match = regex.match(message.content)
    if not re_match:
        return (
            False,
            ('- Your message isn\'t properly formatted. Follow the message structure written in <#986941590780149780>. '
            'Also keep in mind licenses are now required for every submission.'),
            'Bad message structure'
        )

    licenses = ["CC0", "CC BY", "CC BY-SA"]
    if re_match.group('license'):
        if not re_match.group('license') in licenses:
            return (
                False,
                ('- Bad License. Possible licenses: `(CC0)`, `(CC BY)` or `(CC BY-SA)`\n'
                 '```md\n'
                 '# Recommended License Types\n'
                 'CC0 - skin is common property, everyone can use/edit/share it however they like\n'
                 'CC BY - skin can be used/edited/shared, but must be credited\n'
                 'CC BY-SA - skin can be used/edited/shared, but must be credited and '
                 'derived works must also be shared under the same license```'),
                'License Missing or invalid'
            )

    if len(re_match.group('skin_name')) >= 24:
        return (
            False,
            'The skin name should not exceed 23 characters in length. Spaces count as characters too.',
            'Skin name too long, 23 characters max.'
        )

    return True, None, None


def crop_and_generate_image(img):
    image = img

    image_body_shadow = image.crop((96, 0, 192, 96))
    image_feet_shadow_back = image.crop((192, 64, 255, 96))
    image_feet_shadow_front = image.crop((192, 64, 255, 96))
    image_body = image.crop((0, 0, 96, 96))
    image_feet_front = image.crop((192, 32, 255, 64))
    image_feet_back = image.crop((192, 32, 255, 64))

    # default eyes
    image_default_left_eye = image.crop((64, 96, 96, 128))
    image_default_right_eye = image.crop((64, 96, 96, 128))

    # evil eyes
    image_evil_l_eye = image.crop((96, 96, 128, 128))
    image_evil_r_eye = image.crop((96, 96, 128, 128))

    # hurt eyes
    image_hurt_l_eye = image.crop((128, 96, 160, 128))
    image_hurt_r_eye = image.crop((128, 96, 160, 128))

    # happy eyes
    image_happy_l_eye = image.crop((160, 96, 192, 128))
    image_happy_r_eye = image.crop((160, 96, 192, 128))

    # surprised eyes
    image_surprised_l_eye = image.crop((224, 96, 255, 128))
    image_surprised_r_eye = image.crop((224, 96, 255, 128))

    def resize_image(image, scale):
        width, height = image.size
        new_width = int(width * scale)
        new_height = int(height * scale)
        return image.resize((new_width, new_height))

    image_body_resized = resize_image(image_body, 0.66)
    image_body_shadow_resized = resize_image(image_body_shadow, 0.66)

    image_left_eye = resize_image(image_default_left_eye, 0.8)
    image_right_eye = resize_image(image_default_right_eye, 0.8)
    image_right_eye_flipped = ImageOps.mirror(image_right_eye)

    image_evil_l_eye = resize_image(image_evil_l_eye, 0.8)
    image_evil_r_eye = resize_image(image_evil_r_eye, 0.8)
    image_evil_r_eye_flipped = ImageOps.mirror(image_evil_r_eye)

    image_hurt_l_eye = resize_image(image_hurt_l_eye, 0.8)
    image_hurt_r_eye = resize_image(image_hurt_r_eye, 0.8)
    image_hurt_r_eye_flipped = ImageOps.mirror(image_hurt_r_eye)

    image_happy_l_eye = resize_image(image_happy_l_eye, 0.8)
    image_happy_r_eye = resize_image(image_happy_r_eye, 0.8)
    image_happy_r_eye_flipped = ImageOps.mirror(image_happy_r_eye)

    image_surprised_l_eye = resize_image(image_surprised_l_eye, 0.8)
    image_surprised_r_eye = resize_image(image_surprised_r_eye, 0.8)
    image_surprised_r_eye_flipped = ImageOps.mirror(image_surprised_r_eye)

    def paste_part(part, canvas, pos):
        padded = Image.new('RGBA', canvas.size)
        padded.paste(part, pos)
        return Image.alpha_composite(canvas, padded)

    def create_tee_image(image_left_eye, image_right_eye_flipped):
        tee = Image.new("RGBA", (96, 64), (0, 0, 0, 0))

        tee = paste_part(image_body_shadow_resized, tee, (16, 0))
        tee = paste_part(image_feet_shadow_back, tee, (8, 30))
        tee = paste_part(image_feet_shadow_front, tee, (24, 30))
        tee = paste_part(image_feet_back, tee, (8, 30))
        tee = paste_part(image_body_resized, tee, (16, 0))
        tee = paste_part(image_left_eye, tee, (39, 18))
        tee = paste_part(image_right_eye_flipped, tee, (47, 18))
        tee = paste_part(image_feet_front, tee, (24, 30))

        return tee

    tee_images = {
        'default': create_tee_image(image_left_eye, image_right_eye_flipped),
        'evil': create_tee_image(image_evil_l_eye, image_evil_r_eye_flipped),
        'hurt': create_tee_image(image_hurt_l_eye, image_hurt_r_eye_flipped),
        'happy': create_tee_image(image_happy_l_eye, image_happy_r_eye_flipped),
        'surprised': create_tee_image(image_surprised_l_eye, image_surprised_r_eye_flipped)
    }
    return tee_images


class SkinDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # im using a dict to store all message ids for now
        self.original_message_id_and_preview_message_id = {}

    @commands.Cog.listener('on_message')
    async def check_message_format_and_render(self, message: discord.Message):
        if check_if_staff(message) or message.author.bot:
            return

        error_messages = []
        log_errors = []

        check_result, check_message, error = check_if_has_attachments(message)
        if not check_result:
            error_messages.append(check_message)
            log_errors.append(error)

        check_result, check_message, error = check_image_format(message)
        if not check_result:
            error_messages.append(check_message)
            log_errors.append(error)

        check_result, check_message, error = check_image_resolution(message)
        if not check_result:
            error_messages.append(check_message)
            log_errors.append(error)

        check_result, check_message, error = check_message_structure(message)
        if not check_result:
            error_messages.append(check_message)
            log_errors.append(error)

        check_result, check_message, error = check_attachment_amount(message)
        if not check_result:
            error_messages.append(check_message)
            log_errors.append(error)

        if error_messages:
            await message.delete()
            log_errors[0] = f'Skin submit errors by {message.author}: {", ".join(log_errors)}'
            logging.info(log_errors[0])

            try:
                error_messages.insert(0, "Submit Errors: ")
                await message.author.send("\n".join(error_messages))
            except discord.Forbidden:
                logging.info(f'Skin submit: Unable to DM {message.author} due to their privacy settings.')
                privacy_err = (f'Skin submission failed. Unable to DM {message.author.mention}. '
                                 f'Change your privacy settings to allow direct messages from this server.')
                privacy_err_msg = await message.channel.send(content=privacy_err)
                await asyncio.sleep(2 * 60)
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

            f3_emoji = self.bot.get_emoji(346683497701834762)
            f4_emoji = self.bot.get_emoji(346683496476966913)
            await message.add_reaction(f3_emoji)
            await message.add_reaction(f4_emoji)

    @commands.Cog.listener('on_message_delete')
    async def message_delete_handler(self, message: discord.Message):
        if message.id in self.original_message_id_and_preview_message_id:
            preview_message_id = self.original_message_id_and_preview_message_id[message.id]
            preview_message = await message.channel.fetch_message(preview_message_id)
            await preview_message.delete()
            del self.original_message_id_and_preview_message_id[message.id]

    @commands.Cog.listener('on_message_edit')
    async def message_edit_handler(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.guild.id != GUILD_DDNET or before.channel.id != CHAN_SKIN_SUBMIT \
                or before.author.bot or is_staff(before.author):
            return

        if before.content != after.content:
            await after.delete()
            await after.author.send('Editing submissions is not allowed. Please re-submit your submissions.')

async def setup(bot: commands.Bot):
    await bot.add_cog(SkinDB(bot))
