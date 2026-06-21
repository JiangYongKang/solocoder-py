from __future__ import annotations

import pytest

from solocoder_py.url_parser import (
    InvalidSchemeError,
    InvalidUrlError,
    InvalidPortError,
    PercentDecodeError,
    UrlBuildError,
    UrlBuilder,
    UrlParser,
    parse_url,
    percent_decode,
    percent_encode,
    QueryParams,
    validate_scheme,
)


class TestBoundaryConditions:
    def test_minimal_url_scheme_host(self):
        result = parse_url("http://example.com")
        assert result.scheme == "http"
        assert result.host == "example.com"
        assert result.path == ""
        assert result.query is None
        assert result.fragment is None
        assert result.port is None
        assert result.userinfo is None

    def test_url_no_query_no_fragment(self):
        result = parse_url("http://example.com/path/to/resource")
        assert result.query is None
        assert result.fragment is None

    def test_empty_path_vs_root_path(self):
        result_empty = parse_url("http://example.com")
        result_root = parse_url("http://example.com/")
        assert result_empty.path == ""
        assert result_root.path == "/"

    def test_default_port_omitted(self):
        result = parse_url("http://example.com:80/path")
        assert result.port == 80
        rebuilt = result.rebuild()
        assert ":80" in rebuilt

    def test_port_zero(self):
        result = parse_url("http://example.com:0")
        assert result.port == 0

    def test_deeply_nested_path(self):
        url = "http://example.com/a/b/c/d/e/f/g/h"
        result = parse_url(url)
        assert result.path == "/a/b/c/d/e/f/g/h"

    def test_path_normalization_deep(self):
        url = "http://example.com/a/b/c/d/e/f"
        result = parse_url(url)
        assert result.rebuild() == url

    def test_query_with_empty_value(self):
        result = parse_url("http://example.com?key=")
        assert result.query == "key="

    def test_fragment_empty(self):
        result = parse_url("http://example.com#")
        assert result.fragment == ""

    def test_query_multiple_same_key(self):
        qp = QueryParams.from_string("a=1&a=2&a=3")
        assert len(qp) == 3
        assert qp.get_param_all("a") == ["1", "2", "3"]

    def test_percent_encode_preserve_unreserved(self):
        result = percent_encode("ABCxyz0123456789-._~")
        assert result == "ABCxyz0123456789-._~"

    def test_ipv6_loopback(self):
        result = parse_url("http://[::1]/path")
        assert result.host == "[::1]"

    def test_ipv6_with_port(self):
        result = parse_url("http://[::1]:8080/path")
        assert result.host == "[::1]"
        assert result.port == 8080

    def test_url_with_only_path_no_host(self):
        result = parse_url("mailto:user@example.com")
        assert result.scheme == "mailto"
        assert result.host is None
        assert "user@example.com" in result.path

    def test_builder_no_port(self):
        url = UrlBuilder().scheme("http").host("example.com").build()
        assert ":" not in url.replace("http://", "").replace("example.com", "")

    def test_builder_path_normalization(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .path("//double//slash//")
            .build()
        )
        assert "http://example.com/double/slash" == url

    def test_builder_set_query_param(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .add_query_param("k", "1")
            .add_query_param("k", "2")
            .set_query_param("k", "3")
            .build()
        )
        assert url == "http://example.com?k=3"

    def test_builder_remove_query_param(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .add_query_param("a", "1")
            .add_query_param("b", "2")
            .remove_query_param("a")
            .build()
        )
        assert url == "http://example.com?b=2"


