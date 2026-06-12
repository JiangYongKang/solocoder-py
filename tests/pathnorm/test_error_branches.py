import pytest

from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    InvalidPathError,
    PathNormalizer,
    PathResolver,
    SymlinkLoopError,
)
from .conftest import make_normalizer, make_resolver


class TestSymlinkLoopDetection:
    def test_direct_self_loop(self):
        r = make_resolver(symlinks={"/a": "/a"})
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a")

    def test_two_element_loop(self):
        r = make_resolver(
            symlinks={"/a": "/b", "/b": "/a"},
        )
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a/c")

    def test_three_element_loop(self):
        r = make_resolver(
            symlinks={"/a": "/b", "/b": "/c", "/c": "/a"},
        )
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a/x")

    def test_long_chain_before_loop(self):
        r = make_resolver(
            symlinks={
                "/a": "/b",
                "/b": "/c",
                "/c": "/d",
                "/d": "/b",
            },
        )
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a/e")

    def test_exceed_max_symlink_follows(self):
        symlinks = {}
        for i in range(50):
            symlinks[f"/link{i}"] = f"/link{i + 1}"
        r = make_resolver(symlinks=symlinks)
        with pytest.raises(SymlinkLoopError):
            r.resolve("/link0")

    def test_loop_error_contains_path_info(self):
        r = make_resolver(symlinks={"/loop": "/loop"})
        with pytest.raises(SymlinkLoopError) as exc_info:
            r.resolve("/loop/test")
        assert "/loop" in str(exc_info.value)


class TestIllegalCharacterHandling:
    def test_null_byte_in_path(self):
        n = make_normalizer()
        with pytest.raises(InvalidPathError):
            n.normalize("/a/b\x00c")

    def test_control_characters(self):
        n = make_normalizer()
        for i in range(0x00, 0x20):
            with pytest.raises(InvalidPathError):
                n.normalize(f"/a/b{chr(i)}c")

    def test_error_message_contains_reason(self):
        n = make_normalizer()
        with pytest.raises(InvalidPathError) as exc_info:
            n.normalize("/path\x00with\x01nulls")
        assert "illegal characters" in str(exc_info.value)
        assert "/path" in str(exc_info.value)


class TestMissingComponentInSymlinkResolve:
    def test_missing_intermediate_component(self):
        r = make_resolver()
        result = r.resolve("/a/b/c/d")
        assert result == "/a/b/c/d"

    def test_symlink_in_nonexistent_parent(self):
        r = make_resolver(
            symlinks={"/a/b": "/x"},
        )
        result = r.resolve("/a/b/c")
        assert "/x" in result or result.endswith("/c")

    def test_resolver_with_nonexistent_symlink_target(self):
        r = make_resolver(
            symlinks={"/a": "/nonexistent/target"},
        )
        result = r.resolve("/a/b")
        assert result == "/nonexistent/target/b"


class TestCaseSensitiveDifferentPaths:
    def test_case_different_sensitive_not_equal(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("/A/B/C", "/a/b/c") is False

    def test_case_different_after_normalization_sensitive(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("/A/./B/../C", "/a/c") is False

    def test_partial_case_difference_sensitive(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("/a/B/c", "/a/b/c") is False

    def test_case_different_insensitive_equal(self):
        n = make_normalizer(case_sensitive=False)
        assert n.are_equal("/A/B/C", "/a/b/c") is True


class TestEmptyStringVsRoot:
    def test_empty_not_equivalent_to_root_sensitive(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("", "/") is False

    def test_empty_not_equivalent_to_root_insensitive(self):
        n = make_normalizer(case_sensitive=False)
        assert n.are_equal("", "/") is False

    def test_dot_not_equivalent_to_root(self):
        n = make_normalizer()
        assert n.are_equal(".", "/") is False

    def test_dot_equivalent_to_empty(self):
        n = make_normalizer()
        assert n.are_equal(".", "") is True


class TestTypeValidation:
    def test_non_string_path_raises_typeerror(self):
        n = make_normalizer()
        with pytest.raises(TypeError):
            n.normalize(123)
        with pytest.raises(TypeError):
            n.normalize(None)
        with pytest.raises(TypeError):
            n.normalize(["/a", "b"])


class TestMaxPathLength:
    def test_path_exceeds_max_length(self):
        n = PathNormalizer(max_path_length=10)
        long_path = "/a" + "/b" * 100
        with pytest.raises(InvalidPathError):
            n.normalize(long_path)

    def test_error_message_contains_length(self):
        n = PathNormalizer(max_path_length=5)
        with pytest.raises(InvalidPathError) as exc_info:
            n.normalize("/abcdefghij")
        assert "exceeds maximum" in str(exc_info.value)


class TestResolverEquivalenceErrorCases:
    def test_equivalence_with_loop_returns_false(self):
        r = make_resolver(symlinks={"/a": "/b", "/b": "/a"})
        assert r.are_equivalent("/a", "/b") is False

    def test_equivalence_with_illegal_chars_in_path1(self):
        n = make_normalizer()
        r = make_resolver(normalizer=n)
        result = r.are_equivalent("/a\x00/b", "/a/b", resolve_symlinks=False)
        assert result is False

    def test_equivalence_normalization_only(self):
        r = make_resolver(
            symlinks={"/a": "/x/y"},
        )
        assert r.are_equivalent("/a/./b", "/a/b", resolve_symlinks=False) is True
