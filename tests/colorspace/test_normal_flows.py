import math

import pytest

from solocoder_py.colorspace import (
    HEX,
    HSL,
    HSV,
    RGB,
    alpha_composite,
    alpha_composite_over,
    blend_normal,
    check_contrast,
    contrast_ratio,
    meets_aa,
    meets_aaa,
    relative_luminance,
)


def approx_equal(a, b, tol=1e-6):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
    return abs(a - b) < tol


def approx_color_equal(c1, c2, tol=1):
    return (
        approx_equal(c1.r, c2.r, tol=tol)
        and approx_equal(c1.g, c2.g, tol=tol)
        and approx_equal(c1.b, c2.b, tol=tol)
    )


class TestRGBHexConversion:
    def test_rgb_to_hex_red(self):
        rgb = RGB(255, 0, 0)
        assert rgb.to_hex().value == "#ff0000"

    def test_rgb_to_hex_green(self):
        rgb = RGB(0, 255, 0)
        assert rgb.to_hex().value == "#00ff00"

    def test_rgb_to_hex_blue(self):
        rgb = RGB(0, 0, 255)
        assert rgb.to_hex().value == "#0000ff"

    def test_rgb_to_hex_white(self):
        rgb = RGB(255, 255, 255)
        assert rgb.to_hex().value == "#ffffff"

    def test_rgb_to_hex_black(self):
        rgb = RGB(0, 0, 0)
        assert rgb.to_hex().value == "#000000"

    def test_rgb_to_hex_gray(self):
        rgb = RGB(128, 128, 128)
        assert rgb.to_hex().value == "#808080"

    def test_hex_to_rgb_red(self):
        hex_c = HEX("#ff0000")
        rgb = hex_c.to_rgb()
        assert rgb.r == 255
        assert rgb.g == 0
        assert rgb.b == 0

    def test_hex_to_rgb_green(self):
        hex_c = HEX("#00ff00")
        rgb = hex_c.to_rgb()
        assert rgb.r == 0
        assert rgb.g == 255
        assert rgb.b == 0

    def test_hex_to_rgb_blue(self):
        hex_c = HEX("#0000ff")
        rgb = hex_c.to_rgb()
        assert rgb.r == 0
        assert rgb.g == 0
        assert rgb.b == 255

    def test_hex_to_rgb_white(self):
        hex_c = HEX("#ffffff")
        rgb = hex_c.to_rgb()
        assert rgb.r == 255
        assert rgb.g == 255
        assert rgb.b == 255

    def test_hex_to_rgb_black(self):
        hex_c = HEX("#000000")
        rgb = hex_c.to_rgb()
        assert rgb.r == 0
        assert rgb.g == 0
        assert rgb.b == 0

    def test_hex_shorthand_3_digit_expand(self):
        assert HEX("#f00").value == "#ff0000"
        assert HEX("#0f0").value == "#00ff00"
        assert HEX("#00f").value == "#0000ff"
        assert HEX("#fff").value == "#ffffff"
        assert HEX("#000").value == "#000000"
        assert HEX("#abc").value == "#aabbcc"

    def test_hex_shorthand_3_digit_rgb_values(self):
        hex_c = HEX("#f00")
        rgb = hex_c.to_rgb()
        assert rgb.r == 255
        assert rgb.g == 0
        assert rgb.b == 0

    def test_hex_with_alpha_8_digit(self):
        hex_c = HEX("#ff000080")
        rgb = hex_c.to_rgb()
        assert rgb.r == 255
        assert rgb.g == 0
        assert rgb.b == 0
        assert approx_equal(rgb.alpha, 128 / 255, tol=1e-3)

    def test_rgb_to_hex_with_alpha(self):
        rgb = RGB(255, 0, 0, alpha=0.5)
        hex_c = rgb.to_hex()
        assert len(hex_c.value) == 9
        assert hex_c.value.startswith("#ff0000")

    def test_rgb_hex_roundtrip_various_colors(self):
        colors = [
            RGB(255, 0, 0),
            RGB(0, 255, 0),
            RGB(0, 0, 255),
            RGB(255, 255, 255),
            RGB(0, 0, 0),
            RGB(128, 128, 128),
            RGB(255, 128, 0),
            RGB(100, 150, 200),
            RGB(13, 57, 99),
        ]
        for rgb in colors:
            roundtrip = rgb.to_hex().to_rgb()
            assert roundtrip.r == rgb.r
            assert roundtrip.g == rgb.g
            assert roundtrip.b == rgb.b


