import discord
from discord.ext import commands
import re
from io import BytesIO
from PIL import Image, ImageOps

GUILD_DDNET       = 930664819303002123
CHAN_SKIN_SUBMIT  = 986107035747766292
ROLE_ADMIN        = 930665626370985994
ROLE_DISCORD_MOD  = 934131865512730656
ROLE_SKIN_DB_CREW = 930665730091929650


def is_staff(member: discord.Member) -> bool:
    return any(r.id in (ROLE_ADMIN, ROLE_DISCORD_MOD, ROLE_SKIN_DB_CREW) for r in member.roles)


def check_if_staff(message: discord.Message):
    author = message.author
    return message.guild is None or message.guild.id != GUILD_DDNET or message.channel.id != CHAN_SKIN_SUBMIT or is_staff(author)


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

        if len(message.attachments) > 2:
            await message.author.send(
                    'Only 2 attachments per submission. '
                    'Don\'t attach any additional images or gifs, please.'
            )
            await message.delete()
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

            if not image_to_process:
                await message.author.send("One of the attachments should be 128x256.")
                return

            processed_images = crop_and_generate_image(images[0])

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

            f3_emoji = self.bot.get_emoji(933103235651223632)
            f4_emoji = self.bot.get_emoji(933102663841751061)
            await message.add_reaction(f3_emoji)
            await message.add_reaction(f4_emoji)

    @commands.Cog.listener('on_message_delete')
    async def message_delete_handler(self, message: discord.Message):
        if message.id in self.original_message_id_and_preview_message_id:
            preview_message_id = self.original_message_id_and_preview_message_id[message.id]
            preview_message = await message.channel.fetch_message(preview_message_id)
            await preview_message.delete()
            del self.original_message_id_and_preview_message_id[message.id]


def setup(bot: commands.Bot):
    bot.add_cog(SkinDB(bot))
    