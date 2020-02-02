from typing import Callable, List, Tuple, Union

from PIL import Image, ImageDraw, ImageFont


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

def wrap_new(canv: ImageDraw.Draw, box: Tuple[Tuple[int, int], Tuple[int, int]], text: str, *, font: ImageFont.FreeTypeFont):
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
