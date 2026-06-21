from __future__ import annotations

from typing import Optional

from .models import RGB, _clamp


def alpha_composite(foreground: RGB, background: RGB) -> RGB:
    fa = _clamp(foreground.alpha, 0.0, 1.0)
    ba = _clamp(background.alpha, 0.0, 1.0)

    out_a = fa + ba * (1.0 - fa)

    if out_a == 0.0:
        return RGB(0.0, 0.0, 0.0, alpha=0.0)

    fr = foreground.r_float
    fg = foreground.g_float
    fb = foreground.b_float

    br = background.r_float
    bg = background.g_float
    bb = background.b_float

    out_r = (fr * fa + br * ba * (1.0 - fa)) / out_a
    out_g = (fg * fa + bg * ba * (1.0 - fa)) / out_a
    out_b = (fb * fa + bb * ba * (1.0 - fa)) / out_a

    return RGB.from_float(out_r, out_g, out_b, alpha=out_a)


def alpha_composite_over(foreground: RGB, background: RGB) -> RGB:
    return alpha_composite(foreground, background)


def blend_normal(
    foreground: RGB,
    background: RGB,
    fg_alpha: Optional[float] = None,
) -> RGB:
    if fg_alpha is None:
        alpha = _clamp(foreground.alpha, 0.0, 1.0)
    else:
        alpha = _clamp(fg_alpha, 0.0, 1.0)
    fg = RGB(foreground.r, foreground.g, foreground.b, alpha=alpha)
    return alpha_composite(fg, background)


__all__ = [
    "alpha_composite",
    "alpha_composite_over",
    "blend_normal",
]
