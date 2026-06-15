from __future__ import annotations

import pytest

from solocoder_py.version_negotiator import (
    ParsedVersion,
    VersionNegotiator,
    VersionedRequest,
    VersionedResponse,
)


class TestExactVersionMatching:
    def test_exact_match_v1(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = basic_negotiator.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"
        assert response.get_header("X-API-Version") == "v1"

    def test_exact_match_v2(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"
        assert response.get_header("X-API-Version") == "v2"

    def test_exact_match_with_semver(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1.5"},
        )
        response = negotiator_with_semver.process(request)
        assert response.body["version"] == "v1.5"

    def test_exact_match_with_date_version(
        self, negotiator_with_date_versions: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2024-06"},
        )
        response = negotiator_with_date_versions.process(request)
        assert response.body["version"] == "v2024-06"


class TestCompatibleVersionMatching:
    def test_compatible_match_major_version(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_semver.process(request)
        assert response.body["version"] == "v1.5"
        assert response.get_header("X-API-Version-Matched-As") == "compatible"

    def test_compatible_match_minor_version(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        response = negotiator_with_semver.process(request)
        assert response.body["version"] == "v2.1"

    def test_compatible_match_specific_minor(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2.0"},
        )
        response = negotiator_with_semver.process(request)
        assert response.body["version"] == "v2.0"
        assert response.get_header("X-API-Version-Matched-As") != "compatible"

    def test_compatible_match_highest_version(
        self, negotiator_with_semver: VersionNegotiator
    ):
        negotiator_with_semver.register("v2.1.5", lambda r: VersionedResponse(
            body={"version": "v2.1.5"}
        ))
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        response = negotiator_with_semver.process(request)
        assert response.body["version"] == "v2.1.5"

    def test_explicit_compatible_declaration(
        self,
        default_config,
        manual_clock,
        make_handler,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.register("v2", make_handler("v2"), compatible_with=["v1"])
        negotiator.set_default_version("v2")

        negotiator.unregister("v1")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v2"
        assert response.get_header("X-API-Version-Matched-As") == "compatible"


class TestDefaultVersionFallback:
    def test_no_version_header_uses_default(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(path="/api/test")
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"
        assert response.get_header("X-API-Version-Matched-As") == "default"

    def test_empty_version_header_uses_default(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": ""},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"
        assert response.get_header("X-API-Version-Matched-As") == "default"

    def test_whitespace_version_header_uses_default(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "  "},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"


class TestDeprecatedVersionHandling:
    def test_deprecated_version_returns_response_with_headers(
        self,
        negotiator_with_deprecated: VersionNegotiator,
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"
        assert response.get_header("Deprecation") == "true"
        assert response.get_header("X-Deprecation-Message") == "v1 is deprecated, please use v2"
        assert response.get_header("Sunset") is not None
        assert response.get_header("X-Recommended-Version") == "v2"

    def test_deprecated_version_before_sunset_still_works(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        manual_clock.advance(500_000)
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"

    def test_non_deprecated_version_has_no_deprecation_headers(
        self,
        negotiator_with_deprecated: VersionNegotiator,
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.get_header("Deprecation") is None
        assert response.get_header("Sunset") is None


class TestVersionRegistration:
    def test_register_multiple_versions(self, default_config, manual_clock, make_handler):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.register("v2", make_handler("v2"))
        negotiator.register("v3", make_handler("v3"))

        assert len(negotiator) == 3
        assert "v1" in negotiator
        assert "v2" in negotiator
        assert "v3" in negotiator

    def test_list_versions(self, basic_negotiator: VersionNegotiator):
        versions = basic_negotiator.list_versions()
        assert set(versions) == {"v1", "v2"}

    def test_unregister_version(self, basic_negotiator: VersionNegotiator):
        basic_negotiator.unregister("v1")
        assert "v1" not in basic_negotiator
        assert len(basic_negotiator) == 1

    def test_get_processor(self, basic_negotiator: VersionNegotiator):
        processor = basic_negotiator.get_processor("v1")
        assert processor is not None
        assert processor.version == "v1"

        processor = basic_negotiator.get_processor("nonexistent")
        assert processor is None


class TestParsedVersion:
    def test_parse_simple_version(self):
        v = ParsedVersion.parse("v1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.date_suffix is None

    def test_parse_minor_version(self):
        v = ParsedVersion.parse("v2.1")
        assert v.major == 2
        assert v.minor == 1
        assert v.patch == 0

    def test_parse_full_version(self):
        v = ParsedVersion.parse("v2.1.3")
        assert v.major == 2
        assert v.minor == 1
        assert v.patch == 3

    def test_parse_date_version(self):
        v = ParsedVersion.parse("v2024-01")
        assert v.major == 2024
        assert v.date_suffix == "2024-01"

    def test_parse_full_date_version(self):
        v = ParsedVersion.parse("v2024-06-15")
        assert v.major == 2024
        assert v.date_suffix == "2024-06-15"

    def test_compatible_with_same_major(self):
        v1 = ParsedVersion.parse("v1.5")
        v2 = ParsedVersion.parse("v1")
        assert v1.is_compatible_with(v2)

    def test_compatible_with_same_minor(self):
        v1 = ParsedVersion.parse("v1.2.3")
        v2 = ParsedVersion.parse("v1.2")
        assert v1.is_compatible_with(v2)

    def test_compatible_with_exact(self):
        v1 = ParsedVersion.parse("v1.2.3")
        v2 = ParsedVersion.parse("v1.2.3")
        assert v1.is_compatible_with(v2)

    def test_not_compatible_different_major(self):
        v1 = ParsedVersion.parse("v2.0")
        v2 = ParsedVersion.parse("v1.0")
        assert not v1.is_compatible_with(v2)

    def test_not_compatible_lower_minor(self):
        v1 = ParsedVersion.parse("v1.1")
        v2 = ParsedVersion.parse("v1.2")
        assert not v1.is_compatible_with(v2)

    def test_date_version_not_compatible(self):
        v1 = ParsedVersion.parse("v2024-06")
        v2 = ParsedVersion.parse("v2024-01")
        assert not v1.is_compatible_with(v2)


class TestNegotiationResult:
    def test_negotiate_exact_match(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        result = basic_negotiator.negotiate(request)
        assert result.matched_exactly is True
        assert result.used_default is False
        assert result.matched_version == "v1"

    def test_negotiate_compatible_match(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        result = negotiator_with_semver.negotiate(request)
        assert result.matched_exactly is False
        assert result.used_default is False
        assert result.matched_version == "v1.5"

    def test_negotiate_default(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(path="/api/test")
        result = basic_negotiator.negotiate(request)
        assert result.matched_exactly is True
        assert result.used_default is True
        assert result.matched_version == "v2"


class TestHeaderCaseInsensitivity:
    def test_accept_version_header_case_insensitive(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"accept-version": "v1"},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_accept_version_header_mixed_case(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_deprecation_header_case_insensitive(
        self, negotiator_with_deprecated: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.get_header("deprecation") == "true"
