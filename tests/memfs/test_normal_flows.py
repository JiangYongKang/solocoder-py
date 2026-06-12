import pytest

from solocoder_py.memfs import (
    DirectoryExistsError,
    FileExistsError,
    MemoryFileSystem,
    PathNotFoundError,
    PermissionError,
)
from .conftest import make_fs


class TestCreateDirectoryAndFile:
    def test_create_single_directory(self):
        fs = make_fs()
        fs.mkdir("/test")
        assert fs.is_dir("/test")
        assert fs.exists("/test")

    def test_create_nested_directory(self):
        fs = make_fs()
        fs.mkdir("/a")
        fs.mkdir("/a/b")
        fs.mkdir("/a/b/c")
        assert fs.is_dir("/a/b/c")
        assert "/a/b/c".split("/")[-1] in fs.list_dir("/a/b")

    def test_mkdir_p_creates_nested_directories(self):
        fs = make_fs()
        fs.mkdir_p("/x/y/z")
        assert fs.is_dir("/x")
        assert fs.is_dir("/x/y")
        assert fs.is_dir("/x/y/z")

    def test_mkdir_p_on_existing_directory(self):
        fs = make_fs()
        fs.mkdir("/existing")
        fs.mkdir_p("/existing")
        assert fs.is_dir("/existing")

    def test_create_file(self):
        fs = make_fs()
        fs.create_file("/test.txt", b"hello world")
        assert fs.is_file("/test.txt")
        assert fs.exists("/test.txt")

    def test_create_file_in_directory(self):
        fs = make_fs()
        fs.mkdir("/docs")
        fs.create_file("/docs/note.txt", b"memo")
        assert fs.is_file("/docs/note.txt")
        assert "note.txt" in fs.list_dir("/docs")


class TestReadWriteFile:
    def test_write_and_read_file(self):
        fs = make_fs()
        fs.create_file("/data.txt", b"initial")
        assert fs.read_file("/data.txt") == b"initial"
        fs.write_file("/data.txt", b"updated")
        assert fs.read_file("/data.txt") == b"updated"

    def test_append_file_content(self):
        fs = make_fs()
        fs.create_file("/log.txt", b"line1\n")
        content = fs.read_file("/log.txt")
        fs.write_file("/log.txt", content + b"line2\n")
        assert fs.read_file("/log.txt") == b"line1\nline2\n"

    def test_file_size_tracking(self):
        fs = make_fs()
        fs.create_file("/size_test.txt", b"12345")
        stat = fs.stat("/size_test.txt")
        assert stat["size"] == 5
        fs.write_file("/size_test.txt", b"1234567890")
        stat = fs.stat("/size_test.txt")
        assert stat["size"] == 10


class TestDirectoryListing:
    def test_list_empty_directory(self):
        fs = make_fs()
        fs.mkdir("/empty")
        assert fs.list_dir("/empty") == []

    def test_list_directory_with_files(self):
        fs = make_fs()
        fs.mkdir("/mixed")
        fs.create_file("/mixed/a.txt", b"a")
        fs.create_file("/mixed/b.txt", b"b")
        fs.mkdir("/mixed/sub")
        result = fs.list_dir("/mixed")
        assert result == ["a.txt", "b.txt", "sub"]

    def test_list_root_directory(self):
        fs = make_fs()
        fs.create_file("/root_file.txt", b"root")
        fs.mkdir("/root_dir")
        result = fs.list_dir("/")
        assert "root_file.txt" in result
        assert "root_dir" in result

    def test_list_returns_sorted(self):
        fs = make_fs()
        fs.mkdir("/sort_test")
        fs.create_file("/sort_test/z.txt", b"")
        fs.create_file("/sort_test/a.txt", b"")
        fs.create_file("/sort_test/m.txt", b"")
        assert fs.list_dir("/sort_test") == ["a.txt", "m.txt", "z.txt"]


