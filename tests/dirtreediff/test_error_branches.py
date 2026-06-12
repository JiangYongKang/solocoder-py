from __future__ import annotations

import pytest

from solocoder_py.dirtreediff import (
    CaseInsensitivePathConflictError,
    DiffConfig,
    DiffOperationType,
    DirTreeDiffEngine,
    DirTreeDiffError,
    DirectoryTreeSnapshot,
    DuplicatePathError,
    FileNode,
    HashAlgorithmMismatchError,
    InvalidNodeTypeError,
    MissingRequiredFieldError,
    NodeType,
    SymlinkNotSupportedError,
    SymlinkNode,
)

from .conftest import compute_hash


class TestDuplicatePathInSnapshot:
    def test_add_duplicate_path_from_dict_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("content"),
        })

        with pytest.raises(DuplicatePathError, match="Duplicate path"):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "type": NodeType.FILE.value,
                "size": 200,
                "mtime": 2000.0,
                "content_hash": compute_hash("other"),
            })

    def test_add_duplicate_path_from_node_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        node = FileNode(
            path="file.txt",
            size=100,
            mtime=1000.0,
            content_hash=compute_hash("content"),
        )
        snapshot.add_node(node)

        with pytest.raises(DuplicatePathError):
            snapshot.add_node(node)


class TestMissingRequiredFields:
    def test_file_missing_path_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError, match="Missing required fields"):
            snapshot.add_node_from_dict({
                "type": NodeType.FILE.value,
                "size": 100,
                "mtime": 1000.0,
                "content_hash": compute_hash("content"),
            })

    def test_file_missing_type_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "size": 100,
                "mtime": 1000.0,
                "content_hash": compute_hash("content"),
            })

    def test_file_missing_size_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError, match="File node missing required"):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "type": NodeType.FILE.value,
                "mtime": 1000.0,
                "content_hash": compute_hash("content"),
            })

    def test_file_missing_content_hash_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "type": NodeType.FILE.value,
                "size": 100,
                "mtime": 1000.0,
            })

    def test_directory_missing_mtime_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError, match="Directory node missing"):
            snapshot.add_node_from_dict({
                "path": "mydir",
                "type": NodeType.DIRECTORY.value,
            })

    def test_symlink_missing_target_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(MissingRequiredFieldError, match="Symlink node missing"):
            snapshot.add_node_from_dict({
                "path": "link",
                "type": NodeType.SYMLINK.value,
                "mtime": 1000.0,
            })


class TestInvalidNodeType:
    def test_invalid_node_type_string_raises(self):
        snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        with pytest.raises(InvalidNodeTypeError, match="Invalid node type"):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "type": "unknown_type",
                "size": 100,
                "mtime": 1000.0,
                "content_hash": compute_hash("content"),
            })

    def test_file_node_wrong_type_in_constructor(self):
        with pytest.raises(InvalidNodeTypeError):
            FileNode(
                path="file.txt",
                size=100,
                mtime=1000.0,
                content_hash=compute_hash("content"),
                type=NodeType.DIRECTORY,
            )

    def test_file_node_negative_size_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            FileNode(
                path="file.txt",
                size=-1,
                mtime=1000.0,
                content_hash=compute_hash("content"),
            )

    def test_file_node_empty_content_hash_raises(self):
        with pytest.raises(MissingRequiredFieldError, match="content_hash cannot be empty"):
            FileNode(
                path="file.txt",
                size=100,
                mtime=1000.0,
                content_hash="",
            )


