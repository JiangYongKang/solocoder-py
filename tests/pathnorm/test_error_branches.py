import pytest

from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    InvalidPathError,
    MaxSymlinkFollowsError,
    PathNormalizer,
    PathNotFoundError,
    PathResolver,
    SymlinkLoopError,
)
from .conftest import make_normalizer, make_resolver


class TestSymlinkLoopDetection:
    def test_direct_self_loop(self):
        r = make_resolver(symlinks={"/a": "/a"}, directories={"/a"})
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a")

    def test_two_element_loop(self):
        r = make_resolver(
            symlinks={"/a": "/b", "/b": "/a"},
            directories={"/a", "/b"},
        )
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a/c")

    def test_three_element_loop(self):
        r = make_resolver(
            symlinks={"/a": "/b", "/b": "/c", "/c": "/a"},
            directories={"/a", "/b", "/c"},
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
            directories={"/a", "/b", "/c", "/d"},
        )
        with pytest.raises(SymlinkLoopError):
            r.resolve("/a/e")

    def test_exceed_max_symlink_follows(self):
        symlinks = {}
        directories = set()
        for i in range(50):
            symlinks[f"/link{i}"] = f"/link{i + 1}"
            directories.add(f"/link{i}")
        directories.add("/link50")
        r = make_resolver(symlinks=symlinks, directories=directories)
        with pytest.raises(MaxSymlinkFollowsError):
            r.resolve("/link0")

    def test_max_symlink_follows_error_contains_info(self):
        symlinks = {}
        directories = set()
        for i in range(50):
            symlinks[f"/link{i}"] = f"/link{i + 1}"
            directories.add(f"/link{i}")
        directories.add("/link50")
        r = make_resolver(symlinks=symlinks, directories=directories)
        with pytest.raises(MaxSymlinkFollowsError) as exc_info:
            r.resolve("/link0")
        assert "40" in str(exc_info.value)
        assert exc_info.value.max_follows == 40

    def test_loop_error_contains_path_info(self):
        r = make_resolver(symlinks={"/loop": "/loop"}, directories={"/loop"})
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
    def test_missing_intermediate_component_raises(self):
        r = make_resolver(directories={"/a"})
        with pytest.raises(PathNotFoundError) as exc_info:
            r.resolve("/a/b/c/d")
        assert exc_info.value.component == "b"
        assert "b" in str(exc_info.value)

    def test_last_component_missing_is_allowed(self):
        r = make_resolver(directories={"/a", "/a/b", "/a/b/c"})
        result = r.resolve("/a/b/c/d")
        assert result == "/a/b/c/d"

    def test_symlink_with_existing_parent(self):
        r = make_resolver(
            symlinks={"/a/b": "/x/y"},
            directories={"/a", "/x", "/x/y"},
        )
        result = r.resolve("/a/b/c")
        assert result == "/x/y/c"

    def test_resolver_with_nonexistent_symlink_target_intermediate(self):
        r = make_resolver(
            symlinks={"/a": "/nonexistent/target"},
            directories={"/a"},
        )
        with pytest.raises(PathNotFoundError) as exc_info:
            r.resolve("/a/b")
        assert exc_info.value.component == "nonexistent"

    def test_symlink_target_last_component_missing_allowed(self):
        r = make_resolver(
            symlinks={"/a": "/x/y"},
            directories={"/a", "/x"},
        )
        result = r.resolve("/a")
        assert result == "/x/y"


class TestPathNotFoundErrorScenarios:
    def test_absolute_path_first_component_missing(self):
        r = make_resolver()
        with pytest.raises(PathNotFoundError):
            r.resolve("/a/b")

    def test_relative_path_intermediate_missing(self):
        r = make_resolver(directories={"a"})
        with pytest.raises(PathNotFoundError):
            r.resolve("a/b/c/d")

    def test_relative_path_all_components_exist_but_last(self):
        r = make_resolver(directories={"a", "a/b", "a/b/c"})
        result = r.resolve("a/b/c/d")
        assert result == "a/b/c/d"

    def test_exists_returns_false_on_missing_component(self):
        r = make_resolver(directories={"/a"})
        assert r.exists("/a/b/c") is False


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