class TestSymlinkResolution:
    def test_symlink_to_file(self):
        fs = make_fs()
        fs.create_file("/target.txt", b"target content")
        fs.symlink("/target.txt", "/link.txt")
        assert fs.is_symlink("/link.txt")
        assert fs.read_file("/link.txt") == b"target content"

    def test_symlink_to_directory(self):
        fs = make_fs()
        fs.mkdir("/target_dir")
        fs.create_file("/target_dir/file.txt", b"inside")
        fs.symlink("/target_dir", "/link_dir")
        assert fs.is_symlink("/link_dir")
        assert fs.list_dir("/link_dir") == ["file.txt"]

    def test_chained_symlinks(self):
        fs = make_fs()
        fs.create_file("/final.txt", b"final data")
        fs.symlink("/final.txt", "/link1.txt")
        fs.symlink("/link1.txt", "/link2.txt")
        fs.symlink("/link2.txt", "/link3.txt")
        assert fs.read_file("/link3.txt") == b"final data"

    def test_relative_symlink(self):
        fs = make_fs()
        fs.mkdir("/a")
        fs.create_file("/a/target.txt", b"relative test")
        fs.symlink("target.txt", "/a/link.txt")
        assert fs.read_file("/a/link.txt") == b"relative test"

    def test_readlink_returns_target(self):
        fs = make_fs()
        fs.symlink("/some/path", "/mylink")
        assert fs.readlink("/mylink") == "/some/path"

    def test_write_through_symlink(self):
        fs = make_fs()
        fs.create_file("/orig.txt", b"original")
        fs.symlink("/orig.txt", "/alias.txt")
        fs.write_file("/alias.txt", b"modified via link")
        assert fs.read_file("/orig.txt") == b"modified via link"


class TestPermissionModification:
    def test_chmod_changes_permissions(self):
        fs = make_fs()
        fs.create_file("/chmod_test.txt", b"data")
        original_mode = fs.get_mode("/chmod_test.txt")
        fs.chmod("/chmod_test.txt", 0o600)
        assert fs.get_mode("/chmod_test.txt") == 0o600
        assert fs.get_mode("/chmod_test.txt") != original_mode

    def test_chmod_affects_access(self):
        fs = make_fs()
        fs.create_file("/secure.txt", b"secret")
        fs.chmod("/secure.txt", 0o600)
        fs.set_user("alice", {"users"})
        with pytest.raises(PermissionError):
            fs.read_file("/secure.txt")
        fs.set_user("root")
        fs.chmod("/secure.txt", 0o644)
        fs.set_user("alice", {"users"})
        assert fs.read_file("/secure.txt") == b"secret"

    def test_owner_can_chmod(self):
        fs = make_fs()
        fs.create_file("/myfile.txt", b"my data")
        fs.chown("/myfile.txt", "bob", "users")
        fs.set_user("bob", {"users"})
        fs.chmod("/myfile.txt", 0o600)
        assert fs.get_mode("/myfile.txt") == 0o600

    def test_chown_changes_owner(self):
        fs = make_fs()
        fs.create_file("/owned.txt", b"")
        fs.chown("/owned.txt", "newowner", "newgroup")
        assert fs.get_owner("/owned.txt") == "newowner"
        assert fs.get_group("/owned.txt") == "newgroup"


class TestBasicOperations:
    def test_exists_on_nonexistent_path(self):
        fs = make_fs()
        assert fs.exists("/nonexistent") is False
        assert fs.is_file("/nonexistent") is False
        assert fs.is_dir("/nonexistent") is False

    def test_unlink_file(self):
        fs = make_fs()
        fs.create_file("/todelete.txt", b"")
        assert fs.exists("/todelete.txt")
        fs.unlink("/todelete.txt")
        assert fs.exists("/todelete.txt") is False

    def test_rmdir_empty_directory(self):
        fs = make_fs()
        fs.mkdir("/toremove")
        assert fs.exists("/toremove")
        fs.rmdir("/toremove")
        assert fs.exists("/toremove") is False

    def test_remove_file(self):
        fs = make_fs()
        fs.create_file("/rmfile.txt", b"")
        fs.remove("/rmfile.txt")
        assert fs.exists("/rmfile.txt") is False

    def test_remove_empty_directory(self):
        fs = make_fs()
        fs.mkdir("/rmdir")
        fs.remove("/rmdir")
        assert fs.exists("/rmdir") is False

    def test_stat_file(self):
        fs = make_fs()
        fs.create_file("/stat_test.txt", b"content")
        stat = fs.stat("/stat_test.txt")
        assert stat["name"] == "stat_test.txt"
        assert stat["type"] == "file"
        assert stat["owner"] == "root"
        assert stat["group"] == "root"
        assert stat["mode"] == 0o644
        assert stat["size"] == 7

    def test_stat_directory(self):
        fs = make_fs()
        fs.mkdir("/stat_dir")
        stat = fs.stat("/stat_dir")
        assert stat["name"] == "stat_dir"
        assert stat["type"] == "directory"
        assert stat["size"] == 0