class TestRGBHSLRoundTrip:
    def test_rgb_hsl_roundtrip_red(self):
        rgb = RGB(255, 0, 0)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsl_roundtrip_green(self):
        rgb = RGB(0, 255, 0)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsl_roundtrip_blue(self):
        rgb = RGB(0, 0, 255)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsl_roundtrip_white(self):
        rgb = RGB(255, 255, 255)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsl_roundtrip_black(self):
        rgb = RGB(0, 0, 0)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsl_roundtrip_gray(self):
        rgb = RGB(128, 128, 128)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert approx_color_equal(rgb, back, tol=2)

    def test_rgb_hsl_roundtrip_various(self):
        colors = [
            RGB(255, 128, 0),
            RGB(100, 150, 200),
            RGB(13, 57, 99),
            RGB(200, 50, 150),
            RGB(50, 200, 150),
            RGB(128, 64, 192),
        ]
        for rgb in colors:
            hsl = rgb.to_hsl()
            back = hsl.to_rgb()
            assert approx_color_equal(rgb, back, tol=2)

    def test_hsl_rgb_hsl_roundtrip(self):
        hsl_colors = [
            HSL(0, 100, 50),
            HSL(120, 100, 50),
            HSL(240, 100, 50),
            HSL(60, 100, 50),
            HSL(180, 100, 50),
            HSL(300, 100, 50),
            HSL(0, 0, 50),
            HSL(45, 75, 60),
        ]
        for hsl in hsl_colors:
            rgb = hsl.to_rgb()
            back = rgb.to_hsl()
            assert approx_equal(back.h, hsl.h, tol=2)
            assert approx_equal(back.s, hsl.s, tol=2)
            assert approx_equal(back.l, hsl.l, tol=2)


class TestRGBHSVRoundTrip:
    def test_rgb_hsv_roundtrip_red(self):
        rgb = RGB(255, 0, 0)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsv_roundtrip_green(self):
        rgb = RGB(0, 255, 0)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsv_roundtrip_blue(self):
        rgb = RGB(0, 0, 255)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsv_roundtrip_white(self):
        rgb = RGB(255, 255, 255)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsv_roundtrip_black(self):
        rgb = RGB(0, 0, 0)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert approx_color_equal(rgb, back)

    def test_rgb_hsv_roundtrip_various(self):
        colors = [
            RGB(255, 128, 0),
            RGB(100, 150, 200),
            RGB(13, 57, 99),
            RGB(200, 50, 150),
            RGB(50, 200, 150),
            RGB(128, 64, 192),
        ]
        for rgb in colors:
            hsv = rgb.to_hsv()
            back = hsv.to_rgb()
            assert approx_color_equal(rgb, back, tol=2)


class TestHSLHSVConversion:
    def test_hsl_to_hsv_red(self):
        hsl = HSL(0, 100, 50)
        hsv = hsl.to_hsv()
        assert approx_equal(hsv.h, 0, tol=1)
        assert approx_equal(hsv.s, 100, tol=1)
        assert approx_equal(hsv.v, 100, tol=1)

    def test_hsl_to_hsv_white(self):
        hsl = HSL(0, 0, 100)
        hsv = hsl.to_hsv()
        assert approx_equal(hsv.s, 0, tol=1)
        assert approx_equal(hsv.v, 100, tol=1)

    def test_hsl_to_hsv_gray(self):
        hsl = HSL(0, 0, 50)
        hsv = hsl.to_hsv()
        assert approx_equal(hsv.s, 0, tol=1)
        assert approx_equal(hsv.v, 50, tol=1)

    def test_hsv_to_hsl_red(self):
        hsv = HSV(0, 100, 100)
        hsl = hsv.to_hsl()
        assert approx_equal(hsl.h, 0, tol=1)
        assert approx_equal(hsl.s, 100, tol=1)
        assert approx_equal(hsl.l, 50, tol=1)

    def test_hsl_hsv_roundtrip(self):
        colors = [
            HSL(0, 100, 50),
            HSL(120, 80, 40),
            HSL(240, 60, 70),
            HSL(60, 90, 30),
        ]
        for hsl in colors:
            hsv = hsl.to_hsv()
            back = hsv.to_hsl()
            assert approx_equal(back.h, hsl.h, tol=2)
            assert approx_equal(back.s, hsl.s, tol=2)
            assert approx_equal(back.l, hsl.l, tol=2)


