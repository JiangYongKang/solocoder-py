from __future__ import annotations

import pytest

from solocoder_py.version_negotiator import (
    DefaultVersionNotSetError,
    DuplicateVersionError,
    EmptyProcessorRegistryError,
    InvalidCompatibilityError,
    InvalidVersionFormatError,
    VersionDeprecatedError,
    VersionNegotiator,
    VersionNegotiatorConfig,
    VersionNotFoundError,
    VersionedRequest,
)


class TestVersionNotFoundErrorBranches:
    def test_version_not_found_no_compatible(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v3"},
        )
        with pytest.raises(VersionNotFoundError) as exc_info:
            basic_negotiator.process(request)

        assert exc_info.value.requested_version == "v3"
        assert set(exc_info.value.available_versions) == {"v1", "v2"}
        assert "v3" in str(exc_info.value)
        assert "Available versions" in str(exc_info.value)

    def test_version_not_found_with_semver_no_compatible(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v3.0"},
        )
        with pytest.raises(VersionNotFoundError) as exc_info:
            negotiator_with_semver.process(request)

        assert exc_info.value.requested_version == "v3.0"
        assert set(exc_info.value.available_versions) == {
            "v1.0",
            "v1.5",
            "v2.0",
            "v2.1",
        }

    def test_version_not_found_invalid_format(
        self, basic_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "invalid-version"},
        )
        with pytest.raises(VersionNotFoundError) as exc_info:
            basic_negotiator.process(request)

        assert exc_info.value.requested_version == "invalid-version"

    def test_version_not_found_major_mismatch(
        self, negotiator_with_semver: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v3"},
        )
        with pytest.raises(VersionNotFoundError):
            negotiator_with_semver.process(request)

    def test_version_not_found_with_strict_mode(
        self, strict_negotiator: VersionNegotiator
    ):
        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionNotFoundError):
            strict_negotiator.process(request)


