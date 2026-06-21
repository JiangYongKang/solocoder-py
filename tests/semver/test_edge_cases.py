from __future__ import annotations

import pytest

from solocoder_py.semver import SemverVersion, VersionRange


class TestMajorVersionZero:
    def test_zero_major_comparison(self, parse_version):
        v1 = parse_version("0.1.0")
        v2 = parse_version("0.2.0")
        assert v1 < v2

    def test_zero_major_with_patch(self, parse_version):
        v1 = parse_version("0.0.1")
        v2 = parse_version("0.0.2")
        assert v1 < v2

    def test_zero_major_prerelease(self, parse_version):
        v1 = parse_version("0.1.0-alpha")
        v2 = parse_version("0.1.0")
        assert v1 < v2

    def test_zero_major_vs_one_major(self, parse_version):
        v0 = parse_version("0.9.9")
        v1 = parse_version("1.0.0")
        assert v0 < v1

    def test_zero_major_same_minor_different_patch(self, parse_version):
        v1 = parse_version("0.1.1")
        v2 = parse_version("0.1.2")
        assert v1 < v2

    def test_zero_zero_zero(self, parse_version):
        v = parse_version("0.0.0")
        assert v.major == 0
        assert v.minor == 0
        assert v.patch == 0


class TestPrereleaseNumericIdentifiers:
    def test_numeric_prerelease_comparison(self, parse_version):
        v1 = parse_version("1.0.0-1")
        v2 = parse_version("1.0.0-2")
        assert v1 < v2

    def test_numeric_vs_alpha_prerelease(self, parse_version):
        numeric = parse_version("1.0.0-1")
        alpha = parse_version("1.0.0-alpha")
        assert numeric < alpha

    def test_mixed_numeric_alpha_identifiers(self, parse_version):
        v1 = parse_version("1.0.0-alpha.1")
        v2 = parse_version("1.0.0-alpha.2")
        assert v1 < v2

    def test_numeric_tens_comparison(self, parse_version):
        v1 = parse_version("1.0.0-beta.2")
        v2 = parse_version("1.0.0-beta.11")
        assert v1 < v2

    def test_zero_numeric_prerelease(self, parse_version):
        v = parse_version("1.0.0-0")
        assert v.prerelease == "0"

    def test_numeric_zero_less_than_alpha(self, parse_version):
        v0 = parse_version("1.0.0-0")
        v_alpha = parse_version("1.0.0-alpha")
        assert v0 < v_alpha


class TestSimplifiedFormParsing:
    def test_single_number_parses(self, parse_version):
        v = parse_version("1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0

    def test_single_zero(self, parse_version):
        v = parse_version("0")
        assert v.major == 0
        assert v.minor == 0
        assert v.patch == 0

    def test_single_large_number(self, parse_version):
        v = parse_version("42")
        assert v.major == 42
        assert v.minor == 0
        assert v.patch == 0

    def test_simplified_str_representation(self, parse_version):
        v = parse_version("5")
        assert str(v) == "5.0.0"


class TestLargeVersionNumbers:
    def test_very_large_major(self, parse_version):
        v = parse_version("999999999999.0.0")
        assert v.major == 999999999999

    def test_very_large_all_parts(self, parse_version):
        v = parse_version("1000000000.2000000000.3000000000")
        assert v.major == 1000000000
        assert v.minor == 2000000000
        assert v.patch == 3000000000

    def test_large_version_comparison(self, parse_version):
        v1 = parse_version("1000000000.0.0")
        v2 = parse_version("999999999.999999999.999999999")
        assert v1 > v2

    def test_large_version_equality(self, parse_version):
        v1 = parse_version("999999999999.0.0")
        v2 = parse_version("999999999999.0.0")
        assert v1 == v2

    def test_large_version_in_range(self, parse_version, parse_range):
        v = parse_version("1000000000.0.0")
        r = parse_range(">=999999999.0.0")
        assert r.satisfies(v) is True


class TestReleaseVsPrereleasePriority:
    def test_release_higher_than_prerelease_same_core(self, parse_version):
        release = parse_version("1.0.0")
        prerelease = parse_version("1.0.0-rc.1")
        assert release > prerelease

    def test_release_equal_to_release(self, parse_version):
        v1 = parse_version("1.0.0")
        v2 = parse_version("1.0.0")
        assert v1 == v2

    def test_different_prerelease_tags(self, parse_version):
        alpha = parse_version("1.0.0-alpha")
        beta = parse_version("1.0.0-beta")
        rc = parse_version("1.0.0-rc")
        release = parse_version("1.0.0")
        assert alpha < beta < rc < release

    def test_prerelease_not_equal_to_release(self, parse_version):
        release = parse_version("1.0.0")
        prerelease = parse_version("1.0.0-alpha")
        assert release != prerelease

    def test_hash_consistency_release_vs_prerelease(self, parse_version):
        release = parse_version("1.0.0")
        prerelease = parse_version("1.0.0-alpha")
        assert hash(release) != hash(prerelease)

    def test_hash_consistency_with_build_metadata(self, parse_version):
        v1 = parse_version("1.0.0+build1")
        v2 = parse_version("1.0.0+build2")
        assert hash(v1) == hash(v2)

    def test_version_in_set(self, parse_version):
        v1 = parse_version("1.0.0+build1")
        v2 = parse_version("1.0.0+build2")
        s = {v1, v2}
        assert len(s) == 1
