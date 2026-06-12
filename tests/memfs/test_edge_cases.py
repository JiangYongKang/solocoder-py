import pytest

from solocoder_py.memfs import (
    DirectoryExistsError,
    FileExistsError,
    FileNotFoundError,
    MemoryFileSystem,
    PathNotFoundError,
    PermissionError,
    SymlinkLoopError,
)
from .conftest import make_fs


class TestRootDirectoryOperations:
    def test_create_file_at_root(self):
        fs = make_fs()
        fs.create_file("/root.txt", b"root content")
        assert fs.is_file("/root.txt")
        assert fs.read_file("/root.txt") == b"root content"

    def test_read_file_at_root(self):
        fs = make_fs()
        fs.create_file("/a.txt", b"data")
        assert fs.read_file("/a.txt") == b"data"

    def test_list_root_after_operations(self):
        fs = make_fs()
        fs.create_file("/f1.txt", b"")
        fs.mkdir("/d1")
        fs.create_file("/f2.txt", b"")
        result = fs.list_dir("/")
        assert result == ["d1", "f1.txt", "f2.txt"]

    def test_mkdir_on_root_raises(self):
        fs = make_fs()
        with pytest.raises(DirectoryExistsError):
            fs.mkdir("/")

    def test_remove_root_raises(self):
        fs = make_fs()
        with pytest.raises(Exception):
            fs.rmdir("/")
        with pytest.raises(Exception):
            fs.unlink("/")


class TestEmptyFileOperations:
    def test_create_empty_file(self):
        fs = make_fs()
        fs.create_file("/empty.txt")
        assert fs.read_file("/empty.txt") == b""

    def test_write_empty_content(self):
        fs = make_fs()
        fs.create_file("/test.txt", b"initial")
        fs.write_file("/test.txt", b"")
        assert fs.read_file("/test.txt") == b""

    def test_append_to_empty_file(self):
        fs = make_fs()
        fs.create_file("/empty.txt")
        content = fs.read_file("/empty.txt")
        fs.write_file("/empty.txt", content + b"new content")
        assert fs.read_file("/empty.txt") == b"new content"

    def test_empty_file_size_zero(self):
        fs = make_fs()
        fs.create_file("/zero.txt")
        stat = fs.stat("/zero.txt")
        assert stat["size"] == 0


class TestDeeplyNestedPaths:
    def test_create_deep_nested_directories(self):
        fs = make_fs()
        fs.mkdir_p("/a/b/c/d/e/f/g/h/i/j")
        assert fs.is_dir("/a/b/c/d/e/f/g/h/i/j")

    def test_create_file_in_deep_path(self):
        fs = make_fs()
        fs.mkdir_p("/level1/level2/level3/level4/level5")
        fs.create_file("/level1/level2/level3/level4/level5/deep.txt", b"deep")
        assert fs.read_file("/level1/level2/level3/level4/level5/deep.txt") == b"deep"

    def test_access_deep_nested_path(self):
        fs = make_fs()
        fs.mkdir_p("/a/b/c/d/e")
        fs.create_file("/a/b/c/d/e/f.txt", b"nested")
        assert fs.exists("/a/b/c/d/e/f.txt")
        assert fs.read_file("/a/b/c/d/e/f.txt") == b"nested"

    def test_list_deep_nested_directory(self):
        fs = make_fs()
        fs.mkdir_p("/a/b/c/d")
        fs.create_file("/a/b/c/d/x.txt", b"")
        fs.create_file("/a/b/c/d/y.txt", b"")
        fs.mkdir("/a/b/c/d/z")
        assert fs.list_dir("/a/b/c/d") == ["x.txt", "y.txt", "z"]


class TestZeroPermissions:
    def test_all_permissions_denied_read(self):
        fs = make_fs()
        fs.create_file("/locked.txt", b"secret")
        fs.chmod("/locked.txt", 0o000)
        with pytest.raises(PermissionError):
            fs.read_file("/locked.txt")

    def test_all_permissions_denied_write(self):
        fs = make_fs()
        fs.create_file("/locked.txt", b"secret")
        fs.chmod("/locked.txt", 0o000)
        with pytest.raises(PermissionError):
            fs.write_file("/locked.txt", b"modified")

    def test_all_permissions_denied_list_dir(self):
        fs = make_fs()
        fs.mkdir("/locked_dir")
        fs.create_file("/locked_dir/file.txt", b"")
        fs.chmod("/locked_dir", 0o000)
        with pytest.raises(PermissionError):
            fs.list_dir("/locked_dir")

    def test_owner_bypasses_zero_permissions(self):
        fs = make_fs()
        fs.create_file("/mine.txt", b"my data")
        fs.chmod("/mine.txt", 0o000)
        with pytest.raises(PermissionError):
            fs.read_file("/mine.txt")

    def test_root_can_still_chmod_zero_permissions(self):
        fs = make_fs()
        fs.create_file("/file.txt", b"data")
        fs.chmod("/file.txt", 0o000)
        fs.chmod("/file.txt", 0o644)
        assert fs.get_mode("/file.txt") == 0o644


