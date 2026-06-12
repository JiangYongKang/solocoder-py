import pytest

from solocoder_py.memfs import (
    DirectoryExistsError,
    DirectoryNotEmptyError,
    DirectoryNotFoundError,
    FileExistsError,
    IsADirectoryError,
    MemoryFileSystem,
    NotADirectoryError,
    OperationNotPermittedError,
    PathNotFoundError,
    PermissionError,
    SymlinkLoopError,
)
from .conftest import make_fs


class TestPathTraversalProtection:
    def test_dotdot_stays_within_root(self):
        fs = make_fs()
        fs.create_file("/safe.txt", b"safe")
        result = fs._normalize_path("/a/b/../../etc/passwd")
        assert result == "/etc/passwd"
        assert not result.startswith("/../")
        assert result.startswith("/")

    def test_dotdot_at_root_does_nothing(self):
        fs = make_fs()
        assert fs._normalize_path("/../") == "/"
        assert fs._normalize_path("/../../") == "/"
        assert fs._normalize_path("/a/../..") == "/"

    def test_dotdot_in_middle_of_path(self):
        fs = make_fs()
        assert fs._normalize_path("/a/./b/../c/") == "/a/c"

    def test_traversal_attack_prevented(self):
        fs = make_fs()
        fs.mkdir("/etc")
        fs.create_file("/etc/passwd", b"root:x:0:0:root:/root:/bin/bash")
        result = fs._normalize_path("/a/b/../../etc/passwd")
        assert result == "/etc/passwd"
        assert not result.startswith("/../")
        assert result.startswith("/")
        content = fs.read_file("/a/b/../../etc/passwd")
        assert content == b"root:x:0:0:root:/root:/bin/bash"

    def test_symlink_target_with_traversal(self):
        fs = make_fs()
        fs.mkdir("/real")
        fs.create_file("/real/file.txt", b"real content")
        fs.symlink("/../real/file.txt", "/link")
        normalized = fs._normalize_path(fs.readlink("/link"))
        assert normalized == "/real/file.txt"
        assert not normalized.startswith("/../")
        content = fs.read_file("/link")
        assert content == b"real content"

    def test_relative_path_with_dotdot(self):
        fs = make_fs()
        fs.mkdir("/a")
        fs.mkdir("/b")
        fs.create_file("/b/file.txt", b"data")
        result = fs._normalize_path("../b/file.txt", "/a")
        assert result == "/b/file.txt"


class TestDotDotAtRoot:
    def test_root_dotdot_resolves_to_root(self):
        fs = make_fs()
        assert fs._normalize_path("/..") == "/"
        assert fs._normalize_path("/../..") == "/"

    def test_cannot_escape_root_via_dotdot(self):
        fs = make_fs()
        path = fs._normalize_path("/../../../../../etc/shadow")
        assert path == "/etc/shadow"
        with pytest.raises(PathNotFoundError):
            fs.read_file(path)

    def test_mixed_dot_and_dotdot(self):
        fs = make_fs()
        assert fs._normalize_path("/./../a/./b/..") == "/a"


class TestSymlinkLoopDetection:
    def test_direct_symlink_loop(self):
        fs = make_fs()
        fs.symlink("/a", "/b")
        fs.symlink("/b", "/a")
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/a")

    def test_indirect_symlink_loop(self):
        fs = make_fs()
        fs.symlink("/b", "/a")
        fs.symlink("/c", "/b")
        fs.symlink("/a", "/c")
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/a")

    def test_self_referential_symlink(self):
        fs = make_fs()
        fs.symlink("/self", "/self")
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/self")

    def test_long_chain_loop(self):
        fs = make_fs()
        fs.symlink("/link1", "/link0")
        fs.symlink("/link2", "/link1")
        fs.symlink("/link3", "/link2")
        fs.symlink("/link4", "/link3")
        fs.symlink("/link0", "/link4")
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/link0")

    def test_max_symlink_depth(self):
        fs = make_fs()
        fs.create_file("/target.txt", b"target")
        prev = "/target.txt"
        for i in range(40):
            new_link = f"/link{i}"
            fs.symlink(prev, new_link)
            prev = new_link
        with pytest.raises(SymlinkLoopError):
            fs.read_file("/link39")


