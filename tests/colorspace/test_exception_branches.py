import math

import pytest

from solocoder_py.colorspace import HEX, HSL, HSV, RGB, InvalidHexError


def approx_equal(a, b, tol=1e-6):
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
    return abs(a - b) < tol


class TestInvalidHexStrings:
    def test_hex_too_short_length_2(self):
        with pytest.raises(InvalidHexError):
            HEX("#ff")

    def test_hex_too_short_length_1(self):
        with pytest.raises(InvalidHexError):
            HEX("#f")

    def test_hex_invalid_length_5(self):
        with pytest.raises(InvalidHexError):
            HEX("#fffff")

    def test_hex_invalid_length_7(self):
        with pytest.raises(InvalidHexError):
            HEX("#fffffff")

    def test_hex_invalid_length_9(self):
        with pytest.raises(InvalidHexError):
            HEX("#fffffffff")

    def test_hex_invalid_character_g(self):
        with pytest.raises(InvalidHexError):
            HEX("#gg0000")

    def test_hex_invalid_character_special(self):
        with pytest.raises(InvalidHexError):
            HEX("#ff00@0")

    def test_hex_no_hash_prefix(self):
        with pytest.raises(InvalidHexError):
            HEX("ff0000")

    def test_hex_empty_string(self):
        with pytest.raises(InvalidHexError):
            HEX("")

    def test_hex_only_hash(self):
        with pytest.raises(InvalidHexError):
            HEX("#")

    def test_hex_non_string_type(self):
        with pytest.raises(InvalidHexError):
            HEX(12345)

    def test_hex_space_invalid(self):
        with pytest.raises(InvalidHexError):
            HEX("#ff 0000")


class TestRGBClipping:
    def test_rgb_r_below_zero_clamped(self):
        rgb = RGB(-10, 128, 128)
        assert approx_equal(rgb.r, 0.0)

    def test_rgb_g_below_zero_clamped(self):
        rgb = RGB(128, -50, 128)
        assert approx_equal(rgb.g, 0.0)

    def test_rgb_b_below_zero_clamped(self):
        rgb = RGB(128, 128, -100)
        assert approx_equal(rgb.b, 0.0)

    def test_rgb_r_above_255_clamped(self):
        rgb = RGB(300, 128, 128)
        assert approx_equal(rgb.r, 255.0)

    def test_rgb_g_above_255_clamped(self):
        rgb = RGB(128, 500, 128)
        assert approx_equal(rgb.g, 255.0)

    def test_rgb_b_above_255_clamped(self):
        rgb = RGB(128, 128, 1000)
        assert approx_equal(rgb.b, 255.0)

    def test_rgb_all_negative(self):
        rgb = RGB(-1, -2, -3)
        assert approx_equal(rgb.r, 0.0)
        assert approx_equal(rgb.g, 0.0)
        assert approx_equal(rgb.b, 0.0)

    def test_rgb_all_above_max(self):
        rgb = RGB(256, 257, 512)
        assert approx_equal(rgb.r, 255.0)
        assert approx_equal(rgb.g, 255.0)
        assert approx_equal(rgb.b, 255.0)

    def test_rgb_float_out_of_range_from_float(self):
        rgb = RGB.from_float(1.5, -0.5, 2.0)
        assert approx_equal(rgb.r, 255.0)
        assert approx_equal(rgb.g, 0.0)
        assert approx_equal(rgb.b, 255.0)


class TestHSLHueNormalizationAndClipping:
    def test_hsl_hue_above_360_normalized(self):
        hsl = HSL(400, 50, 50)
        assert approx_equal(hsl.h, 40.0, tol=1)

    def test_hsl_hue_below_zero_normalized(self):
        hsl = HSL(-60, 50, 50)
        assert approx_equal(hsl.h, 300.0, tol=1)

    def test_hsl_saturation_below_zero_clamped(self):
        hsl = HSL(120, -10, 50)
        assert approx_equal(hsl.s, 0.0)

    def test_hsl_saturation_above_100_clamped(self):
        hsl = HSL(120, 150, 50)
        assert approx_equal(hsl.s, 100.0)

    def test_hsl_lightness_below_zero_clamped(self):
        hsl = HSL(120, 50, -20)
        assert approx_equal(hsl.l, 0.0)

    def test_hsl_lightness_above_100_clamped(self):
        hsl = HSL(120, 50, 200)
        assert approx_equal(hsl.l, 100.0)


