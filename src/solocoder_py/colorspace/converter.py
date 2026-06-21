from __future__ import annotations

import math

from .models import HEX, HSL, HSV, RGB, _clamp


def rgb_to_hsl(rgb: RGB) -> HSL:
    r = rgb.r_float
    g = rgb.g_float
    b = rgb.b_float

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    delta = max_c - min_c

    l = (max_c + min_c) / 2.0

    if delta == 0.0:
        h = 0.0
        s = 0.0
    else:
        s = delta / (1.0 - abs(2.0 * l - 1.0)) if (1.0 - abs(2.0 * l - 1.0)) != 0 else 0.0

        if max_c == r:
            h = 60.0 * (((g - b) / delta) % 6.0)
        elif max_c == g:
            h = 60.0 * (((b - r) / delta) + 2.0)
        else:
            h = 60.0 * (((r - g) / delta) + 4.0)

        if h < 0:
            h += 360.0

    return HSL(h=h, s=s * 100.0, l=l * 100.0, alpha=rgb.alpha)


def hsl_to_rgb(hsl: HSL) -> RGB:
    h = hsl.h % 360.0
    s = hsl.s / 100.0
    l = hsl.l / 100.0

    if s == 0.0:
        r = g = b = l
    else:
        def hue_to_rgb(p: float, q: float, t: float) -> float:
            if t < 0.0:
                t += 1.0
            if t > 1.0:
                t -= 1.0
            if t < 1.0 / 6.0:
                return p + (q - p) * 6.0 * t
            if t < 1.0 / 2.0:
                return q
            if t < 2.0 / 3.0:
                return p + (q - p) * (2.0 / 3.0 - t) * 6.0
            return p

        q = l * (1.0 + s) if l < 0.5 else l + s - l * s
        p = 2.0 * l - q

        h_k = h / 360.0
        r = hue_to_rgb(p, q, h_k + 1.0 / 3.0)
        g = hue_to_rgb(p, q, h_k)
        b = hue_to_rgb(p, q, h_k - 1.0 / 3.0)

    return RGB(r * 255.0, g * 255.0, b * 255.0, alpha=hsl.alpha)


def rgb_to_hsv(rgb: RGB) -> HSV:
    r = rgb.r_float
    g = rgb.g_float
    b = rgb.b_float

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    delta = max_c - min_c

    v = max_c

    if delta == 0.0:
        h = 0.0
        s = 0.0
    else:
        s = delta / max_c if max_c != 0.0 else 0.0

        if max_c == r:
            h = 60.0 * (((g - b) / delta) % 6.0)
        elif max_c == g:
            h = 60.0 * (((b - r) / delta) + 2.0)
        else:
            h = 60.0 * (((r - g) / delta) + 4.0)

        if h < 0:
            h += 360.0

    return HSV(h=h, s=s * 100.0, v=v * 100.0, alpha=rgb.alpha)


def hsv_to_rgb(hsv: HSV) -> RGB:
    h = hsv.h % 360.0
    s = hsv.s / 100.0
    v = hsv.v / 100.0

    if s == 0.0:
        r = g = b = v
    else:
        h_i = int(h / 60.0) % 6
        f = (h / 60.0) - h_i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if h_i == 0:
            r, g, b = v, t, p
        elif h_i == 1:
            r, g, b = q, v, p
        elif h_i == 2:
            r, g, b = p, v, t
        elif h_i == 3:
            r, g, b = p, q, v
        elif h_i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

    return RGB(r * 255.0, g * 255.0, b * 255.0, alpha=hsv.alpha)


def hsl_to_hsv(hsl: HSL) -> HSV:
    rgb = hsl_to_rgb(hsl)
    return rgb_to_hsv(rgb)


def hsv_to_hsl(hsv: HSV) -> HSL:
    rgb = hsv_to_rgb(hsv)
    return rgb_to_hsl(rgb)


def rgb_to_hex(rgb: RGB) -> HEX:
    r_i, g_i, b_i = rgb.to_int()
    r_i = int(_clamp(r_i, 0, 255))
    g_i = int(_clamp(g_i, 0, 255))
    b_i = int(_clamp(b_i, 0, 255))

    if rgb.alpha < 1.0:
        a_i = int(round(_clamp(rgb.alpha, 0.0, 1.0) * 255))
        hex_str = f"#{r_i:02x}{g_i:02x}{b_i:02x}{a_i:02x}"
    else:
        hex_str = f"#{r_i:02x}{g_i:02x}{b_i:02x}"

    return HEX(hex_str)


def hex_to_rgb(hex_color: HEX) -> RGB:
    s = hex_color.value[1:]

    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)

    if len(s) == 8:
        a = int(s[6:8], 16) / 255.0
    else:
        a = 1.0

    return RGB(r, g, b, alpha=a)


__all__ = [
    "rgb_to_hsl",
    "hsl_to_rgb",
    "rgb_to_hsv",
    "hsv_to_rgb",
    "hsl_to_hsv",
    "hsv_to_hsl",
    "rgb_to_hex",
    "hex_to_rgb",
]
