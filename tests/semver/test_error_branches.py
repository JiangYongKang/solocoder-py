from __future__ import annotations

import pytest

from solocoder_py.semver import SemverVersion, VersionRange, InvalidVersionError, InvalidRangeError


class TestIllegalVersionStrings:
    def test_non_numeric_parts(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("a.b.c")

    def test_missing_patch(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.2")

    def test_empty_string(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("")

    def test_only_dots(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("...")

    def test_leading_zero_major(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("01.0.0")

    def test_leading_zero_minor(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.01.0")

    def test_leading_zero_patch(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.0.01")

    def test_negative_version(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("-1.0.0")

    def test_special_characters(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.2.3!")

    def test_two_parts_only(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.2")

    def test_four_parts(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.2.3.4")

    def test_non_string_input(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version(123)


class TestPrereleaseLeadingZeros:
    def test_leading_zero_in_prerelease_numeric(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.0.0-01")

    def test_leading_zero_in_dotted_prerelease(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.0.0-alpha.01")

    def test_zero_itself_is_valid(self, parse_version):
        v = parse_version("1.0.0-0")
        assert v.prerelease == "0"

    def test_single_digit_numeric_prerelease(self, parse_version):
        v = parse_version("1.0.0-1")
        assert v.prerelease == "1"

    def test_multi_digit_no_leading_zero(self, parse_version):
        v = parse_version("1.0.0-10")
        assert v.prerelease == "10"


class TestBuildMetadataWithSpaces:
    def test_space_in_build_metadata(self, parse_version):
        with pytest.raises(InvalidVersionError):
            parse_version("1.0.0+build meta")

    def test_valid_build_metadata(self, parse_version):
        v = parse_version("1.0.0+build-1")
        assert v.build_metadata == "build-1"

    def test_build_metadata_with_dots(self, parse_version):
        v = parse_version("1.0.0+build.123")
        assert v.build_metadata == "build.123"

    def test_build_metadata_with_leading_zeros(self, parse_version):
        v = parse_version("1.0.0+001")
        assert v.build_metadata == "001"


class TestInvalidRangeOperators:
    def test_tilde_operator(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("~1.2.3")

    def test_caret_operator(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("^1.2.3")

    def test_double_equals(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("==1.2.3")

    def test_no_operator(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("1.2.3")

    def test_exclamation_operator(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("!1.2.3")

    def test_empty_range(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range("")

    def test_non_string_range(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range(123)

    def test_invalid_version_in_range(self, parse_range):
        with pytest.raises(InvalidRangeError):
            parse_range(">=abc")


class TestNegativeVersionNumbers:
    def test_negative_major_in_constructor(self):
        with pytest.raises(InvalidVersionError):
            SemverVersion(-1, 0, 0)

    def test_negative_minor_in_constructor(self):
        with pytest.raises(InvalidVersionError):
            SemverVersion(1, -1, 0)

    def test_negative_patch_in_constructor(self):
        with pytest.raises(InvalidVersionError):
            SemverVersion(1, 0, -1)

    def test_all_negative_in_constructor(self):
        with pytest.raises(InvalidVersionError):
            SemverVersion(-1, -1, -1)

    def test_non_integer_in_constructor(self):
        with pytest.raises(InvalidVersionError):
            SemverVersion(1.5, 0, 0)