class TestSymlinkEdgeCases:
    def test_symlink_to_nonexistent_path(self):
        fs = make_fs()
        fs.symlink("/nonexistent/file.txt", "/bad_link")
        assert fs.is_symlink("/bad_link")
        with pytest.raises(PathNotFoundError):
            fs.read_file("/bad_link")

    def test_symlink_to_symlink_to_nonexistent(self):
        fs = make_fs()
        fs.symlink("/nonexistent", "/link1")
        fs.symlink("/link1", "/link2")
        assert fs.is_symlink("/link2")
        with pytest.raises(PathNotFoundError):
            fs.read_file("/link2")

    def test_symlink_target_outside_root_absolute(self):
        fs = make_fs()
        fs.create_file("/target.txt", b"content")
        fs.symlink("/../../etc/passwd", "/escape_try")
        assert fs.readlink("/escape_try") == "/../../etc/passwd"
        with pytest.raises(PathNotFoundError):
            fs.read_file("/escape_try")

    def test_symlink_to_empty_path(self):
        fs = make_fs()
        fs.symlink("", "/empty_target")
        assert fs.readlink("/empty_target") == ""
        with pytest.raises(Exception):
            fs.read_file("/empty_target")

    def test_multiple_chained_symlinks(self):
        fs = make_fs()
        fs.create_file("/base.txt", b"base")
        fs.symlink("/base.txt", "/link1")
        fs.symlink("/link1", "/link2")
        fs.symlink("/link2", "/link3")
        fs.symlink("/link3", "/link4")
        fs.symlink("/link4", "/link5")
        assert fs.read_file("/link5") == b"base"

    def test_symlink_to_root(self):
        fs = make_fs()
        fs.create_file("/root_file.txt", b"at root")
        fs.symlink("/", "/root_link")
        assert "root_file.txt" in fs.list_dir("/root_link")

    def test_symlink_to_itself_directly(self):
        fs = make_fs()
        fs.symlink("/self", "/self")
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/self")


class TestLargeData:
    def test_write_large_content(self):
        fs = make_fs()
        large_data = b"x" * 1000000
        fs.create_file("/large.bin", large_data)
        assert len(fs.read_file("/large.bin")) == 1000000
        assert fs.stat("/large.bin")["size"] == 1000000

    def test_write_binary_data(self):
        fs = make_fs()
        binary_data = bytes(range(256))
        fs.create_file("/binary.bin", binary_data)
        assert fs.read_file("/binary.bin") == binary_data


class TestSpecialPathComponents:
    def test_current_directory_in_path(self):
        fs = make_fs()
        fs.mkdir("/a")
        fs.create_file("/a/./file.txt", b"test")
        assert fs.read_file("/a/file.txt") == b"test"

    def test_multiple_slashes_in_path(self):
        fs = make_fs()
        fs.mkdir_p("/a/b")
        fs.create_file("//a//b///file.txt", b"test")
        assert fs.read_file("/a/b/file.txt") == b"test"

    def test_trailing_slash_on_directory(self):
        fs = make_fs()
        fs.mkdir("/test_dir")
        assert fs.list_dir("/test_dir/") == []

    def test_trailing_slash_on_file_works(self):
        fs = make_fs()
        fs.create_file("/test.txt", b"data")
        assert fs.read_file("/test.txt/") == b"data"


class TestPermissionGroups:
    def test_group_permission_grants_access(self):
        fs = make_fs()
        fs.create_file("/shared.txt", b"shared data")
        fs.chmod("/shared.txt", 0o040)
        fs.set_user("alice", {"users"})
        with pytest.raises(PermissionError):
            fs.read_file("/shared.txt")
        fs.set_user("root")
        fs.chown("/shared.txt", "owner", "devs")
        fs.set_user("alice", {"devs"})
        assert fs.read_file("/shared.txt") == b"shared data"

    def test_other_permission_grants_access(self):
        fs = make_fs()
        fs.create_file("/public.txt", b"public data")
        fs.chmod("/public.txt", 0o004)
        fs.set_user("stranger", set())
        assert fs.read_file("/public.txt") == b"public data"

    def test_owner_permission_overrides_group_and_other(self):
        fs = make_fs()
        fs.create_file("/owner_file.txt", b"owner data")
        fs.chown("/owner_file.txt", "owner", "devs")
        fs.set_user("owner", {"devs"})
        fs.chmod("/owner_file.txt", 0o400)
        assert fs.read_file("/owner_file.txt") == b"owner data"
        fs.chmod("/owner_file.txt", 0o040)
        with pytest.raises(PermissionError):
            fs.read_file("/owner_file.txt")
