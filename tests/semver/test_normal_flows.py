from __future__ import annotations

import pytest

from solocoder_py.semver import SemverVersion, VersionRange


class TestStandardThreePartParsing:
    def test_basic_version(self, parse_version):
        v = parse_version("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build_metadata is None

    def test_zero_version(self, parse_version):
        v = parse_version("0.0.0")
        assert v.major == 0
        assert v.minor == 0
        assert v.patch == 0

    def test_large_version_numbers(self, parse_version):
        v = parse_version("100.200.300")
        assert v.major == 100
        assert v.minor == 200
        assert v.patch == 300

    def test_str_representation(self, parse_version):
        assert str(parse_version("1.2.3")) == "1.2.3"

    def test_repr_representation(self, parse_version):
        v = parse_version("1.2.3")
        assert repr(v) == "SemverVersion.parse('1.2.3')"


class TestPrereleaseVersionParsing:
    def test_version_with_prerelease(self, parse_version):
        v = parse_version("1.2.3-alpha")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease == "alpha"

    def test_version_with_dotted_prerelease(self, parse_version):
        v = parse_version("1.2.3-alpha.1")
        assert v.prerelease == "alpha.1"

    def test_version_with_numeric_prerelease(self, parse_version):
        v = parse_version("1.2.3-0")
        assert v.prerelease == "0"

    def test_version_with_mixed_prerelease(self, parse_version):
        v = parse_version("1.2.3-alpha.1.beta.2")
        assert v.prerelease == "alpha.1.beta.2"

    def test_prerelease_with_hyphen(self, parse_version):
        v = parse_version("1.2.3-alpha-1")
        assert v.prerelease == "alpha-1"

    def test_str_with_prerelease(self, parse_version):
        assert str(parse_version("1.2.3-alpha")) == "1.2.3-alpha"

    def test_str_with_dotted_prerelease(self, parse_version):
        assert str(parse_version("1.2.3-alpha.1")) == "1.2.3-alpha.1"


class TestBuildMetadataParsing:
    def test_version_with_build_metadata(self, parse_version):
        v = parse_version("1.2.3+build")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.build_metadata == "build"
        assert v.prerelease is None

    def test_version_with_dotted_build_metadata(self, parse_version):
        v = parse_version("1.2.3+build.123")
        assert v.build_metadata == "build.123"

    def test_version_with_prerelease_and_build(self, parse_version):
        v = parse_version("1.2.3-alpha+build.1")
        assert v.prerelease == "alpha"
        assert v.build_metadata == "build.1"

    def test_str_with_build_metadata(self, parse_version):
        assert str(parse_version("1.2.3+build")) == "1.2.3+build"

    def test_str_with_prerelease_and_build(self, parse_version):
        assert str(parse_version("1.2.3-alpha+build")) == "1.2.3-alpha+build"


class TestPrereleasePriorityComparison:
    def test_release_greater_than_prerelease(self, parse_version):
        release = parse_version("1.0.0")
        prerelease = parse_version("1.0.0-alpha")
        assert release > prerelease
        assert prerelease < release

    def test_prerelease_alphabetic_order(self, parse_version):
        alpha = parse_version("1.0.0-alpha")
        beta = parse_version("1.0.0-beta")
        assert alpha < beta
        assert beta > alpha

    def test_prerelease_numeric_order(self, parse_version):
        v1 = parse_version("1.0.0-alpha.1")
        v2 = parse_version("1.0.0-alpha.2")
        assert v1 < v2

    def test_prerelease_numeric_less_than_alpha(self, parse_version):
        numeric = parse_version("1.0.0-1")
        alpha = parse_version("1.0.0-alpha")
        assert numeric < alpha
        assert alpha > numeric

    def test_prerelease_shorter_is_less(self, parse_version):
        short = parse_version("1.0.0-alpha")
        long = parse_version("1.0.0-alpha.1")
        assert short < long

    def test_full_precedence_chain(self, parse_version):
        versions = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ]
        parsed = [parse_version(v) for v in versions]
        for i in range(len(parsed) - 1):
            assert parsed[i] < parsed[i + 1], f"Expected {versions[i]} < {versions[i + 1]}"

    def test_major_takes_precedence_over_prerelease(self, parse_version):
        v1 = parse_version("2.0.0-alpha")
        v2 = parse_version("1.0.0")
        assert v1 > v2


