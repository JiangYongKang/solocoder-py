from __future__ import annotations

import pytest

from solocoder_py.url_parser import (
    UrlBuilder,
    UrlComponents,
    UrlParser,
    parse_url,
    percent_decode,
    percent_encode,
    percent_encode_component,
    QueryParams,
    QueryParam,
    validate_scheme,
    is_scheme_known,
    register_scheme,
    get_known_schemes,
)


class TestUrlParserStandard:
    def test_parse_full_url(self):
        url = "https://user:pass@example.com:8080/path/to/resource?key=value#fragment"
        result = parse_url(url)
        assert result.scheme == "https"
        assert result.userinfo == "user:pass"
        assert result.host == "example.com"
        assert result.port == 8080
        assert result.path == "/path/to/resource"
        assert result.query == "key=value"
        assert result.fragment == "fragment"

    def test_parse_url_no_userinfo(self):
        url = "http://example.com/path"
        result = parse_url(url)
        assert result.scheme == "http"
        assert result.userinfo is None
        assert result.host == "example.com"
        assert result.port is None
        assert result.path == "/path"

    def test_parse_url_no_port(self):
        url = "http://example.com/path"
        result = parse_url(url)
        assert result.port is None

    def test_parse_url_no_query(self):
        url = "http://example.com/path#fragment"
        result = parse_url(url)
        assert result.query is None
        assert result.fragment == "fragment"

    def test_parse_url_no_fragment(self):
        url = "http://example.com/path?key=value"
        result = parse_url(url)
        assert result.query == "key=value"
        assert result.fragment is None

    def test_parse_url_scheme_only_host(self):
        url = "http://example.com"
        result = parse_url(url)
        assert result.scheme == "http"
        assert result.host == "example.com"
        assert result.path == ""

    def test_parse_url_with_ipv6_host(self):
        url = "http://[::1]:8080/path"
        result = parse_url(url)
        assert result.host == "[::1]"
        assert result.port == 8080
        assert result.path == "/path"

    def test_parse_url_ipv6_full(self):
        url = "https://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]/path"
        result = parse_url(url)
        assert result.host == "[2001:0db8:85a3:0000:0000:8a2e:0370:7334]"
        assert result.path == "/path"

    def test_parse_url_authority_property(self):
        url = "http://user@example.com:8080/path"
        result = parse_url(url)
        assert result.authority == "user@example.com:8080"

    def test_parse_url_rebuild(self):
        url = "https://example.com:8080/path?q=1#frag"
        result = parse_url(url)
        assert result.rebuild() == url


class TestSchemeValidation:
    def test_valid_schemes(self):
        for scheme in ["http", "https", "ftp", "sftp", "my-scheme", "scheme.name", "a0+"]:
            validate_scheme(scheme)

    def test_invalid_scheme_starts_with_digit(self):
        from solocoder_py.url_parser import InvalidSchemeError
        with pytest.raises(InvalidSchemeError):
            validate_scheme("1http")

    def test_invalid_scheme_starts_with_special(self):
        from solocoder_py.url_parser import InvalidSchemeError
        with pytest.raises(InvalidSchemeError):
            validate_scheme("+http")

    def test_invalid_scheme_contains_space(self):
        from solocoder_py.url_parser import InvalidSchemeError
        with pytest.raises(InvalidSchemeError):
            validate_scheme("ht tp")

    def test_known_schemes(self):
        assert is_scheme_known("http")
        assert is_scheme_known("https")
        assert is_scheme_known("ftp")

    def test_unknown_scheme(self):
        assert not is_scheme_known("xyzabc123")

    def test_register_and_check_scheme(self):
        register_scheme("my-custom-scheme")
        assert is_scheme_known("my-custom-scheme")

    def test_get_known_schemes(self):
        schemes = get_known_schemes()
        assert "http" in schemes
        assert "https" in schemes


class TestPercentEncoding:
    def test_encode_unreserved(self):
        assert percent_encode("hello") == "hello"
        assert percent_encode("abc123-._~") == "abc123-._~"

    def test_encode_space(self):
        assert percent_encode("hello world") == "hello%20world"

    def test_encode_unicode(self):
        encoded = percent_encode("中文")
        decoded = percent_decode(encoded)
        assert decoded == "中文"

    def test_encode_safe_chars(self):
        assert percent_encode("a/b", safe="/") == "a/b"

    def test_encode_component(self):
        result = percent_encode_component("hello world")
        assert " " not in result
        assert "%20" in result

    def test_decode_simple(self):
        assert percent_decode("hello%20world") == "hello world"

    def test_decode_unreserved(self):
        assert percent_decode("hello") == "hello"

    def test_roundtrip_ascii(self):
        original = "hello world!@#$%^&*()"
        encoded = percent_encode(original)
        decoded = percent_decode(encoded)
        assert decoded == original

    def test_roundtrip_utf8(self):
        original = "日本語テスト"
        encoded = percent_encode(original)
        decoded = percent_decode(encoded)
        assert decoded == original

    def test_roundtrip_chinese(self):
        original = "中文测试"
        encoded = percent_encode(original)
        decoded = percent_decode(encoded)
        assert decoded == original

    def test_roundtrip_emoji(self):
        original = "🎉"
        encoded = percent_encode(original)
        decoded = percent_decode(encoded)
        assert decoded == original

    def test_decode_mixed(self):
        assert percent_decode("hello%2Bworld") == "hello+world"


