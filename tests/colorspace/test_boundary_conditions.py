import math

import pytest

from solocoder_py.colorspace import (
    HEX,
    HSL,
    HSV,
    RGB,
    alpha_composite_over,
    blend_normal,
    contrast_ratio,
    relative_luminance,
)


def approx_equal(a, b, tol=1e-6):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
    return abs(a - b) < tol


class TestPureBlackWhite:
    def test_pure_black_rgb(self):
        rgb = RGB(0, 0, 0)
        assert rgb.r == 0
        assert rgb.g == 0
        assert rgb.b == 0

    def test_pure_white_rgb(self):
        rgb = RGB(255, 255, 255)
        assert rgb.r == 255
        assert rgb.g == 255
        assert rgb.b == 255

    def test_pure_black_hsl(self):
        rgb = RGB(0, 0, 0)
        hsl = rgb.to_hsl()
        assert approx_equal(hsl.s, 0)
        assert approx_equal(hsl.l, 0)

    def test_pure_white_hsl(self):
        rgb = RGB(255, 255, 255)
        hsl = rgb.to_hsl()
        assert approx_equal(hsl.s, 0)
        assert approx_equal(hsl.l, 100)

    def test_pure_black_hsv(self):
        rgb = RGB(0, 0, 0)
        hsv = rgb.to_hsv()
        assert approx_equal(hsv.s, 0)
        assert approx_equal(hsv.v, 0)

    def test_pure_white_hsv(self):
        rgb = RGB(255, 255, 255)
        hsv = rgb.to_hsv()
        assert approx_equal(hsv.s, 0)
        assert approx_equal(hsv.v, 100)

    def test_pure_black_hex(self):
        assert RGB(0, 0, 0).to_hex().value == "#000000"

    def test_pure_white_hex(self):
        assert RGB(255, 255, 255).to_hex().value == "#ffffff"

    def test_rgb_all_zero(self):
        rgb = RGB(0, 0, 0)
        assert rgb.to_int() == (0, 0, 0)

    def test_rgb_all_255(self):
        rgb = RGB(255, 255, 255)
        assert rgb.to_int() == (255, 255, 255)


class TestGrayHueZero:
    def test_medium_gray_hsl_hue_zero(self):
        hsl = HSL(0, 0, 50)
        rgb = hsl.to_rgb()
        assert approx_equal(rgb.r, rgb.g, tol=1)
        assert approx_equal(rgb.g, rgb.b, tol=1)
        back = rgb.to_hsl()
        assert approx_equal(back.s, 0, tol=1)

    def test_light_gray_hsl(self):
        hsl = HSL(0, 0, 75)
        rgb = hsl.to_rgb()
        assert approx_equal(rgb.r, rgb.g, tol=1)
        assert approx_equal(rgb.g, rgb.b, tol=1)

    def test_dark_gray_hsl(self):
        hsl = HSL(0, 0, 25)
        rgb = hsl.to_rgb()
        assert approx_equal(rgb.r, rgb.g, tol=1)
        assert approx_equal(rgb.g, rgb.b, tol=1)

    def test_gray_hsv_saturation_zero(self):
        hsv = HSV(0, 0, 50)
        rgb = hsv.to_rgb()
        assert approx_equal(rgb.r, rgb.g, tol=1)
        assert approx_equal(rgb.g, rgb.b, tol=1)

    def test_rgb_gray_to_hsl_saturation_zero(self):
        rgb = RGB(128, 128, 128)
        hsl = rgb.to_hsl()
        assert approx_equal(hsl.s, 0, tol=1)


class TestHexCaseInsensitive:
    def test_all_uppercase(self):
        h = HEX("#AABBCC")
        assert h.value == "#aabbcc"

    def test_all_lowercase(self):
        h = HEX("#aabbcc")
        assert h.value == "#aabbcc"

    def test_mixed_case(self):
        h = HEX("#AaBbCc")
        assert h.value == "#abcdef" or h.value == "#aabbcc"

    def test_uppercase_shorthand(self):
        h = HEX("#ABC")
        assert h.value == "#aabbcc"

    def test_lowercase_shorthand(self):
        h = HEX("#abc")
        assert h.value == "#aabbcc"

    def test_mixed_shorthand(self):
        h = HEX("#AbC")
        assert h.value == "#aabbcc"

    def test_hex_with_leading_trailing_whitespace(self):
        h = HEX("  #ff0000  ")
        assert h.value == "#ff0000"


class TestRGBFloatMode:
    def test_rgb_from_float_red(self):
        rgb = RGB.from_float(1.0, 0.0, 0.0)
        assert approx_equal(rgb.r, 255.0)
        assert approx_equal(rgb.g, 0.0)
        assert approx_equal(rgb.b, 0.0)

    def test_rgb_from_float_white(self):
        rgb = RGB.from_float(1.0, 1.0, 1.0)
        assert approx_equal(rgb.r, 255.0)
        assert approx_equal(rgb.g, 255.0)
        assert approx_equal(rgb.b, 255.0)

    def test_rgb_from_float_black(self):
        rgb = RGB.from_float(0.0, 0.0, 0.0)
        assert approx_equal(rgb.r, 0.0)
        assert approx_equal(rgb.g, 0.0)
        assert approx_equal(rgb.b, 0.0)

    def test_rgb_float_properties(self):
        rgb = RGB(128, 64, 192)
        assert approx_equal(rgb.r_float, 128 / 255.0)
        assert approx_equal(rgb.g_float, 64 / 255.0)
        assert approx_equal(rgb.b_float, 192 / 255.0)

    def test_rgb_float_roundtrip(self):
        rgb = RGB.from_float(0.5, 0.25, 0.75)
        assert approx_equal(rgb.r_float, 0.5, tol=0.01)
        assert approx_equal(rgb.g_float, 0.25, tol=0.01)
        assert approx_equal(rgb.b_float, 0.75, tol=0.01)