class TestPermissionDenied:
    def test_read_without_permission(self):
        fs = make_fs()
        fs.create_file("/no_read.txt", b"secret")
        fs.chmod("/no_read.txt", 0o000)
        with pytest.raises(PermissionError):
            fs.read_file("/no_read.txt")

    def test_write_without_permission(self):
        fs = make_fs()
        fs.create_file("/no_write.txt", b"data")
        fs.chmod("/no_write.txt", 0o444)
        with pytest.raises(PermissionError):
            fs.write_file("/no_write.txt", b"modified")

    def test_list_dir_without_permission(self):
        fs = make_fs()
        fs.mkdir("/no_list")
        fs.chmod("/no_list", 0o200)
        with pytest.raises(PermissionError):
            fs.list_dir("/no_list")

    def test_traverse_directory_without_execute_permission(self):
        fs = make_fs()
        fs.mkdir("/no_traverse")
        fs.create_file("/no_traverse/file.txt", b"data")
        fs.chmod("/no_traverse", 0o400)
        with pytest.raises(PermissionError):
            fs.read_file("/no_traverse/file.txt")

    def test_create_file_without_write_permission(self):
        fs = make_fs()
        fs.mkdir("/no_write_dir")
        fs.chmod("/no_write_dir", 0o555)
        with pytest.raises(PermissionError):
            fs.create_file("/no_write_dir/file.txt", b"data")

    def test_non_owner_cannot_chmod(self):
        fs = make_fs()
        fs.create_file("/not_mine.txt", b"data")
        fs.set_user("bob", {"users"})
        with pytest.raises(OperationNotPermittedError):
            fs.chmod("/not_mine.txt", 0o777)

    def test_non_root_cannot_chown(self):
        fs = make_fs()
        fs.create_file("/bob_file.txt", b"")
        fs.chown("/bob_file.txt", "bob", "users")
        fs.set_user("bob", {"users"})
        with pytest.raises(OperationNotPermittedError):
            fs.chown("/bob_file.txt", "alice", "users")


class TestDirectoryNotEmpty:
    def test_rmdir_non_empty_directory(self):
        fs = make_fs()
        fs.mkdir("/not_empty")
        fs.create_file("/not_empty/file.txt", b"data")
        with pytest.raises(DirectoryNotEmptyError):
            fs.rmdir("/not_empty")

    def test_rmdir_with_subdirectory(self):
        fs = make_fs()
        fs.mkdir("/parent")
        fs.mkdir("/parent/child")
        with pytest.raises(DirectoryNotEmptyError):
            fs.rmdir("/parent")

    def test_remove_non_empty_directory(self):
        fs = make_fs()
        fs.mkdir("/not_empty")
        fs.create_file("/not_empty/file.txt", b"data")
        with pytest.raises(DirectoryNotEmptyError):
            fs.remove("/not_empty")

    def test_rmdir_empty_after_removing_contents(self):
        fs = make_fs()
        fs.mkdir("/dir")
        fs.create_file("/dir/file.txt", b"data")
        fs.unlink("/dir/file.txt")
        fs.rmdir("/dir")
        assert not fs.exists("/dir")


