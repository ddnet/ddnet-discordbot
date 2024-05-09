from io import BytesIO
from typing import Callable, List, Tuple, Union

from PIL import Image, ImageDraw, ImageFont, ImageOps


def save(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format='png')
    buf.seek(0)
    return buf


def center(size: int, area_size: int = 0) -> int:
    return int((area_size - size) / 2)


def round_rectangle(size: Tuple[int, int], radius: int, *, color: Tuple[int, int, int, int]) -> Image.Image:
    width, height = size

    radius = min(width, height, radius * 2)
    width *= 2
    height *= 2

    corner = Image.new('RGBA', (radius, radius))
    draw = ImageDraw.Draw(corner)
    xy = (0, 0, radius * 2, radius * 2)
    draw.pieslice(xy, 180, 270, fill=color)

    rect = Image.new('RGBA', (width, height), color=color)
    rect.paste(corner, (0, 0))  # upper left
    rect.paste(corner.rotate(90), (0, height - radius))  # lower left
    rect.paste(corner.rotate(180), (width - radius, height - radius))  # lower right
    rect.paste(corner.rotate(270), (width - radius, 0))  # upper right

    return rect.resize(size, resample=Image.LANCZOS, reducing_gap=1.0)  # antialiasing


def auto_font(font: Union[ImageFont.FreeTypeFont, Tuple[str, int]], text: str, max_width: int,
              *, check: Callable = lambda w, _: w) -> ImageFont.FreeTypeFont:
    if isinstance(font, tuple):
        font = ImageFont.truetype(*font)

    while check(font.getsize(text)[0], font.size) > max_width:
        font = ImageFont.truetype(font.path, font.size - 1)

    return font


def wrap_new(canv: ImageDraw.Draw, box: Tuple[Tuple[int, int], Tuple[int, int]], text: str, *,
             font: ImageFont.FreeTypeFont):
    _, h = font.getsize('yA')

    max_width = box[1][0] - box[0][0]
    max_height = box[1][1]

    def write(x: int, y: int, line: List[str]):
        text_ = ' '.join(line)
        font_ = auto_font(font, text_, max_width)
        w, h = font_.getsize(text_)
        xy = (x + center(w, max_width), y)
        canv.text(xy, text_, fill='black', font=font_)

    x, y = box[0]
    line = []
    for word in text.split():
        w, _ = font.getsize(' '.join(line + [word]))

        if w > max_width:
            write(x, y, line)

            y += h
            if y > max_height:
                return

            line = [word]
        else:
            line.append(word)

    if line:
        write(x, y, line)


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