class TestErrorBranches:
    def test_invalid_scheme_format_digit_start(self):
        with pytest.raises((InvalidSchemeError, InvalidUrlError)):
            parse_url("1http://example.com")

    def test_invalid_scheme_format_special_char(self):
        with pytest.raises(InvalidSchemeError):
            validate_scheme("ht tp")

    def test_invalid_scheme_empty(self):
        with pytest.raises(InvalidSchemeError):
            validate_scheme("")

    def test_empty_url(self):
        with pytest.raises(InvalidUrlError):
            parse_url("")

    def test_host_missing_in_url(self):
        result = parse_url("file:///path/to/file")
        assert result.host is None or result.host == ""

    def test_authority_none_for_file_url_with_double_slash(self):
        result = parse_url("file:///path/to/file")
        assert result.has_authority is True
        assert result.host is None
        assert result.authority is None
        assert result.authority is not ""
        assert result.rebuild() == "file:///path/to/file"

    def test_authority_none_for_empty_double_slash(self):
        result = parse_url("file://")
        assert result.has_authority is True
        assert result.host is None
        assert result.authority is None
        assert result.rebuild() == "file://"

    def test_authority_none_for_no_double_slash_scheme(self):
        result = parse_url("mailto:user@example.com")
        assert result.has_authority is False
        assert result.authority is None
        assert result.rebuild() == "mailto:user@example.com"

    def test_authority_none_for_http_no_host(self):
        result = parse_url("http://")
        assert result.has_authority is True
        assert result.host is None
        assert result.authority is None
        assert result.authority is not ""
        assert result.rebuild() == "http://"

    def test_authority_is_none_for_file_root(self):
        result = parse_url("file:///")
        assert result.has_authority is True
        assert result.authority is None
        assert result.path == "/"
        assert result.rebuild() == "file:///"

    def test_percent_decode_incomplete(self):
        with pytest.raises(PercentDecodeError):
            percent_decode("hello%", errors="strict")

    def test_percent_decode_incomplete_single_hex(self):
        with pytest.raises(PercentDecodeError):
            percent_decode("hello%2", errors="strict")

    def test_percent_decode_non_hex(self):
        with pytest.raises(PercentDecodeError):
            percent_decode("hello%GG", errors="strict")

    def test_percent_decode_incomplete_replace(self):
        result = percent_decode("hello%", errors="replace")
        assert "hello" in result

    def test_percent_decode_incomplete_ignore(self):
        result = percent_decode("hello%", errors="ignore")
        assert "hello" in result

    def test_percent_decode_non_hex_replace(self):
        result = percent_decode("hello%GG", errors="replace")
        assert "hello" in result

    def test_url_with_space(self):
        result = parse_url("http://example.com/path%20with%20spaces")
        assert result.path == "/path%20with%20spaces"

    def test_builder_no_scheme_raises(self):
        builder = UrlBuilder().host("example.com")
        with pytest.raises(UrlBuildError):
            builder.build()

    def test_builder_invalid_port_negative(self):
        with pytest.raises(UrlBuildError):
            UrlBuilder().port(-1)

    def test_builder_invalid_port_too_large(self):
        with pytest.raises(UrlBuildError):
            UrlBuilder().port(70000)

    def test_scheme_with_invalid_chars(self):
        with pytest.raises(InvalidSchemeError):
            validate_scheme("http#")

    def test_url_no_scheme(self):
        with pytest.raises(InvalidUrlError):
            parse_url("//example.com/path")

    def test_port_non_numeric_in_url(self):
        with pytest.raises(InvalidPortError):
            parse_url("http://example.com:abc/path")

    def test_query_params_remove_nonexistent(self):
        qp = QueryParams()
        removed = qp.remove_param("nonexistent")
        assert removed == 0

    def test_query_params_get_nonexistent(self):
        qp = QueryParams()
        assert qp.get_param("nonexistent") is None
        assert qp.get_param_all("nonexistent") == []

    def test_decode_encode_roundtrip_special_chars(self):
        original = "hello+world&foo=bar"
        encoded = percent_encode(original)
        decoded = percent_decode(encoded)
        assert decoded == original

    def test_parse_url_with_ipv4_host(self):
        result = parse_url("http://192.168.1.1/path")
        assert result.host == "192.168.1.1"
        assert result.path == "/path"

    def test_percent_encode_type_error(self):
        with pytest.raises(TypeError):
            percent_encode(123)

    def test_percent_decode_type_error(self):
        with pytest.raises(TypeError):
            percent_decode(123)

    def test_url_with_userinfo_no_port(self):
        result = parse_url("http://user@example.com/path")
        assert result.userinfo == "user"
        assert result.host == "example.com"
        assert result.port is None

    def test_url_only_scheme_and_host(self):
        result = parse_url("ftp://ftp.example.com")
        assert result.scheme == "ftp"
        assert result.host == "ftp.example.com"