class TestSymlinkHandling:
    def test_symlink_error_strategy_raises_on_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "link",
            "type": NodeType.SYMLINK.value,
            "target": "/somewhere",
            "mtime": 2000.0,
        })

        config = DiffConfig(symlink_strategy="error")
        engine = DirTreeDiffEngine(
            snapshot_a=empty_snapshot, snapshot_b=snapshot_b, config=config
        )
        with pytest.raises(SymlinkNotSupportedError, match="Symlinks are not supported"):
            engine.diff()

    def test_symlink_error_strategy_raises_on_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "link",
            "type": NodeType.SYMLINK.value,
            "target": "/somewhere",
            "mtime": 1000.0,
        })

        config = DiffConfig(symlink_strategy="error")
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=empty_snapshot, config=config
        )
        with pytest.raises(SymlinkNotSupportedError):
            engine.diff()

    def test_symlink_ignore_strategy_skips_all(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "old_link",
            "type": NodeType.SYMLINK.value,
            "target": "/old",
            "mtime": 1000.0,
        })
        snapshot_b.add_node_from_dict({
            "path": "new_link",
            "type": NodeType.SYMLINK.value,
            "target": "/new",
            "mtime": 2000.0,
        })

        config = DiffConfig(symlink_strategy="ignore")
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 0

    def test_symlink_detect_strategy_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "link",
            "type": NodeType.SYMLINK.value,
            "target": "/somewhere",
            "mtime": 2000.0,
        })

        config = DiffConfig(symlink_strategy="detect")
        engine = DirTreeDiffEngine(
            snapshot_a=empty_snapshot, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 1
        assert ops[0].node_type == NodeType.SYMLINK

    def test_symlink_detect_strategy_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node(SymlinkNode(
            path="link",
            target="/old",
            mtime=1000.0,
        ))
        snapshot_b.add_node(SymlinkNode(
            path="link",
            target="/new",
            mtime=2000.0,
        ))

        config = DiffConfig(symlink_strategy="detect")
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 1
        from solocoder_py.dirtreediff import DiffOperationType
        assert ops[0].operation_type == DiffOperationType.MODIFY

    def test_symlink_follow_strategy_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "link",
            "type": NodeType.SYMLINK.value,
            "target": "/somewhere",
            "mtime": 2000.0,
        })

        config = DiffConfig(symlink_strategy="follow")
        engine = DirTreeDiffEngine(
            snapshot_a=empty_snapshot, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.CREATE
        assert ops[0].node_type == NodeType.SYMLINK

    def test_symlink_follow_strategy_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "link",
            "type": NodeType.SYMLINK.value,
            "target": "/somewhere",
            "mtime": 1000.0,
        })

        config = DiffConfig(symlink_strategy="follow")
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=empty_snapshot, config=config
        )
        ops = engine.diff()
        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.DELETE
        assert ops[0].node_type == NodeType.SYMLINK

    def test_symlink_follow_strategy_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node(SymlinkNode(
            path="link",
            target="/old_target",
            mtime=1000.0,
        ))
        snapshot_b.add_node(SymlinkNode(
            path="link",
            target="/new_target",
            mtime=2000.0,
        ))

        config = DiffConfig(symlink_strategy="follow")
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        ops = engine.diff()
        assert len(ops) == 1
        from solocoder_py.dirtreediff import DiffOperationType
        assert ops[0].operation_type == DiffOperationType.MODIFY

    def test_symlink_follow_strategy_behavior_identical_to_detect(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node(SymlinkNode(
            path="deleted_link",
            target="/old",
            mtime=1000.0,
        ))
        snapshot_a.add_node(SymlinkNode(
            path="modified_link",
            target="/old_target",
            mtime=1000.0,
        ))
        snapshot_b.add_node(SymlinkNode(
            path="modified_link",
            target="/new_target",
            mtime=2000.0,
        ))
        snapshot_b.add_node(SymlinkNode(
            path="new_link",
            target="/created",
            mtime=2000.0,
        ))

        config_detect = DiffConfig(symlink_strategy="detect")
        engine_detect = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config_detect
        )
        ops_detect = engine_detect.diff()

        config_follow = DiffConfig(symlink_strategy="follow")
        engine_follow = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config_follow
        )
        ops_follow = engine_follow.diff()

        assert len(ops_detect) == len(ops_follow)
        for op_d, op_f in zip(ops_detect, ops_follow):
            assert op_d.operation_type == op_f.operation_type
            assert op_d.path == op_f.path
            assert op_d.node_type == op_f.node_type

    def test_invalid_symlink_strategy_raises(self):
        with pytest.raises(ValueError, match="Invalid symlink_strategy"):
            DiffConfig(symlink_strategy="invalid_value")


class TestCaseSensitivityConflicts:
    def test_case_insensitive_same_path_different_case_conflict(self):
        snapshot = DirectoryTreeSnapshot(
            root_path="/", timestamp=1000.0, case_sensitive=False
        )
        snapshot.add_node_from_dict({
            "path": "File.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("f1"),
        })

        with pytest.raises(CaseInsensitivePathConflictError, match="Path conflict"):
            snapshot.add_node_from_dict({
                "path": "file.txt",
                "type": NodeType.FILE.value,
                "size": 20,
                "mtime": 2000.0,
                "content_hash": compute_hash("f2"),
            })

    def test_case_sensitive_allows_different_case_paths(self):
        snapshot = DirectoryTreeSnapshot(
            root_path="/", timestamp=1000.0, case_sensitive=True
        )
        snapshot.add_node_from_dict({
            "path": "File.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("f1"),
        })
        snapshot.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 2000.0,
            "content_hash": compute_hash("f2"),
        })
        assert len(snapshot) == 2


class TestHashAlgorithmMismatch:
    def test_hash_algorithm_mismatch_raises_by_default(self):
        content = "same content"
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content, "sha256"),
            "hash_algorithm": "sha256",
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content, "md5"),
            "hash_algorithm": "md5",
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        with pytest.raises(HashAlgorithmMismatchError, match="Hash algorithm mismatch"):
            engine.diff()

    def test_hash_algorithm_mismatch_raises_without_resolver(self):
        content = "same content"
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content, "sha256"),
            "hash_algorithm": "sha256",
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": len(content),
            "mtime": 1000.0,
            "content_hash": compute_hash(content, "md5"),
            "hash_algorithm": "md5",
        })

        def failing_resolver(hash_a, algo_a, hash_b, algo_b):
            return None

        config = DiffConfig(hash_resolver=failing_resolver)
        engine = DirTreeDiffEngine(
            snapshot_a=snapshot_a, snapshot_b=snapshot_b, config=config
        )
        with pytest.raises(HashAlgorithmMismatchError):
            engine.diff()


class TestEngineInitializationErrors:
    def test_none_snapshot_a_raises(self, empty_snapshot):
        with pytest.raises(DirTreeDiffError, match="Both snapshots must be provided"):
            DirTreeDiffEngine(snapshot_a=None, snapshot_b=empty_snapshot)

    def test_none_snapshot_b_raises(self, empty_snapshot):
        with pytest.raises(DirTreeDiffError):
            DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=None)

    def test_mismatched_case_sensitive_settings_raises(self):
        snapshot_a = DirectoryTreeSnapshot(
            root_path="/", timestamp=1000.0, case_sensitive=True
        )
        snapshot_b = DirectoryTreeSnapshot(
            root_path="/", timestamp=2000.0, case_sensitive=False
        )
        with pytest.raises(DirTreeDiffError, match="case_sensitive setting"):
            DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)


class TestNodeTypeChange:
    def test_file_to_directory_change_is_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "path",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("file content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "path",
            "type": NodeType.DIRECTORY.value,
            "mtime": 2000.0,
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        from solocoder_py.dirtreediff import DiffOperationType
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "type" in changed_fields
