import re
from io import BytesIO
from typing import Callable, Optional, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

SPACING = 4  # internal line spacing


def save(img: Image.Image) -> BytesIO:
    buf = BytesIO()
    img.save(buf, format='png')
    buf.seek(0)
    return buf

def center(size: int, area_size: int=0) -> int:
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
    rect.paste(corner, (0, 0))                                          # upper left
    rect.paste(corner.rotate(90), (0, height - radius))                 # lower left
    rect.paste(corner.rotate(180), (width - radius, height - radius))   # lower right
    rect.paste(corner.rotate(270), (width - radius, 0))                 # upper right

    return rect.resize(size, resample=Image.LANCZOS, reducing_gap=1.0)  # antialiasing

def auto_font(font: Union[ImageFont.FreeTypeFont, Tuple[str, int]], text: str, max_width: int,
              *, check: Callable=lambda w, _: w) -> ImageFont.FreeTypeFont:
    if isinstance(font, tuple):
        font = ImageFont.truetype(*font)

    while check(font.getsize(text)[0], font.size) > max_width:
        font = ImageFont.truetype(font.path, font.size - 1)

    return font

def wrap_text(font: ImageFont.FreeTypeFont, text: str, max_width: int, max_height: int) -> Optional[str]:
    line_height = font.size
    lines = ['']
    first_word = True

    words = re.split(r'(\s+)', text)
    for word in words:
        if first_word:
            word_width = font.getlength(word)

            if word_width > max_width:
                # word is too long
                return None

            lines[-1] = word
            first_word = False
        else:
            line_width = font.getlength(lines[-1] + word)

            if line_width > max_width:
                word_width = font.getlength(word)
                num_lines = len(lines) + 1
                text_height = (num_lines * line_height) + (num_lines * SPACING)

                if word_width > max_width or text_height > max_height:
                    # word is too long or adding a new line exceeds max height
                    return None

                lines.append(word) # add word on the next line
                lines[-1] = lines[-1].strip()
            else:
                lines[-1] = lines[-1] + word # add word on the current line

    return '\n'.join(lines).strip()

def auto_wrap_text(font: ImageFont.FreeTypeFont, text: str, max_width: int, max_height: int, min_font_size: int=16) -> Tuple[ImageFont.FreeTypeFont, str]:
    while font.size >= min_font_size:
        wrapped_text = wrap_text(font, text, max_width, max_height)
        if wrapped_text is not None:
            return font, wrapped_text
        
        font = font.font_variant(size=font.size - 1)

    raise ValueError("Text doesn't fit")
