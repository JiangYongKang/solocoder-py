from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .models import RGB


class WCAGLevel(str, Enum):
    AA = "AA"
    AAA = "AAA"


class WCAGTextSize(str, Enum):
    NORMAL = "normal"
    LARGE = "large"


WCAG_AA_NORMAL = 4.5
WCAG_AA_LARGE = 3.0
WCAG_AAA_NORMAL = 7.0
WCAG_AAA_LARGE = 4.5


def _linearize_channel(c: float) -> float:
    c_srgb = c / 255.0
    if c_srgb <= 0.04045:
        return c_srgb / 12.92
    return ((c_srgb + 0.055) / 1.055) ** 2.4


def relative_luminance(color: RGB) -> float:
    r_lin = _linearize_channel(color.r)
    g_lin = _linearize_channel(color.g)
    b_lin = _linearize_channel(color.b)
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1: RGB, color2: RGB) -> float:
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)

    lighter = max(l1, l2)
    darker = min(l1, l2)

    if darker == 0.0 and lighter == 0.0:
        return 1.0

    if darker == 0.0:
        return (lighter + 0.05) / 0.05

    return (lighter + 0.05) / (darker + 0.05)


@dataclass(frozen=True)
class ContrastResult:
    ratio: float
    aa_normal: bool
    aa_large: bool
    aaa_normal: bool
    aaa_large: bool

    @property
    def passes(self) -> dict[str, bool]:
        return {
            "AA_normal": self.aa_normal,
            "AA_large": self.aa_large,
            "AAA_normal": self.aaa_normal,
            "AAA_large": self.aaa_large,
        }

    def meets(self, level: WCAGLevel, size: WCAGTextSize = WCAGTextSize.NORMAL) -> bool:
        if level == WCAGLevel.AA:
            return self.aa_normal if size == WCAGTextSize.NORMAL else self.aa_large
        return self.aaa_normal if size == WCAGTextSize.NORMAL else self.aaa_large


def check_contrast(fg: RGB, bg: RGB) -> ContrastResult:
    ratio = contrast_ratio(fg, bg)
    return ContrastResult(
        ratio=ratio,
        aa_normal=ratio >= WCAG_AA_NORMAL,
        aa_large=ratio >= WCAG_AA_LARGE,
        aaa_normal=ratio >= WCAG_AAA_NORMAL,
        aaa_large=ratio >= WCAG_AAA_LARGE,
    )


def meets_aa(fg: RGB, bg: RGB, size: WCAGTextSize = WCAGTextSize.NORMAL) -> bool:
    ratio = contrast_ratio(fg, bg)
    threshold = WCAG_AA_NORMAL if size == WCAGTextSize.NORMAL else WCAG_AA_LARGE
    return ratio >= threshold


def meets_aaa(fg: RGB, bg: RGB, size: WCAGTextSize = WCAGTextSize.NORMAL) -> bool:
    ratio = contrast_ratio(fg, bg)
    threshold = WCAG_AAA_NORMAL if size == WCAGTextSize.NORMAL else WCAG_AAA_LARGE
    return ratio >= threshold


__all__ = [
    "WCAGLevel",
    "WCAGTextSize",
    "WCAG_AA_NORMAL",
    "WCAG_AA_LARGE",
    "WCAG_AAA_NORMAL",
    "WCAG_AAA_LARGE",
    "relative_luminance",
    "contrast_ratio",
    "ContrastResult",
    "check_contrast",
    "meets_aa",
    "meets_aaa",
]
