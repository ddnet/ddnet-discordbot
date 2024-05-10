import math
from typing import Tuple, Union

# http://alienryderflex.com/hsp.html

PR = 0.299
PG = 0.587
PB = 0.114


def rgb_to_hsp(rgb: Union[int, Tuple[int, int, int]]) -> Tuple[float, float, float]:
    if isinstance(rgb, int):
        rgb = unpack_rgb(rgb)

    if not all(0 <= v <= 255 for v in rgb):
        raise ValueError('RGB values have to be on a scale of 0 to 255')

    r, g, b = (v / 255 for v in rgb)

    # perceived brightness
    p = math.sqrt(PR * r ** 2 + PG * g ** 2 + PB * b ** 2)

    # hue and saturation
    if r == g and r == b:  # all same
        h = 0
        s = 0
    elif r >= g and r >= b:  # r is largest
        if b >= g:
            h = 1 - (b - g) / (6 * (r - g))
            s = 1 - g / r
        else:
            h = (g - b) / (6 * (r - b))
            s = 1 - b / r
    elif g >= r and g >= b:  # g is largest
        if r >= b:
            h = 2 / 6 - (r - b) / (6 * (g - b))
            s = 1 - b / g
        else:
            h = 2 / 6 + (b - r) / (6 * (g - r))
            s = 1 - r / g
    else:  # b is largest
        if g >= r:
            h = 4 / 6 - (g - r) / (6 * (b - r))
            s = 1 - r / b
        else:
            h = 4 / 6 + (r - g) / (6 * (b - g))
            s = 1 - g / b

    return h, s, p


def hsp_to_rgb(hsp: Tuple[float, float, float]) -> tuple[int, ...]:
    if not all(0 <= v <= 1 for v in hsp):
        raise ValueError('HSP values have to be on a scale of 0 to 1')

    h, s, p = hsp

    min_over_max = 1 - s

    if min_over_max > 0:
        if h < 1 / 6:  # r > g > b
            h *= 6
            part = 1 + h * (1 / min_over_max - 1)
            b = p / math.sqrt(PR / (min_over_max * 2) + PG * part ** 2 + PB)
            r = b / min_over_max
            g = b + h * (r - b)
        elif h < 2 / 6:  # g > r > b
            h = 6 * (2 / 6 - h)
            part = 1 + h * (1 / min_over_max - 1)
            b = p / math.sqrt(PG / (min_over_max * 2) + PR * part ** 2 + PB)
            g = b / min_over_max
            r = b + h * (g - b)
        elif h < 3 / 6:  # g > b > r
            h = 6 * (h - 2 / 6)
            part = 1 + h * (1 / min_over_max - 1)
            r = p / math.sqrt(PG / (min_over_max * 2) + PB * part ** 2 + PR)
            g = r / min_over_max
            b = r + h * (g - r)
        elif h < 4 / 6:  # b > g > r
            h = 6 * (4 / 6 - h)
            part = 1 + h * (1 / min_over_max - 1)
            r = p / math.sqrt(PB / (min_over_max * 2) + PG * part ** 2 + PR)
            b = r / min_over_max
            g = r + h * (b - r)
        elif h < 5 / 6:  # b > r > g
            h = 6 * (h - 4 / 6)
            part = 1 + h * (1 / min_over_max - 1)
            g = p / math.sqrt(PB / (min_over_max * 2) + PR * part ** 2 + PG)
            b = g / min_over_max
            r = g + h * (b - g)
        else:  # r > b > g
            h = 6 * (1 - h)
            part = 1 + h * (1 / min_over_max - 1)
            g = p / math.sqrt(PR / (min_over_max * 2) + PB * part ** 2 + PG)
            r = g / min_over_max
            b = g + h * (r - g)
    else:
        if h < 1 / 6:  # r > g > b
            h *= 6
            r = math.sqrt(p ** 2 / (PR + PG * h ** 2))
            g = r * h
            b = 0
        elif h < 2 / 6:  # g > r > b
            h = 6 * (2 / 6 - h)
            g = math.sqrt(p ** 2 / (PG + PR * h ** 2))
            r = g * h
            b = 0
        elif h < 3 / 6:  # g > b > r
            h = 6 * (h - 2 / 6)
            g = math.sqrt(p ** 2 / (PG + PB * h ** 2))
            b = g * h
            r = 0
        elif h < 4 / 6:  # b > g > r
            h = 6 * (4 / 6 - h)
            b = math.sqrt(p ** 2 / (PB + PG * h ** 2))
            g = b * h
            r = 0
        elif h < 5 / 6:  # b > r > g
            h = 6 * (h - 4 / 6)
            b = math.sqrt(p ** 2 / (PB + PR * h ** 2))
            r = b * h
            g = 0
        else:  # r > b > g
            h = 6 * (1 - h)
            r = math.sqrt(p ** 2 / (PR + PB * h ** 2))
            b = r * h
            g = 0

    mult = max(r, g, b, 1)  # adjust invalid values > 1

    return tuple(round(v / mult * 255) for v in (r, g, b))


def clamp_luminance(rgb: Union[int, Tuple[int, int, int]], degrees: float) -> tuple[int, ...]:
    h, s, p = rgb_to_hsp(rgb)
    return hsp_to_rgb((h, s, max(p, degrees)))


def pack_rgb(rgb: Tuple[int, int, int]) -> int:
    r, g, b = rgb
    return (b << 16) | (g << 8) | r


def unpack_rgb(rgb: int) -> Tuple[int, int, int]:
    return 0xff & rgb, (0xff00 & rgb) >> 8, (0xff0000 & rgb) >> 16