class TestBuildMetadataEquality:
    def test_different_build_metadata_are_equal(self, parse_version):
        v1 = parse_version("1.0.0+build1")
        v2 = parse_version("1.0.0+build2")
        assert v1 == v2

    def test_build_vs_no_build_are_equal(self, parse_version):
        v1 = parse_version("1.0.0")
        v2 = parse_version("1.0.0+build")
        assert v1 == v2

    def test_build_metadata_does_not_affect_ordering(self, parse_version):
        v1 = parse_version("1.0.0+aaa")
        v2 = parse_version("1.0.0+zzz")
        assert not (v1 < v2)
        assert not (v1 > v2)
        assert v1 == v2

    def test_without_build_metadata(self, parse_version):
        v = parse_version("1.2.3-alpha+build.1")
        assert v.without_build_metadata() == "1.2.3-alpha"

    def test_without_build_metadata_no_prerelease(self, parse_version):
        v = parse_version("1.2.3+build.1")
        assert v.without_build_metadata() == "1.2.3"

    def test_without_build_metadata_neither(self, parse_version):
        v = parse_version("1.2.3")
        assert v.without_build_metadata() == "1.2.3"

    def test_prerelease_with_different_build_equal(self, parse_version):
        v1 = parse_version("1.0.0-alpha+build1")
        v2 = parse_version("1.0.0-alpha+build2")
        assert v1 == v2


class TestExactMatchRange:
    def test_exact_match_satisfied(self, parse_version, parse_range):
        r = parse_range("=1.2.3")
        assert r.satisfies(parse_version("1.2.3")) is True

    def test_exact_match_not_satisfied(self, parse_version, parse_range):
        r = parse_range("=1.2.3")
        assert r.satisfies(parse_version("1.2.4")) is False

    def test_exact_match_different_major(self, parse_version, parse_range):
        r = parse_range("=1.2.3")
        assert r.satisfies(parse_version("2.0.0")) is False

    def test_exact_match_ignores_build_metadata(self, parse_version, parse_range):
        r = parse_range("=1.2.3")
        assert r.satisfies(parse_version("1.2.3+build")) is True


class TestIntervalRange:
    def test_version_in_interval(self, parse_version, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert r.satisfies(parse_version("1.5.0")) is True

    def test_version_at_lower_bound(self, parse_version, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert r.satisfies(parse_version("1.2.3")) is True

    def test_version_at_upper_bound(self, parse_version, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert r.satisfies(parse_version("2.0.0")) is False

    def test_version_below_lower_bound(self, parse_version, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert r.satisfies(parse_version("1.2.2")) is False

    def test_version_above_upper_bound(self, parse_version, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert r.satisfies(parse_version("2.0.1")) is False


class TestMultiConditionRange:
    def test_greater_than_and_less_than(self, parse_version, parse_range):
        r = parse_range(">1.0.0 <2.0.0")
        assert r.satisfies(parse_version("1.5.0")) is True
        assert r.satisfies(parse_version("1.0.0")) is False
        assert r.satisfies(parse_version("2.0.0")) is False

    def test_greater_equal_and_less_equal(self, parse_version, parse_range):
        r = parse_range(">=1.0.0 <=2.0.0")
        assert r.satisfies(parse_version("1.0.0")) is True
        assert r.satisfies(parse_version("2.0.0")) is True
        assert r.satisfies(parse_version("1.5.0")) is True
        assert r.satisfies(parse_version("0.9.0")) is False
        assert r.satisfies(parse_version("2.1.0")) is False

    def test_single_greater_equal(self, parse_version, parse_range):
        r = parse_range(">=1.2.3")
        assert r.satisfies(parse_version("1.2.3")) is True
        assert r.satisfies(parse_version("2.0.0")) is True
        assert r.satisfies(parse_version("1.2.2")) is False

    def test_single_less_than(self, parse_version, parse_range):
        r = parse_range("<2.0.0")
        assert r.satisfies(parse_version("1.9.9")) is True
        assert r.satisfies(parse_version("2.0.0")) is False
        assert r.satisfies(parse_version("1.0.0")) is True

    def test_three_conditions(self, parse_version, parse_range):
        r = parse_range(">=1.0.0 <3.0.0 <=2.5.0")
        assert r.satisfies(parse_version("2.5.0")) is True
        assert r.satisfies(parse_version("2.6.0")) is False

    def test_range_str_representation(self, parse_range):
        r = parse_range(">=1.2.3 <2.0.0")
        assert str(r) == ">=1.2.3 <2.0.0"

    def test_range_repr(self, parse_range):
        r = parse_range(">=1.2.3")
        assert repr(r) == "VersionRange.parse('>=1.2.3')"