class TestHueNormalization:
    def test_hue_360_normalized_to_0(self):
        hsl = HSL(360, 100, 50)
        assert approx_equal(hsl.h, 0.0) or approx_equal(hsl.h, 360.0)

    def test_hue_negative_normalized(self):
        hsl = HSL(-30, 100, 50)
        assert approx_equal(hsl.h, 330.0, tol=1)

    def test_hue_720_normalized(self):
        hsl = HSL(720, 100, 50)
        assert approx_equal(hsl.h, 0.0, tol=1) or approx_equal(hsl.h, 360.0, tol=1)

    def test_hue_450_normalized(self):
        hsl = HSL(450, 100, 50)
        assert approx_equal(hsl.h, 90.0, tol=1)

    def test_hsv_hue_normalized(self):
        hsv = HSV(-90, 100, 100)
        assert approx_equal(hsv.h, 270.0, tol=1)


class TestAlphaBoundary:
    def test_alpha_zero(self):
        rgb = RGB(255, 0, 0, alpha=0.0)
        assert approx_equal(rgb.alpha, 0.0)

    def test_alpha_one(self):
        rgb = RGB(255, 0, 0, alpha=1.0)
        assert approx_equal(rgb.alpha, 1.0)

    def test_hsl_alpha_zero(self):
        hsl = HSL(0, 100, 50, alpha=0.0)
        assert approx_equal(hsl.alpha, 0.0)

    def test_hsv_alpha_one(self):
        hsv = HSV(0, 100, 100, alpha=1.0)
        assert approx_equal(hsv.alpha, 1.0)

    def test_alpha_preserved_in_conversion(self):
        rgb = RGB(255, 0, 0, alpha=0.5)
        hsl = rgb.to_hsl()
        assert approx_equal(hsl.alpha, 0.5, tol=0.01)

        hsv = rgb.to_hsv()
        assert approx_equal(hsv.alpha, 0.5, tol=0.01)

        hex_c = rgb.to_hex()
        assert hex_c.has_alpha is True
        back = hex_c.to_rgb()
        assert approx_equal(back.alpha, 0.5, tol=0.05)


class TestHexShorthandExpansion:
    def test_rgb_shorthand_all_primary(self):
        assert HEX("#f00").to_rgb().r == 255
        assert HEX("#f00").to_rgb().g == 0
        assert HEX("#f00").to_rgb().b == 0

    def test_rgb_shorthand_white(self):
        assert HEX("#fff").to_rgb().r == 255
        assert HEX("#fff").to_rgb().g == 255
        assert HEX("#fff").to_rgb().b == 255

    def test_rgb_shorthand_black(self):
        assert HEX("#000").to_rgb().r == 0
        assert HEX("#000").to_rgb().g == 0
        assert HEX("#000").to_rgb().b == 0

    def test_rgba_shorthand_4digit(self):
        h = HEX("#f008")
        assert len(h.value) == 9
        rgb = h.to_rgb()
        assert rgb.r == 255
        assert rgb.g == 0
        assert rgb.b == 0
        assert approx_equal(rgb.alpha, 0x88 / 255.0, tol=0.01)


class TestAlphaCompositeOverBoundary:
    def test_alpha_composite_over_both_opaque(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.alpha, 1.0)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)

    def test_alpha_composite_over_both_transparent(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 255, 0, alpha=0.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.alpha, 0.0)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)

    def test_alpha_composite_over_bg_transparent_fg_opaque(self):
        fg = RGB(255, 100, 50, alpha=1.0)
        bg = RGB(0, 0, 0, alpha=0.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.alpha, 1.0)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 100)
        assert approx_equal(result.b, 50)


class TestBlendNormalBoundary:
    def test_blend_normal_fg_alpha_below_zero_clamped(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 0, 255, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=-0.5)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 255)

    def test_blend_normal_fg_alpha_above_one_clamped(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=2.0)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)

    def test_blend_normal_fg_alpha_zero(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(100, 150, 200, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=0.0)
        assert approx_equal(result.r, 100)
        assert approx_equal(result.g, 150)
        assert approx_equal(result.b, 200)

    def test_blend_normal_fg_alpha_one(self):
        fg = RGB(100, 150, 200, alpha=0.0)
        bg = RGB(255, 255, 255, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=1.0)
        assert approx_equal(result.r, 100)
        assert approx_equal(result.g, 150)
        assert approx_equal(result.b, 200)

    def test_blend_normal_default_with_high_alpha(self):
        fg = RGB(255, 0, 0, alpha=0.95)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        expected = alpha_composite_over(fg, bg)
        assert approx_equal(result.r, expected.r, tol=1)
        assert approx_equal(result.g, expected.g, tol=1)

    def test_blend_normal_default_with_low_alpha(self):
        fg = RGB(255, 0, 0, alpha=0.05)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        expected = alpha_composite_over(fg, bg)
        assert approx_equal(result.r, expected.r, tol=1)
        assert approx_equal(result.g, expected.g, tol=1)