class TestDuplicateVersionErrorBranches:
    def test_duplicate_version_registration(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        with pytest.raises(DuplicateVersionError) as exc_info:
            negotiator.register("v1", make_handler("v1-different"))

        assert exc_info.value.version == "v1"
        assert "v1" in str(exc_info.value)

    def test_duplicate_version_after_unregister_allowed(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.unregister("v1")
        negotiator.register("v1", make_handler("v1-new"))

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["message"] == "Hello from v1-new"

    def test_duplicate_version_case_sensitive(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        with pytest.raises(InvalidVersionFormatError):
            negotiator.register("V1", make_handler("V1"))


class TestVersionDeprecatedErrorBranches:
    def test_sunset_date_passed_rejected(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        sunset_at = base_timestamp + 1_000_000
        manual_clock.advance(2_000_000)

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionDeprecatedError) as exc_info:
            negotiator_with_deprecated.process(request)

        assert exc_info.value.version == "v1"
        assert exc_info.value.sunset_at == sunset_at
        assert "v1" in str(exc_info.value)
        assert str(sunset_at) in str(exc_info.value)

    def test_sunset_date_passed_via_default(
        self,
        default_config,
        manual_clock,
        make_handler,
        base_timestamp,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        sunset_at = base_timestamp + 100
        negotiator.register(
            "v1",
            make_handler("v1"),
            is_deprecated=True,
            sunset_at=sunset_at,
        )
        negotiator.set_default_version("v1")

        manual_clock.advance(200)

        request = VersionedRequest(path="/api/test")
        with pytest.raises(VersionDeprecatedError):
            negotiator.process(request)

    def test_sunset_date_passed_via_compatible(
        self,
        default_config,
        manual_clock,
        make_handler,
        base_timestamp,
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        sunset_at = base_timestamp + 100
        negotiator.register(
            "v1.5",
            make_handler("v1.5"),
            is_deprecated=True,
            sunset_at=sunset_at,
        )
        negotiator.register("v2", make_handler("v2"))
        negotiator.set_default_version("v2")

        manual_clock.advance(200)

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionDeprecatedError):
            negotiator.process(request)

    def test_non_deprecated_version_passes_sunset_check(
        self,
        negotiator_with_deprecated: VersionNegotiator,
        manual_clock,
        base_timestamp,
    ):
        manual_clock.advance(10_000_000)

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v2"},
        )
        response = negotiator_with_deprecated.process(request)
        assert response.status_code == 200


class TestEmptyProcessorRegistryErrorBranches:
    def test_process_with_empty_registry(self, default_config, manual_clock):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)

        request = VersionedRequest(path="/api/test")
        with pytest.raises(EmptyProcessorRegistryError):
            negotiator.process(request)

    def test_negotiate_with_empty_registry(self, default_config, manual_clock):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)

        request = VersionedRequest(path="/api/test")
        with pytest.raises(EmptyProcessorRegistryError):
            negotiator.negotiate(request)

    def test_process_after_unregister_all(self, basic_negotiator: VersionNegotiator):
        basic_negotiator.unregister("v1")
        basic_negotiator.unregister("v2")

        request = VersionedRequest(path="/api/test")
        with pytest.raises(EmptyProcessorRegistryError):
            basic_negotiator.process(request)


class TestDefaultVersionNotSetErrorBranches:
    def test_no_default_version_without_header(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        request = VersionedRequest(path="/api/test")
        with pytest.raises(DefaultVersionNotSetError):
            negotiator.process(request)

    def test_get_default_version_not_set(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        with pytest.raises(DefaultVersionNotSetError):
            negotiator.get_default_version()

    def test_set_default_version_not_registered(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        with pytest.raises(VersionNotFoundError):
            negotiator.set_default_version("v2")


class TestInvalidVersionFormatErrorBranches:
    def test_invalid_format_no_v_prefix(self):
        with pytest.raises(InvalidVersionFormatError) as exc_info:
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("1.0.0")

        assert exc_info.value.version == "1.0.0"

    def test_invalid_format_empty_string(self):
        with pytest.raises(InvalidVersionFormatError) as exc_info:
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("")

        assert exc_info.value.version == ""

    def test_invalid_format_none(self):
        with pytest.raises(InvalidVersionFormatError):
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse(None)

    def test_invalid_format_just_v(self):
        with pytest.raises(InvalidVersionFormatError):
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("v")

    def test_invalid_format_letters(self):
        with pytest.raises(InvalidVersionFormatError):
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("vabc")

    def test_invalid_format_malformed_date(self):
        with pytest.raises(InvalidVersionFormatError):
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("v2024-1")

    def test_invalid_format_negative_numbers(self):
        with pytest.raises(InvalidVersionFormatError):
            from solocoder_py.version_negotiator import ParsedVersion

            ParsedVersion.parse("v-1")

    def test_invalid_format_registration(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)

        with pytest.raises(InvalidVersionFormatError):
            negotiator.register("invalid", make_handler("invalid"))


class TestInvalidCompatibilityErrorBranches:
    def test_compatible_with_unregistered_version(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)

        with pytest.raises(InvalidCompatibilityError) as exc_info:
            negotiator.register(
                "v2",
                make_handler("v2"),
                compatible_with=["v1"],
            )

        assert exc_info.value.from_version == "v1"
        assert exc_info.value.to_version == "v2"
        assert "v1" in str(exc_info.value)
        assert "v2" in str(exc_info.value)

    def test_compatible_with_multiple_unregistered(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        with pytest.raises(InvalidCompatibilityError) as exc_info:
            negotiator.register(
                "v3",
                make_handler("v3"),
                compatible_with=["v1", "v2"],
            )

        assert exc_info.value.from_version == "v2"

    def test_compatible_with_self_allowed(
        self, default_config, manual_clock, make_handler
    ):
        negotiator = VersionNegotiator(config=default_config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))

        negotiator.register(
            "v2",
            make_handler("v2"),
            compatible_with=["v1"],
        )

        assert "v2" in negotiator
        processor = negotiator.get_processor("v2")
        assert processor.compatible_with == ["v1"]


class TestExceptionHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(VersionNotFoundError, Exception)
        assert issubclass(VersionNotFoundError, Exception)
        assert issubclass(DuplicateVersionError, Exception)
        assert issubclass(VersionDeprecatedError, Exception)
        assert issubclass(InvalidVersionFormatError, Exception)
        assert issubclass(EmptyProcessorRegistryError, Exception)
        assert issubclass(DefaultVersionNotSetError, Exception)
        assert issubclass(InvalidCompatibilityError, Exception)

    def test_catch_all_with_base_exception(
        self, basic_negotiator: VersionNegotiator
    ):
        from solocoder_py.version_negotiator import VersionNegotiatorError

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v999"},
        )
        with pytest.raises(VersionNegotiatorError):
            basic_negotiator.process(request)


class TestConfigValidation:
    def test_config_none_accept_version_header(self):
        with pytest.raises(ValueError):
            VersionNegotiatorConfig(accept_version_header=None)

    def test_config_none_deprecation_header(self):
        with pytest.raises(ValueError):
            VersionNegotiatorConfig(deprecation_header=None)

    def test_config_none_sunset_header(self):
        with pytest.raises(ValueError):
            VersionNegotiatorConfig(sunset_header=None)

    def test_config_valid_allows_custom_headers(self):
        config = VersionNegotiatorConfig(
            accept_version_header="X-API-Version",
            deprecation_header="X-Deprecated",
            sunset_header="X-Sunset-Date",
        )
        assert config.accept_version_header == "X-API-Version"
        assert config.deprecation_header == "X-Deprecated"
        assert config.sunset_header == "X-Sunset-Date"

    def test_custom_header_name_in_request(
        self, manual_clock, make_handler
    ):
        config = VersionNegotiatorConfig(
            default_version="v2",
            accept_version_header="X-API-Version",
        )
        negotiator = VersionNegotiator(config=config, clock=manual_clock)
        negotiator.register("v1", make_handler("v1"))
        negotiator.register("v2", make_handler("v2"))

        request = VersionedRequest(
            path="/api/test",
            headers={"X-API-Version": "v1"},
        )
        response = negotiator.process(request)
        assert response.body["version"] == "v1"


class TestUnregisterEdgeCases:
    def test_unregister_nonexistent_no_error(
        self, basic_negotiator: VersionNegotiator
    ):
        basic_negotiator.unregister("nonexistent")
        assert len(basic_negotiator) == 2

    def test_unregister_default_version(
        self, basic_negotiator: VersionNegotiator
    ):
        basic_negotiator.unregister("v2")

        request = VersionedRequest(path="/api/test")
        with pytest.raises(VersionNotFoundError):
            basic_negotiator.process(request)

    def test_unregister_then_negotiate(
        self, basic_negotiator: VersionNegotiator
    ):
        basic_negotiator.unregister("v1")

        request = VersionedRequest(
            path="/api/test",
            headers={"Accept-Version": "v1"},
        )
        with pytest.raises(VersionNotFoundError):
            basic_negotiator.process(request)