class TestAlphaCompositing:
    def test_semitransparent_white_over_black(self):
        fg = RGB(255, 255, 255, alpha=0.5)
        bg = RGB(0, 0, 0, alpha=1.0)
        result = alpha_composite(fg, bg)
        assert approx_equal(result.r, 127.5, tol=1)
        assert approx_equal(result.g, 127.5, tol=1)
        assert approx_equal(result.b, 127.5, tol=1)
        assert approx_equal(result.alpha, 1.0)

    def test_opaque_foreground_covers_background(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = alpha_composite(fg, bg)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)

    def test_fully_transparent_foreground(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = alpha_composite(fg, bg)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 255)
        assert approx_equal(result.b, 0)

    def test_both_with_alpha(self):
        fg = RGB(255, 0, 0, alpha=0.5)
        bg = RGB(0, 0, 255, alpha=0.5)
        result = alpha_composite(fg, bg)
        expected_alpha = 0.5 + 0.5 * (1 - 0.5)
        assert approx_equal(result.alpha, expected_alpha)
        expected_r = (255 * 0.5 + 0 * 0.5 * 0.5) / expected_alpha
        expected_b = (0 * 0.5 + 255 * 0.5 * 0.5) / expected_alpha
        assert approx_equal(result.r, expected_r, tol=1)
        assert approx_equal(result.b, expected_b, tol=1)


class TestWCAGContrast:
    def test_black_white_max_contrast(self):
        black = RGB(0, 0, 0)
        white = RGB(255, 255, 255)
        ratio = contrast_ratio(black, white)
        assert approx_equal(ratio, 21.0, tol=0.01)

    def test_white_white_min_contrast(self):
        white = RGB(255, 255, 255)
        ratio = contrast_ratio(white, white)
        assert approx_equal(ratio, 1.0, tol=0.01)

    def test_black_black_min_contrast(self):
        black = RGB(0, 0, 0)
        ratio = contrast_ratio(black, black)
        assert approx_equal(ratio, 1.0, tol=0.01)

    def test_relative_luminance_white(self):
        white = RGB(255, 255, 255)
        assert approx_equal(relative_luminance(white), 1.0, tol=0.01)

    def test_relative_luminance_black(self):
        black = RGB(0, 0, 0)
        assert approx_equal(relative_luminance(black), 0.0, tol=0.01)

    def test_meets_aa_black_on_white(self):
        black = RGB(0, 0, 0)
        white = RGB(255, 255, 255)
        assert meets_aa(black, white) is True

    def test_meets_aaa_black_on_white(self):
        black = RGB(0, 0, 0)
        white = RGB(255, 255, 255)
        assert meets_aaa(black, white) is True

    def test_meets_aa_white_on_white(self):
        white = RGB(255, 255, 255)
        assert meets_aa(white, white) is False

    def test_meets_aaa_white_on_white(self):
        white = RGB(255, 255, 255)
        assert meets_aaa(white, white) is False

    def test_check_contrast_result_black_white(self):
        black = RGB(0, 0, 0)
        white = RGB(255, 255, 255)
        result = check_contrast(black, white)
        assert result.aa_normal is True
        assert result.aa_large is True
        assert result.aaa_normal is True
        assert result.aaa_large is True
        assert approx_equal(result.ratio, 21.0, tol=0.01)

    def test_check_contrast_result_white_white(self):
        white = RGB(255, 255, 255)
        result = check_contrast(white, white)
        assert result.aa_normal is False
        assert result.aa_large is False
        assert result.aaa_normal is False
        assert result.aaa_large is False
        assert approx_equal(result.ratio, 1.0, tol=0.01)

    def test_hex_case_insensitive(self):
        h1 = HEX("#FF0000")
        h2 = HEX("#ff0000")
        assert h1.value == h2.value
        assert h1.value == "#ff0000"

    def test_hex_mixed_case(self):
        h = HEX("#AbCdEf")
        assert h.value == "#abcdef"