class TestHSVHueNormalizationAndClipping:
    def test_hsv_hue_above_360_normalized(self):
        hsv = HSV(540, 50, 50)
        assert approx_equal(hsv.h, 180.0, tol=1)

    def test_hsv_hue_below_zero_normalized(self):
        hsv = HSV(-180, 50, 50)
        assert approx_equal(hsv.h, 180.0, tol=1)

    def test_hsv_saturation_below_zero_clamped(self):
        hsv = HSV(120, -10, 50)
        assert approx_equal(hsv.s, 0.0)

    def test_hsv_saturation_above_100_clamped(self):
        hsv = HSV(120, 150, 50)
        assert approx_equal(hsv.s, 100.0)

    def test_hsv_value_below_zero_clamped(self):
        hsv = HSV(120, 50, -20)
        assert approx_equal(hsv.v, 0.0)

    def test_hsv_value_above_100_clamped(self):
        hsv = HSV(120, 50, 200)
        assert approx_equal(hsv.v, 100.0)


class TestAlphaClipping:
    def test_alpha_below_zero_clamped_rgb(self):
        rgb = RGB(255, 0, 0, alpha=-0.5)
        assert approx_equal(rgb.alpha, 0.0)

    def test_alpha_above_one_clamped_rgb(self):
        rgb = RGB(255, 0, 0, alpha=1.5)
        assert approx_equal(rgb.alpha, 1.0)

    def test_alpha_below_zero_clamped_hsl(self):
        hsl = HSL(0, 100, 50, alpha=-0.1)
        assert approx_equal(hsl.alpha, 0.0)

    def test_alpha_above_one_clamped_hsl(self):
        hsl = HSL(0, 100, 50, alpha=2.0)
        assert approx_equal(hsl.alpha, 1.0)

    def test_alpha_below_zero_clamped_hsv(self):
        hsv = HSV(0, 100, 100, alpha=-1.0)
        assert approx_equal(hsv.alpha, 0.0)

    def test_alpha_above_one_clamped_hsv(self):
        hsv = HSV(0, 100, 100, alpha=3.0)
        assert approx_equal(hsv.alpha, 1.0)


class TestNaNHandling:
    def test_rgb_nan_clamped_to_zero(self):
        rgb = RGB(float("nan"), 128, 128)
        assert approx_equal(rgb.r, 0.0)

    def test_hsl_nan_hue_clamped_to_zero(self):
        hsl = HSL(float("nan"), 50, 50)
        assert approx_equal(hsl.h, 0.0)

    def test_hsl_nan_saturation_clamped_to_zero(self):
        hsl = HSL(120, float("nan"), 50)
        assert approx_equal(hsl.s, 0.0)

    def test_hsv_nan_value_clamped_to_zero(self):
        hsv = HSV(120, 50, float("nan"))
        assert approx_equal(hsv.v, 0.0)

    def test_alpha_nan_clamped_to_zero(self):
        rgb = RGB(255, 0, 0, alpha=float("nan"))
        assert approx_equal(rgb.alpha, 0.0)


class TestConversionClamping:
    def test_rgb_hsl_rgb_roundtrip_with_clamping(self):
        rgb = RGB(255.5, -0.5, 300)
        hsl = rgb.to_hsl()
        back = hsl.to_rgb()
        assert 0 <= back.r <= 255
        assert 0 <= back.g <= 255
        assert 0 <= back.b <= 255

    def test_rgb_hsv_rgb_roundtrip_with_clamping(self):
        rgb = RGB(500, -100, 255.1)
        hsv = rgb.to_hsv()
        back = hsv.to_rgb()
        assert 0 <= back.r <= 255
        assert 0 <= back.g <= 255
        assert 0 <= back.b <= 255

    def test_rgb_hex_roundtrip_with_clamping(self):
        rgb = RGB(300, -10, 256)
        hex_c = rgb.to_hex()
        back = hex_c.to_rgb()
        assert 0 <= back.r <= 255
        assert 0 <= back.g <= 255
        assert 0 <= back.b <= 255
