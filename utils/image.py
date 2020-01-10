from typing import Tuple

from PIL import Image, ImageDraw


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
