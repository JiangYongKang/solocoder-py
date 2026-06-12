from __future__ import annotations

import time

import pytest

from solocoder_py.dirtreediff import (
    DiffConfig,
    DiffOperationType,
    DirTreeDiffEngine,
    DirectoryTreeSnapshot,
    NodeType,
)

from .conftest import compute_hash


class TestIdenticalSnapshots:
    def test_both_empty_snapshots_return_empty(self, empty_snapshot):
        engine = DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=empty_snapshot)
        ops = engine.diff()
        assert len(ops) == 0
        assert engine.summary()["total"] == 0

    def test_identical_non_empty_snapshots_return_empty(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        for snap in [snapshot_a, snapshot_b]:
            snap.add_node_from_dict({
                "path": "src",
                "type": NodeType.DIRECTORY.value,
                "mtime": 1000.0,
            })
            snap.add_node_from_dict({
                "path": "src/main.py",
                "type": NodeType.FILE.value,
                "size": 100,
                "mtime": 1000.0,
                "content_hash": compute_hash("content"),
            })
            snap.add_node_from_dict({
                "path": "readme.md",
                "type": NodeType.FILE.value,
                "size": 50,
                "mtime": 1000.0,
                "content_hash": compute_hash("# readme"),
            })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()
        assert len(ops) == 0


class TestEmptyVsNonEmpty:
    def test_empty_to_non_empty_all_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "dir1",
            "type": NodeType.DIRECTORY.value,
            "mtime": 2000.0,
        })
        snapshot_b.add_node_from_dict({
            "path": "dir1/file1.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 2000.0,
            "content_hash": compute_hash("f1"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file2.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 2000.0,
            "content_hash": compute_hash("f2"),
        })

        engine = DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 3
        assert all(op.operation_type == DiffOperationType.CREATE for op in ops)
        summary = engine.summary()
        assert summary["create"] == 3
        assert summary["delete"] == 0
        assert summary["modify"] == 0

    def test_non_empty_to_empty_all_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "dir1",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
        })
        snapshot_a.add_node_from_dict({
            "path": "dir1/file1.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("f1"),
        })
        snapshot_a.add_node_from_dict({
            "path": "file2.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 1000.0,
            "content_hash": compute_hash("f2"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=empty_snapshot)
        ops = engine.diff()

        assert len(ops) == 3
        assert all(op.operation_type == DiffOperationType.DELETE for op in ops)
        summary = engine.summary()
        assert summary["create"] == 0
        assert summary["delete"] == 3
        assert summary["modify"] == 0


class TestPerformanceWithManyFiles:
    def test_hundreds_of_files_compare_in_acceptable_time(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        num_files = 500
        for i in range(num_files):
            path = f"dir/file_{i:04d}.txt"
            content_old = f"content_{i}_old"
            content_new = f"content_{i}_new" if i % 2 == 0 else content_old

            snapshot_a.add_node_from_dict({
                "path": path,
                "type": NodeType.FILE.value,
                "size": len(content_old),
                "mtime": 1000.0,
                "content_hash": compute_hash(content_old),
            })
            snapshot_b.add_node_from_dict({
                "path": path,
                "type": NodeType.FILE.value,
                "size": len(content_new),
                "mtime": 2000.0 if i % 2 == 0 else 1000.0,
                "content_hash": compute_hash(content_new),
            })

        for i in range(num_files, num_files + 50):
            path = f"dir/new_file_{i:04d}.txt"
            snapshot_b.add_node_from_dict({
                "path": path,
                "type": NodeType.FILE.value,
                "size": 10,
                "mtime": 2000.0,
                "content_hash": compute_hash(f"new_{i}"),
            })

        for i in range(num_files - 50, num_files):
            path = f"dir/deleted_file_{i:04d}.txt"
            snapshot_a.add_node_from_dict({
                "path": path,
                "type": NodeType.FILE.value,
                "size": 10,
                "mtime": 1000.0,
                "content_hash": compute_hash(f"del_{i}"),
            })

        start = time.time()
        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()
        elapsed = time.time() - start

        assert elapsed < 5.0
        summary = engine.summary()
        assert summary["modify"] == 250
        assert summary["create"] == 50
        assert summary["delete"] == 50
        assert summary["total"] == 350


class TestMtimeOnlyChange:
    def test_file_mtime_only_change_is_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        content = "unchanged content"

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 2000.0,
            "content_hash": compute_hash(content),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "mtime" in changed_fields
        assert "content_hash" not in changed_fields
        assert "size" not in changed_fields

    def test_file_mtime_only_not_modified_when_config_excludes_mtime(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        content = "unchanged content"

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 2000.0,
            "content_hash": compute_hash(content),
        })

        config = DiffConfig(include_mtime=False)
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()

        assert len(ops) == 0


class TestDirectoryPermissionsChange:
    def test_directory_only_permissions_change_is_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "mydir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
            "permissions": 0o755,
        })
        snapshot_b.add_node_from_dict({
            "path": "mydir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
            "permissions": 0o700,
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "permissions" in changed_fields
        assert "mtime" not in changed_fields

    def test_directory_permissions_not_checked_when_config_excludes(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "mydir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
            "permissions": 0o755,
        })
        snapshot_b.add_node_from_dict({
            "path": "mydir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
            "permissions": 0o700,
        })

        config = DiffConfig(include_permissions=False)
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()

        assert len(ops) == 0


class TestCaseInsensitivePaths:
    def test_case_sensitive_paths_different_paths(self):
        snapshot_a = DirectoryTreeSnapshot(
            root_path="/", timestamp=1000.0, case_sensitive=True
        )
        snapshot_b = DirectoryTreeSnapshot(
            root_path="/", timestamp=2000.0, case_sensitive=True
        )

        snapshot_a.add_node_from_dict({
            "path": "File.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("f1"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 2000.0,
            "content_hash": compute_hash("f2"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 2
        op_types = {op.operation_type for op in ops}
        assert DiffOperationType.CREATE in op_types
        assert DiffOperationType.DELETE in op_types

    def test_case_insensitive_paths_same_file_modify(self):
        snapshot_a = DirectoryTreeSnapshot(
            root_path="/", timestamp=1000.0, case_sensitive=False
        )
        snapshot_b = DirectoryTreeSnapshot(
            root_path="/", timestamp=2000.0, case_sensitive=False
        )

        snapshot_a.add_node_from_dict({
            "path": "File.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("f1"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 2000.0,
            "content_hash": compute_hash("f2"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY


class TestPathNormalization:
    def test_leading_dot_slash_is_normalized(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "./dir/file.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "dir/file.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()
        assert len(ops) == 0

    def test_backslash_converted_to_forward_slash(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "dir\\file.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "dir/file.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()
        assert len(ops) == 0


class TestSnapshotContainerMethods:
    def test_snapshot_len(self, simple_snapshot_a):
        assert len(simple_snapshot_a) == 4

    def test_snapshot_contains(self, simple_snapshot_a):
        assert "src/main.py" in simple_snapshot_a
        assert "nonexistent.txt" not in simple_snapshot_a

    def test_snapshot_iteration(self, simple_snapshot_a):
        paths = {node.path for node in simple_snapshot_a}
        assert "src" in paths
        assert "src/main.py" in paths
        assert "docs" in paths
        assert "docs/readme.md" in paths

    def test_snapshot_all_paths_sorted(self, simple_snapshot_a):
        paths = simple_snapshot_a.all_paths()
        assert paths == sorted(paths)

    def test_snapshot_get_node(self, simple_snapshot_a):
        node = simple_snapshot_a.get_node("src/main.py")
        assert node is not None
        assert node.path == "src/main.py"

    def test_snapshot_get_node_missing(self, simple_snapshot_a):
        assert simple_snapshot_a.get_node("missing.txt") is None

    def test_snapshot_all_nodes_returns_copy(self, simple_snapshot_a):
        nodes = simple_snapshot_a.all_nodes()
        assert "src/main.py" in nodes
        nodes["new"] = "test"
        assert simple_snapshot_a.get_node("new") is None


class TestHashAlgorithmMismatchHandling:
    def test_same_content_different_hash_algorithms_with_resolver(self):
        content = "same content"
        sha256_hash = compute_hash(content, "sha256")
        md5_hash = compute_hash(content, "md5")

        def resolver(hash_a, algo_a, hash_b, algo_b):
            if algo_a == "sha256" and algo_b == "md5":
                if hash_a == sha256_hash and hash_b == md5_hash:
                    return hash_a
            if algo_a == "md5" and algo_b == "sha256":
                if hash_a == md5_hash and hash_b == sha256_hash:
                    return hash_b
            return None

        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": sha256_hash,
            "hash_algorithm": "sha256",
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 2000.0,
            "content_hash": md5_hash,
            "hash_algorithm": "md5",
        })

        config = DiffConfig(hash_resolver=resolver)
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "content_hash" not in changed_fields
        assert "mtime" in changed_fields

    def test_same_content_different_hash_algorithms_allow_mismatch(self):
        content = "same content"
        sha256_hash = compute_hash(content, "sha256")
        md5_hash = compute_hash(content, "md5")

        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": sha256_hash,
            "hash_algorithm": "sha256",
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": md5_hash,
            "hash_algorithm": "md5",
        })

        config = DiffConfig(allow_hash_algorithm_mismatch=True)
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 0
