import pytest

from solocoder_py.pathnorm import PathNormalizer
from .conftest import make_normalizer, make_resolver


class TestRootDotDotHandling:
    def test_dotdot_at_root_absolute(self):
        n = make_normalizer()
        assert n.normalize("/..") == "/"

    def test_dotdot_beyond_root_absolute(self):
        n = make_normalizer()
        assert n.normalize("/a/../../..") == "/"

    def test_many_dotdots_absolute(self):
        n = make_normalizer()
        assert n.normalize("/a/b/../../../../c") == "/c"

    def test_dotdot_at_start_relative_preserved(self):
        n = make_normalizer()
        assert n.normalize("../a/../b") == "../b"

    def test_dotdot_only_relative(self):
        n = make_normalizer()
        assert n.normalize("../../..") == "../../.."

    def test_mixed_dotdots_relative(self):
        n = make_normalizer()
        assert n.normalize("a/../../b") == "../b"


class TestEmptyPathHandling:
    def test_empty_string(self):
        n = make_normalizer()
        assert n.normalize("") == "."

    def test_empty_vs_dot_not_equivalent_to_root(self):
        n = make_normalizer()
        assert n.are_equal("", ".") is True
        assert n.are_equal("", "/") is False

    def test_dot_vs_empty(self):
        n = make_normalizer()
        assert n.normalize(".") == "."


class TestSlashOnlyPaths:
    def test_single_slash(self):
        n = make_normalizer()
        assert n.normalize("/") == "/"

    def test_double_slash(self):
        n = make_normalizer()
        assert n.normalize("//") == "/"

    def test_many_slashes(self):
        n = make_normalizer()
        assert n.normalize("////////////") == "/"


class TestExcessiveDotDot:
    def test_massive_dotdot_absolute(self):
        n = make_normalizer()
        many_dotdots = "/" + "/".join([".."] * 100)
        assert n.normalize(many_dotdots) == "/"

    def test_massive_dotdot_relative(self):
        n = make_normalizer()
        many_dotdots = "/".join([".."] * 100)
        assert n.normalize(many_dotdots) == "/".join([".."] * 100)

    def test_dotdot_after_every_component_absolute(self):
        n = make_normalizer()
        path = "/a/../b/../c/../d/../e"
        assert n.normalize(path) == "/e"


class TestLongPathNormalization:
    def test_long_path_with_many_components(self):
        n = make_normalizer()
        components = [f"dir{i}" for i in range(100)]
        path = "/" + "/".join(components)
        result = n.normalize(path)
        assert result == path
        assert len(result.split("/")) == 101

    def test_long_path_with_dots(self):
        n = make_normalizer()
        parts = []
        for i in range(50):
            parts.append(f"dir{i}")
            parts.append(".")
            parts.append("..")
        path = "/" + "/".join(parts)
        result = n.normalize(path)
        assert result == "/"

    def test_very_long_component_names(self):
        n = make_normalizer()
        long_name = "a" * 200
        path = f"/{long_name}/{long_name}"
        result = n.normalize(path)
        assert result == path


class TestIdempotency:
    def test_normalize_twice_same_result(self):
        n = make_normalizer()
        paths = [
            "/a/b/../c/./d//",
            "a/./b/../c",
            "/../../a/b",
            "//a//b////c//",
            "",
            ".",
            "/",
            "../a/../b/../c",
        ]
        for p in paths:
            once = n.normalize(p)
            twice = n.normalize(once)
            assert once == twice, f"Failed idempotency for {p!r}: {once!r} vs {twice!r}"

    def test_normalize_three_times_same(self):
        n = make_normalizer()
        path = "/a//b/../../c/./d///e/"
        r1 = n.normalize(path)
        r2 = n.normalize(r1)
        r3 = n.normalize(r2)
        assert r1 == r2 == r3


class TestComplexPaths:
    def test_complex_mixed_path_1(self):
        n = make_normalizer()
        assert n.normalize("/a//b/.././c//d/../../e/") == "/a/e"

    def test_complex_mixed_path_2(self):
        n = make_normalizer()
        assert n.normalize("././a/./b/../c/./d/../e/././f") == "a/c/e/f"

    def test_symlink_with_dotdot(self):
        r = make_resolver(
            symlinks={"/a/b": "/x/y/../z"},
            directories={"/x/z"},
        )
        result = r.resolve("/a/b/c")
        assert result == "/x/z/c"

    def test_symlink_with_many_slashes(self):
        r = make_resolver(
            symlinks={"/a": "/x"},
            directories={"/x/b"},
        )
        assert r.resolve("///a//b///c") == "/x/b/c"


class TestResolverEdgeCases:
    def test_resolve_root(self):
        r = make_resolver()
        assert r.resolve("/") == "/"

    def test_resolve_dot(self):
        r = make_resolver()
        assert r.resolve(".") == "."

    def test_resolve_empty(self):
        r = make_resolver()
        assert r.resolve("") == "."

    def test_resolve_symlink_to_root(self):
        r = make_resolver(
            symlinks={"/a": "/"},
            directories={"/"},
        )
        assert r.resolve("/a/b/c") == "/b/c"

    def test_resolver_exists(self):
        r = make_resolver(
            directories={"/a/b/c"},
        )
        assert r.exists("/a/b/c") is True
        assert r.exists("/x/y/z") is False