class TestQueryParams:
    def test_from_string_simple(self):
        qp = QueryParams.from_string("key=value")
        assert qp.get_param("key") == "value"

    def test_from_string_multiple(self):
        qp = QueryParams.from_string("a=1&b=2&c=3")
        assert qp.get_param("a") == "1"
        assert qp.get_param("b") == "2"
        assert qp.get_param("c") == "3"

    def test_from_string_duplicate_keys(self):
        qp = QueryParams.from_string("key=1&key=2&key=3")
        assert qp.get_param("key") == "3"
        assert qp.get_param_all("key") == ["1", "2", "3"]

    def test_from_string_no_value(self):
        qp = QueryParams.from_string("key")
        assert qp.get_param("key") is None

    def test_add_param(self):
        qp = QueryParams()
        qp.add_param("a", "1")
        qp.add_param("b", "2")
        assert qp.get_param("a") == "1"
        assert qp.get_param("b") == "2"

    def test_add_param_duplicate(self):
        qp = QueryParams()
        qp.add_param("key", "1")
        qp.add_param("key", "2")
        assert qp.get_param_all("key") == ["1", "2"]
        assert qp.get_param("key") == "2"

    def test_remove_param(self):
        qp = QueryParams.from_string("a=1&b=2&c=3")
        removed = qp.remove_param("b")
        assert removed == 1
        assert qp.get_param("b") is None
        assert qp.get_param("a") == "1"

    def test_remove_param_all_duplicates(self):
        qp = QueryParams.from_string("key=1&key=2&key=3")
        removed = qp.remove_param("key")
        assert removed == 3
        assert not qp.has_param("key")

    def test_set_param_replaces_all(self):
        qp = QueryParams.from_string("key=1&key=2&key=3")
        qp.set_param("key", "new")
        assert qp.get_param("key") == "new"
        assert qp.get_param_all("key") == ["new"]

    def test_set_param_new(self):
        qp = QueryParams()
        qp.set_param("key", "value")
        assert qp.get_param("key") == "value"

    def test_to_string(self):
        qp = QueryParams()
        qp.add_param("a", "1")
        qp.add_param("b", "2")
        result = qp.to_string()
        assert result == "a=1&b=2"

    def test_to_string_empty(self):
        qp = QueryParams()
        assert qp.to_string() is None

    def test_from_string_none(self):
        qp = QueryParams.from_string(None)
        assert len(qp) == 0

    def test_from_string_empty(self):
        qp = QueryParams.from_string("")
        assert len(qp) == 0

    def test_roundtrip(self):
        original = "a=1&b=2&c=3"
        qp = QueryParams.from_string(original)
        result = qp.to_string()
        assert result == original

    def test_encoded_query_params(self):
        qp = QueryParams.from_string("name=John%20Doe")
        assert qp.get_param("name") == "John Doe"


class TestUrlBuilder:
    def test_build_simple(self):
        url = UrlBuilder().scheme("http").host("example.com").build()
        assert url == "http://example.com"

    def test_build_with_path(self):
        url = UrlBuilder().scheme("http").host("example.com").path("/api/v1/users").build()
        assert url == "http://example.com/api/v1/users"

    def test_build_with_path_segments(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .path_segment("api")
            .path_segment("v1")
            .path_segment("users")
            .build()
        )
        assert url == "http://example.com/api/v1/users"

    def test_build_with_query(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .add_query_param("q", "test")
            .add_query_param("page", "1")
            .build()
        )
        assert url == "http://example.com?q=test&page=1"

    def test_build_with_fragment(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .fragment("section")
            .build()
        )
        assert url == "http://example.com#section"

    def test_build_full_url(self):
        url = (
            UrlBuilder()
            .scheme("https")
            .userinfo("user:pass")
            .host("example.com")
            .port(8080)
            .path_segment("api")
            .path_segment("v1")
            .add_query_param("key", "value")
            .fragment("frag")
            .build()
        )
        assert "https://" in url
        assert "example.com" in url
        assert "8080" in url
        assert "key=value" in url
        assert "#frag" in url

    def test_build_path_with_extra_slashes(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .path("//api//v1//")
            .build()
        )
        assert "http://example.com/api/v1" == url

    def test_builder_method_chaining(self):
        url = (
            UrlBuilder()
            .scheme("http")
            .host("example.com")
            .port(443)
            .path_segment("test")
            .add_query_param("q", "1")
            .fragment("f")
            .build()
        )
        assert url == "http://example.com:443/test?q=1#f"


class TestParserAndBuilderRoundtrip:
    def test_parse_then_rebuild(self):
        url = "https://example.com:8080/path?key=value#fragment"
        parsed = parse_url(url)
        assert parsed.rebuild() == url

    def test_parse_modify_rebuild(self):
        url = "http://example.com/path?key=value"
        parsed = parse_url(url)
        qp = QueryParams.from_string(parsed.query)
        qp.add_param("new", "param")
        parsed.query = qp.to_string()
        rebuilt = parsed.rebuild()
        assert "new=param" in rebuilt
        assert "key=value" in rebuilt
