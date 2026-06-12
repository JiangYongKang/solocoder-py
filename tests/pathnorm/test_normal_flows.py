import pytest

from solocoder_py.pathnorm import PathNormalizer
from .conftest import make_normalizer, make_resolver


class TestDotComponentRemoval:
    def test_single_dot_in_middle(self):
        n = make_normalizer()
        assert n.normalize("/a/./b") == "/a/b"

    def test_single_dot_at_start_relative(self):
        n = make_normalizer()
        assert n.normalize("./a/b") == "a/b"

    def test_single_dot_alone(self):
        n = make_normalizer()
        assert n.normalize(".") == "."

    def test_multiple_dots_in_sequence(self):
        n = make_normalizer()
        assert n.normalize("/a/./././b") == "/a/b"

    def test_dot_after_dotdot(self):
        n = make_normalizer()
        assert n.normalize("/a/b/.././c") == "/a/c"

    def test_dot_with_trailing_slash(self):
        n = make_normalizer()
        assert n.normalize("/a/./b/./") == "/a/b"


class TestDotDotComponentBacktrack:
    def test_single_dotdot_backtrack(self):
        n = make_normalizer()
        assert n.normalize("/a/b/../c") == "/a/c"

    def test_multiple_dotdot_backtrack(self):
        n = make_normalizer()
        assert n.normalize("/a/b/c/../../d") == "/a/d"

    def test_dotdot_relative(self):
        n = make_normalizer()
        assert n.normalize("a/b/../c") == "a/c"

    def test_dotdot_at_start_relative(self):
        n = make_normalizer()
        assert n.normalize("../a/b") == "../a/b"

    def test_multiple_dotdot_at_start_relative(self):
        n = make_normalizer()
        assert n.normalize("../../a") == "../../a"

    def test_example_from_spec(self):
        n = make_normalizer()
        assert n.normalize("/a/b/../c/./d//") == "/a/c/d"

    def test_dotdot_back_to_root(self):
        n = make_normalizer()
        assert n.normalize("/a/../") == "/"


class TestConsecutiveSlashMerge:
    def test_double_slash_in_middle(self):
        n = make_normalizer()
        assert n.normalize("/a//b") == "/a/b"

    def test_triple_slash_in_middle(self):
        n = make_normalizer()
        assert n.normalize("/a///b") == "/a/b"

    def test_multiple_groups_of_slashes(self):
        n = make_normalizer()
        assert n.normalize("//a//b////c") == "/a/b/c"

    def test_leading_double_slash(self):
        n = make_normalizer()
        assert n.normalize("//a/b") == "/a/b"

    def test_many_leading_slashes(self):
        n = make_normalizer()
        assert n.normalize("//////a/b") == "/a/b"


class TestTrailingSlashHandling:
    def test_trailing_slash_removed(self):
        n = make_normalizer()
        assert n.normalize("/a/b/") == "/a/b"

    def test_multiple_trailing_slashes(self):
        n = make_normalizer()
        assert n.normalize("/a/b///") == "/a/b"

    def test_root_only(self):
        n = make_normalizer()
        assert n.normalize("/") == "/"

    def test_relative_with_trailing_slash(self):
        n = make_normalizer()
        assert n.normalize("a/b/") == "a/b"


class TestSymlinkResolution:
    def test_single_symlink_resolution(self):
        r = make_resolver(symlinks={"/a": "/x"}, directories={"/x/b"})
        assert r.resolve("/a/b/c") == "/x/b/c"

    def test_symlink_at_middle_level(self):
        r = make_resolver(symlinks={"/a/b": "/m/n"}, directories={"/a", "/m/n"})
        assert r.resolve("/a/b/c/d") == "/m/n/c/d"

    def test_chained_symlinks(self):
        r = make_resolver(
            symlinks={"/a": "/b", "/b": "/c", "/c": "/d"},
            directories={"/d/e"},
        )
        assert r.resolve("/a/e/f") == "/d/e/f"

    def test_relative_symlink_target(self):
        r = make_resolver(
            symlinks={"/a/b": "../x/y"},
            directories={"/a", "/x/y"},
        )
        result = r.resolve("/a/b/c")
        assert result == "/x/y/c"

    def test_symlink_no_resolve_option(self):
        r = make_resolver(symlinks={"/a": "/x"}, directories={"/x/b"})
        assert r.resolve("/a/b/c", resolve_symlinks=False) == "/a/b/c"


class TestCaseInsensitiveEquivalence:
    def test_simple_case_difference_insensitive(self):
        n = make_normalizer(case_sensitive=False)
        assert n.are_equal("/A/b/C", "/a/B/c") is True

    def test_simple_case_difference_sensitive(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("/A/b/C", "/a/B/c") is False

    def test_case_insensitive_with_normalization(self):
        n = make_normalizer(case_sensitive=False)
        assert n.are_equal("/A//B/./C/../D", "/a/b/d") is True

    def test_same_path_sensitive(self):
        n = make_normalizer(case_sensitive=True)
        assert n.are_equal("/a/b/c", "/a/b/c") is True

    def test_same_path_insensitive(self):
        n = make_normalizer(case_sensitive=False)
        assert n.are_equal("/a/b/c", "/a/b/c") is True


class TestResolverEquivalence:
    def test_equivalent_with_symlinks(self):
        r = make_resolver(
            symlinks={"/a": "/x/y"},
            directories={"/x/y/b"},
            case_sensitive=True,
        )
        assert r.are_equivalent("/a/b/c", "/x/y/b/c") is True

    def test_equivalent_case_insensitive(self):
        r = make_resolver(
            symlinks={"/A": "/x/y"},
            directories={"/x/y/b"},
            case_sensitive=False,
        )
        assert r.are_equivalent("/a/b/c", "/X/Y/B/c") is True

    def test_not_equivalent_different_paths(self):
        r = make_resolver(case_sensitive=True)
        assert r.are_equivalent("/a/b", "/a/c") is False