class TestAlphaCompositeOver:
    def test_alpha_composite_over_equals_alpha_composite(self):
        fg = RGB(255, 128, 64, alpha=0.7)
        bg = RGB(32, 64, 128, alpha=1.0)
        r1 = alpha_composite(fg, bg)
        r2 = alpha_composite_over(fg, bg)
        assert approx_equal(r1.r, r2.r)
        assert approx_equal(r1.g, r2.g)
        assert approx_equal(r1.b, r2.b)
        assert approx_equal(r1.alpha, r2.alpha)

    def test_alpha_composite_over_red_on_green(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)
        assert approx_equal(result.alpha, 1.0)

    def test_alpha_composite_over_semitransparent_white_black(self):
        fg = RGB(255, 255, 255, alpha=0.5)
        bg = RGB(0, 0, 0, alpha=1.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.r, 127.5, tol=1)
        assert approx_equal(result.g, 127.5, tol=1)
        assert approx_equal(result.b, 127.5, tol=1)

    def test_alpha_composite_over_transparent_foreground(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 0, 255, alpha=1.0)
        result = alpha_composite_over(fg, bg)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 255)

    def test_alpha_composite_over_both_semitransparent(self):
        fg = RGB(255, 0, 0, alpha=0.5)
        bg = RGB(0, 0, 255, alpha=0.5)
        result = alpha_composite_over(fg, bg)
        expected_alpha = 0.5 + 0.5 * (1 - 0.5)
        assert approx_equal(result.alpha, expected_alpha)


class TestBlendNormal:
    def test_blend_normal_default_uses_foreground_alpha(self):
        fg = RGB(255, 255, 255, alpha=0.5)
        bg = RGB(0, 0, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        expected = alpha_composite(fg, bg)
        assert approx_equal(result.r, expected.r, tol=1)
        assert approx_equal(result.g, expected.g, tol=1)
        assert approx_equal(result.b, expected.b, tol=1)
        assert approx_equal(result.alpha, expected.alpha)

    def test_blend_normal_default_half_transparent(self):
        fg = RGB(255, 255, 255, alpha=0.5)
        bg = RGB(0, 0, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        assert approx_equal(result.r, 127.5, tol=1)
        assert approx_equal(result.g, 127.5, tol=1)
        assert approx_equal(result.b, 127.5, tol=1)

    def test_blend_normal_default_fully_transparent(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 255)
        assert approx_equal(result.b, 0)

    def test_blend_normal_default_opaque(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)

    def test_blend_normal_explicit_fg_alpha_override(self):
        fg = RGB(255, 255, 255, alpha=1.0)
        bg = RGB(0, 0, 0, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=0.5)
        assert approx_equal(result.r, 127.5, tol=1)
        assert approx_equal(result.g, 127.5, tol=1)
        assert approx_equal(result.b, 127.5, tol=1)

    def test_blend_normal_explicit_fg_alpha_zero(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 0, 255, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=0.0)
        assert approx_equal(result.r, 0)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 255)

    def test_blend_normal_explicit_fg_alpha_one(self):
        fg = RGB(255, 0, 0, alpha=0.0)
        bg = RGB(0, 255, 0, alpha=1.0)
        result = blend_normal(fg, bg, fg_alpha=1.0)
        assert approx_equal(result.r, 255)
        assert approx_equal(result.g, 0)
        assert approx_equal(result.b, 0)

    def test_blend_normal_fg_alpha_half(self):
        fg = RGB(255, 0, 0, alpha=1.0)
        bg = RGB(0, 0, 255, alpha=0.5)
        result = blend_normal(fg, bg, fg_alpha=0.5)
        expected_alpha = 0.5 + 0.5 * (1 - 0.5)
        assert approx_equal(result.alpha, expected_alpha)
        expected_r = (1.0 * 0.5 + 0 * 0.5 * 0.5) / expected_alpha
        expected_b = (0 * 0.5 + 1.0 * 0.5 * 0.5) / expected_alpha
        assert approx_equal(result.r, expected_r * 255, tol=1)
        assert approx_equal(result.b, expected_b * 255, tol=1)

    def test_blend_normal_consistent_with_alpha_composite_when_default(self):
        cases = [
            (RGB(255, 0, 0, alpha=0.3), RGB(0, 255, 0, alpha=1.0)),
            (RGB(100, 150, 200, alpha=0.7), RGB(50, 50, 50, alpha=0.8)),
            (RGB(0, 0, 0, alpha=1.0), RGB(255, 255, 255, alpha=1.0)),
        ]
        for fg, bg in cases:
            r1 = blend_normal(fg, bg)
            r2 = alpha_composite(fg, bg)
            assert approx_equal(r1.r, r2.r, tol=1)
            assert approx_equal(r1.g, r2.g, tol=1)
            assert approx_equal(r1.b, r2.b, tol=1)
            assert approx_equal(r1.alpha, r2.alpha, tol=1e-6)
