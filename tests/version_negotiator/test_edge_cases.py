from __future__ import annotations

import pytest

from solocoder_py.version_negotiator import (
    ParsedVersion,
    VersionNegotiator,
    VersionNegotiatorConfig,
    VersionedRequest,
    VersionedResponse,
)


class TestNoVersionHeaderEdgeCases:
    def test_no_headers_at_all(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"
        assert response.get_header("X-API-Version-Matched-As") == "default"

    def test_no_headers_dict(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(path="/api/test")
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"

    def test_other_headers_present_but_no_version(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer token",
            },
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"

    def test_header_key_exists_but_none_value(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": None},
        )
        request.headers = {
            k: v for k, v in request.headers.items() if v is not None
        }
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"


class TestDeprecatedVersionDualPath:
    def test_deprecated_version_exact_match_with_headers(
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
        assert response.get_header("Sunset") is not None
        assert response.get_header("X-Deprecation-Message") is not None
        assert response.get_header("X-Recommended-Version") == "v2"
        assert response.get_header("X-API-Version") == "v1"

    def test_deprecated_version_compatible_match(
        self,
        default_config,
        manual_clock,
        make_handler,
        base_timestamp,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        sunset_at = base_timestamp + 1_000_000
        negotiator.register(
            "v1.5",
            make_handler("v1.5"),
            is_deprecated=True,
            sunset_at=sunset_at,
            deprecation_message="v1.x is deprecated",
        )
        negotiator.register("v2.0", make_handler("v2.0"))
        negotiator.set_default_version("v2.0")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)

        assert response.body["version"] == "v1.5"
        assert response.get_header("Deprecation") == "true"
        assert response.get_header("X-API-Version-Matched-As") == "compatible"

    def test_deprecated_version_but_not_sunset_yet(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        manual_clock.advance(999_999)

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"

    def test_deprecated_version_no_sunset_date(
        self,
        default_config,
        manual_clock,
        make_handler,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register(
            "v1",
            make_handler("v1"),
            is_deprecated=True,
            sunset_at=None,
            deprecation_message="v1 is deprecated but no sunset date",
        )
        negotiator.register("v2", make_handler("v2"))
        negotiator.set_default_version("v2")

        manual_clock.advance(10_000_000)

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"
        assert response.get_header("Deprecation") == "true"
        assert response.get_header("Sunset") is None

    def test_deprecated_version_with_link_header(
        self,
        manual_clock,
        make_handler,
        base_timestamp,
    ):
        config = VersionNegotiatorConfig(
            default_version="v2",
            deprecation_link="https://docs.example.com/deprecation/v1",
        )
        negotiator = VersionNegotiator(config=config, clock=manual_clock)
        sunset_at = base_timestamp + 1_000_000
        negotiator.register(
            "v1",
            make_handler("v1"),
            is_deprecated=True,
            sunset_at=sunset_at,
        )
        negotiator.register("v2", make_handler("v2"))

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.get_header("Link") == (
            '<https://docs.example.com/deprecation/v1>; rel="deprecation"'
        )


class TestVersionFormatEdgeCases:
    def test_version_with_leading_whitespace(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "  v1"},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_version_with_trailing_whitespace(self, basic_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1  "},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_version_with_surrounding_whitespace(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "  v2  "},
        )
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v2"

    def test_parse_version_zero(self):
        v = ParsedVersion.parse("v0")
        assert v.major == 0
        assert v.minor == 0

    def test_parse_version_large_numbers(self):
        v = ParsedVersion.parse("v999.999.999")
        assert v.major == 999
        assert v.minor == 999
        assert v.patch == 999

    def test_parse_version_without_v_prefix_fails(self):
        from solocoder_py.version_negotiator import InvalidVersionFormatError

        with pytest.raises(InvalidVersionFormatError):
            ParsedVersion.parse("1.0.0")

    def test_parse_empty_string_fails(self):
        from solocoder_py.version_negotiator import InvalidVersionFormatError

        with pytest.raises(InvalidVersionFormatError):
            ParsedVersion.parse("")


class TestStrictVersionMatchingEdgeCases:
    def test_strict_mode_exact_match_works(self, strict_negotiator: VersionNegotiator):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1.0"},
        )
        response = strict_negotiator.process(request)
        assert response.body["version"] == "v1.0"

    def test_strict_mode_major_only_fails(self, strict_negotiator: VersionNegotiator):
        from solocoder_py.version_negotiator import VersionNotFoundError

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionNotFoundError) as exc_info:
            strict_negotiator.process(request)
        assert exc_info.value.requested_version == "v1"
        assert set(exc_info.value.available_versions) == {"v1.0", "v2.0"}

    def test_strict_mode_lower_minor_fails(self, strict_negotiator: VersionNegotiator):
        from solocoder_py.version_negotiator import VersionNotFoundError

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        with pytest.raises(VersionNotFoundError):
            strict_negotiator.process(request)


class TestRequireVersionHeaderEdgeCases:
    def test_require_header_with_header_present(
        self, default_config, manual_clock, make_handler
    ):
        config = VersionNegotiatorConfig(
            default_version="v2",
            require_version_header=True,
        )
        negotiator = VersionNegotiator(config=config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.register("v2", make_handler("v2"))

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_require_header_without_header_fails(
        self, default_config, manual_clock, make_handler
    ):
        from solocoder_py.version_negotiator import VersionNotFoundError

        config = VersionNegotiatorConfig(
            default_version="v2",
            require_version_header=True,
        )
        negotiator = VersionNegotiator(config=config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.register("v2", make_handler("v2"))

        request = VersionedRequest(path="/api/test")
        with pytest.raises(VersionNotFoundError) as exc_info:
            negotiator.process(request)
        assert exc_info.value.requested_version == "none"


class TestSunsetBoundaryEdgeCases:
    def test_sunset_exact_moment_rejected(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        from solocoder_py.version_negotiator import VersionDeprecatedError

        sunset_at = base_timestamp + 1_000_000
        manual_clock._time = sunset_at

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionDeprecatedError) as exc_info:
            negotiator_with_deprecated.process(request)
        assert exc_info.value.version == "v1"
        assert exc_info.value.sunset_at == sunset_at

    def test_sunset_one_second_before_allowed(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        sunset_at = base_timestamp + 1_000_000
        manual_clock._time = sunset_at - 1

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.status_code == 200
        assert response.body["version"] == "v1"

    def test_sunset_one_second_after_rejected(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        from solocoder_py.version_negotiator import VersionDeprecatedError

        sunset_at = base_timestamp + 1_000_000
        manual_clock._time = sunset_at + 1

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionDeprecatedError):
            negotiator_with_deprecated.process(request)


class TestCompatibleMatchEdgeCases:
    def test_compatible_match_exact_patch_version(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1.2.3", make_handler("v1.2.3"))
        negotiator.set_default_version("v1.2.3")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1.2.3"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1.2.3"
        assert response.get_header("X-API-Version-Matched-As") != "compatible"

    def test_compatible_match_patch_version(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1.2.0", make_handler("v1.2.0"))
        negotiator.register("v1.2.3", make_handler("v1.2.3"))
        negotiator.set_default_version("v1.2.3")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1.2"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1.2.3"

    def test_compatible_match_higher_minor(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1.0", make_handler("v1.0"))
        negotiator.register("v1.5", make_handler("v1.5"))
        negotiator.register("v1.10", make_handler("v1.10"))
        negotiator.set_default_version("v1.10")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1.10"

    def test_compatible_match_skips_higher_major(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1.5", make_handler("v1.5"))
        negotiator.register("v2.0", make_handler("v2.0"))
        negotiator.set_default_version("v2.0")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1.5"

    def test_date_version_exact_match_only(
        self, negotiator_with_date_versions: VersionNegotiator
    ):
        from solocoder_py.version_negotiator import VersionNotFoundError

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2024"},
        )
        with pytest.raises(VersionNotFoundError):
            negotiator_with_date_versions.process(request)

    def test_date_version_exact_match_works(
        self, negotiator_with_date_versions: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2024-01"},
        )
        response = negotiator_with_date_versions.process(request)
        assert response.body["version"] == "v2024-01"


class TestDefaultVersionEdgeCases:
    def test_change_default_version(self, basic_negotiator: VersionNegotiator):
        basic_negotiator.set_default_version("v1")
        assert basic_negotiator.get_default_version() == "v1"

        request = VersionedRequest(path="/api/test")
        response = basic_negotiator.process(request)
        assert response.body["version"] == "v1"

    def test_default_version_also_deprecated(
        self,
        default_config,
        manual_clock,
        make_handler,
        base_timestamp,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        sunset_at = base_timestamp + 1_000_000
        negotiator.register(
            "v1",
            make_handler("v1"),
            is_deprecated=True,
            sunset_at=sunset_at,
        )
        negotiator.set_default_version("v1")

        request = VersionedRequest(path="/api/test")
        response = negotiator.process(request)
        assert response.body["version"] == "v1"
        assert response.get_header("Deprecation") == "true"
        assert response.get_header("X-API-Version-Matched-As") == "default"

    def test_handler_returns_none(
        self, default_config, manual_clock
    ):
        def handler_returns_none(request):
            return None

        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", handler_returns_none)
        negotiator.set_default_version("v1")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response is not None
        assert response.status_code == 200