class TestPathNotFound:
    def test_read_nonexistent_file(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.read_file("/nonexistent.txt")

    def test_write_nonexistent_file(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.write_file("/nonexistent.txt", b"data")

    def test_list_nonexistent_directory(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.list_dir("/nonexistent")

    def test_chmod_nonexistent_path(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.chmod("/nonexistent", 0o644)

    def test_chown_nonexistent_path(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.chown("/nonexistent", "user", "group")

    def test_stat_nonexistent_path(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.stat("/nonexistent")

    def test_mkdir_in_nonexistent_parent(self):
        fs = make_fs()
        with pytest.raises(DirectoryNotFoundError):
            fs.mkdir("/nonexistent/subdir")

    def test_create_file_in_nonexistent_parent(self):
        fs = make_fs()
        with pytest.raises(PathNotFoundError):
            fs.create_file("/nonexistent/file.txt", b"data")


class TestDuplicateCreation:
    def test_create_existing_file(self):
        fs = make_fs()
        fs.create_file("/exists.txt", b"original")
        with pytest.raises(FileExistsError):
            fs.create_file("/exists.txt", b"new")

    def test_create_existing_directory(self):
        fs = make_fs()
        fs.mkdir("/exists")
        with pytest.raises(DirectoryExistsError):
            fs.mkdir("/exists")

    def test_symlink_to_existing_path(self):
        fs = make_fs()
        fs.create_file("/target.txt", b"data")
        with pytest.raises(FileExistsError):
            fs.symlink("/other", "/target.txt")

    def test_mkdir_p_on_existing_file_raises(self):
        fs = make_fs()
        fs.mkdir("/path")
        fs.create_file("/path/file.txt", b"data")
        with pytest.raises(FileExistsError):
            fs.mkdir_p("/path/file.txt")


class TestTypeMismatchErrors:
    def test_read_directory_as_file(self):
        fs = make_fs()
        fs.mkdir("/dir")
        with pytest.raises(IsADirectoryError):
            fs.read_file("/dir")

    def test_write_directory_as_file(self):
        fs = make_fs()
        fs.mkdir("/dir")
        with pytest.raises(IsADirectoryError):
            fs.write_file("/dir", b"data")

    def test_list_file_as_directory(self):
        fs = make_fs()
        fs.create_file("/file.txt", b"data")
        with pytest.raises(NotADirectoryError):
            fs.list_dir("/file.txt")

    def test_rmdir_on_file(self):
        fs = make_fs()
        fs.create_file("/file.txt", b"data")
        with pytest.raises(NotADirectoryError):
            fs.rmdir("/file.txt")

    def test_unlink_on_directory(self):
        fs = make_fs()
        fs.mkdir("/dir")
        with pytest.raises(IsADirectoryError):
            fs.unlink("/dir")

    def test_readlink_on_non_symlink(self):
        fs = make_fs()
        fs.create_file("/file.txt", b"data")
        with pytest.raises(OperationNotPermittedError):
            fs.readlink("/file.txt")

    def test_create_file_on_existing_directory(self):
        fs = make_fs()
        fs.mkdir("/mypath")
        with pytest.raises(FileExistsError):
            fs.create_file("/mypath", b"data")

    def test_mkdir_on_existing_file(self):
        fs = make_fs()
        fs.create_file("/myfile", b"data")
        with pytest.raises(DirectoryExistsError):
            fs.mkdir("/myfile")


class TestInvalidOperations:
    def test_remove_root_directory(self):
        fs = make_fs()
        with pytest.raises(OperationNotPermittedError):
            fs.rmdir("/")

    def test_unlink_root(self):
        fs = make_fs()
        with pytest.raises(OperationNotPermittedError):
            fs.unlink("/")

    def test_chmod_invalid_mode_high(self):
        fs = make_fs()
        fs.create_file("/test.txt", b"")
        with pytest.raises(ValueError):
            fs.chmod("/test.txt", 0o1000)

    def test_chmod_invalid_mode_negative(self):
        fs = make_fs()
        fs.create_file("/test.txt", b"")
        with pytest.raises(ValueError):
            fs.chmod("/test.txt", -1)


class TestSymlinkThroughDirectory:
    def test_symlink_directory_then_file(self):
        fs = make_fs()
        fs.mkdir("/real_dir")
        fs.create_file("/real_dir/file.txt", b"data")
        fs.symlink("/real_dir", "/link_dir")
        assert fs.read_file("/link_dir/file.txt") == b"data"

    def test_symlink_loop_through_directory(self):
        fs = make_fs()
        fs.mkdir("/a")
        fs.symlink("/a", "/a/b")
        with pytest.raises(PathNotFoundError):
            fs.read_file("/a/b/c")


class TestPathComponentSymlink:
    def test_symlink_in_path_components(self):
        fs = make_fs()
        fs.mkdir("/real_dir")
        fs.create_file("/real_dir/file.txt", b"content")
        fs.symlink("/real_dir", "/link")
        result = fs.list_dir("/link/")
        assert "file.txt" in result
