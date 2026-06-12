from __future__ import annotations

import pytest

from solocoder_py.dirtreediff import (
    DiffOperationType,
    DirTreeDiffEngine,
    DirectoryTreeSnapshot,
    NodeType,
)

from .conftest import compute_hash


class TestCreateDetection:
    def test_single_new_file_detected_as_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "new_file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 2000.0,
            "content_hash": compute_hash("new content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.CREATE
        assert ops[0].path == "new_file.txt"
        assert ops[0].node_type == NodeType.FILE
        assert ops[0].old_attributes is None
        assert ops[0].new_attributes is not None
        assert ops[0].new_attributes["size"] == 100
        assert ops[0].changed_fields is None

    def test_single_new_directory_detected_as_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "new_dir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 2000.0,
        })

        engine = DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.CREATE
        assert ops[0].path == "new_dir"
        assert ops[0].node_type == NodeType.DIRECTORY

    def test_multiple_new_files_all_detected_as_create(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "existing.txt",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 1000.0,
            "content_hash": compute_hash("existing"),
        })

        snapshot_b.add_node_from_dict({
            "path": "existing.txt",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 1000.0,
            "content_hash": compute_hash("existing"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file1.txt",
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

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        create_ops = [op for op in ops if op.operation_type == DiffOperationType.CREATE]
        assert len(create_ops) == 2
        paths = sorted([op.path for op in create_ops])
        assert paths == ["file1.txt", "file2.txt"]


class TestDeleteDetection:
    def test_single_deleted_file_detected_as_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "deleted_file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("old content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=empty_snapshot)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.DELETE
        assert ops[0].path == "deleted_file.txt"
        assert ops[0].node_type == NodeType.FILE
        assert ops[0].old_attributes is not None
        assert ops[0].new_attributes is None

    def test_single_deleted_directory_detected_as_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "old_dir",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=empty_snapshot)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.DELETE
        assert ops[0].path == "old_dir"

    def test_multiple_deletions_all_detected(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "keep.txt",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 1000.0,
            "content_hash": compute_hash("keep"),
        })
        snapshot_a.add_node_from_dict({
            "path": "delete1.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("d1"),
        })
        snapshot_a.add_node_from_dict({
            "path": "delete2.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 1000.0,
            "content_hash": compute_hash("d2"),
        })

        snapshot_b.add_node_from_dict({
            "path": "keep.txt",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 1000.0,
            "content_hash": compute_hash("keep"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        delete_ops = [op for op in ops if op.operation_type == DiffOperationType.DELETE]
        assert len(delete_ops) == 2
        paths = sorted([op.path for op in delete_ops])
        assert paths == ["delete1.txt", "delete2.txt"]


class TestModifyDetection:
    def test_file_content_change_detected_as_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("old content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 105,
            "mtime": 2000.0,
            "content_hash": compute_hash("new content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        assert ops[0].path == "file.txt"
        assert ops[0].changed_fields is not None
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "size" in changed_fields
        assert "mtime" in changed_fields
        assert "content_hash" in changed_fields

    def test_file_only_size_change_detected_as_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("same content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 200,
            "mtime": 1000.0,
            "content_hash": compute_hash("same content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "size" in changed_fields
        assert "mtime" not in changed_fields
        assert "content_hash" not in changed_fields

    def test_directory_permissions_change_detected_as_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

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

    def test_file_mtime_only_change_is_modify(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("same content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 2000.0,
            "content_hash": compute_hash("same content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "mtime" in changed_fields
        assert len(changed_fields) == 1

    def test_file_content_change_only(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)

        snapshot_a.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("old content"),
        })
        snapshot_b.add_node_from_dict({
            "path": "file.txt",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 1000.0,
            "content_hash": compute_hash("new content"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        assert len(ops) == 1
        assert ops[0].operation_type == DiffOperationType.MODIFY
        changed_fields = {cf.field for cf in ops[0].changed_fields}
        assert "content_hash" in changed_fields
        assert len(changed_fields) == 1


class TestRecursiveDirectoryChanges:
    def test_new_directory_with_children_all_create(self, empty_snapshot):
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)
        snapshot_b.add_node_from_dict({
            "path": "src",
            "type": NodeType.DIRECTORY.value,
            "mtime": 2000.0,
        })
        snapshot_b.add_node_from_dict({
            "path": "src/utils",
            "type": NodeType.DIRECTORY.value,
            "mtime": 2000.0,
        })
        snapshot_b.add_node_from_dict({
            "path": "src/utils/helper.py",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 2000.0,
            "content_hash": compute_hash("def helper(): pass"),
        })
        snapshot_b.add_node_from_dict({
            "path": "src/main.py",
            "type": NodeType.FILE.value,
            "size": 100,
            "mtime": 2000.0,
            "content_hash": compute_hash("def main(): pass"),
        })

        engine = DirTreeDiffEngine(snapshot_a=empty_snapshot, snapshot_b=snapshot_b)
        ops = engine.diff()

        create_ops = [op for op in ops if op.operation_type == DiffOperationType.CREATE]
        assert len(create_ops) == 4
        paths = [op.path for op in ops]
        assert paths == sorted(paths)
        assert "src" in paths
        assert "src/utils" in paths
        assert "src/utils/helper.py" in paths
        assert "src/main.py" in paths

    def test_deleted_directory_with_children_all_delete(self, empty_snapshot):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_a.add_node_from_dict({
            "path": "src",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
        })
        snapshot_a.add_node_from_dict({
            "path": "src/utils",
            "type": NodeType.DIRECTORY.value,
            "mtime": 1000.0,
        })
        snapshot_a.add_node_from_dict({
            "path": "src/utils/helper.py",
            "type": NodeType.FILE.value,
            "size": 50,
            "mtime": 1000.0,
            "content_hash": compute_hash("def helper(): pass"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=empty_snapshot)
        ops = engine.diff()

        delete_ops = [op for op in ops if op.operation_type == DiffOperationType.DELETE]
        assert len(delete_ops) == 3
        paths = [op.path for op in ops]
        assert paths == sorted(paths)


class TestMixedScenarios:
    def test_all_three_operation_types(self, simple_snapshot_a, simple_snapshot_b):
        engine = DirTreeDiffEngine(
            snapshot_a=simple_snapshot_a, snapshot_b=simple_snapshot_b
        )
        ops = engine.diff()

        by_type: dict = {}
        for op in ops:
            by_type.setdefault(op.operation_type, []).append(op)

        assert DiffOperationType.CREATE in by_type
        assert DiffOperationType.DELETE in by_type
        assert DiffOperationType.MODIFY in by_type

        create_paths = [op.path for op in by_type[DiffOperationType.CREATE]]
        assert "src/utils.py" in create_paths

        delete_paths = [op.path for op in by_type[DiffOperationType.DELETE]]
        assert "docs" in delete_paths

        modify_paths = [op.path for op in by_type[DiffOperationType.MODIFY]]
        assert "src/main.py" in modify_paths

    def test_operations_sorted_by_path_lexicographic(self):
        snapshot_a = DirectoryTreeSnapshot(root_path="/", timestamp=1000.0)
        snapshot_b = DirectoryTreeSnapshot(root_path="/", timestamp=2000.0)

        snapshot_a.add_node_from_dict({
            "path": "zebra.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("z"),
        })
        snapshot_a.add_node_from_dict({
            "path": "alpha.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 1000.0,
            "content_hash": compute_hash("a"),
        })

        snapshot_b.add_node_from_dict({
            "path": "zebra.txt",
            "type": NodeType.FILE.value,
            "size": 20,
            "mtime": 2000.0,
            "content_hash": compute_hash("z2"),
        })
        snapshot_b.add_node_from_dict({
            "path": "beta.txt",
            "type": NodeType.FILE.value,
            "size": 10,
            "mtime": 2000.0,
            "content_hash": compute_hash("b"),
        })

        engine = DirTreeDiffEngine(snapshot_a=snapshot_a, snapshot_b=snapshot_b)
        ops = engine.diff()

        paths = [op.path for op in ops]
        assert paths == sorted(paths)

    def test_diff_by_type_method(self, simple_snapshot_a, simple_snapshot_b):
        engine = DirTreeDiffEngine(
            snapshot_a=simple_snapshot_a, snapshot_b=simple_snapshot_b
        )
        by_type = engine.diff_by_type()

        assert DiffOperationType.CREATE in by_type
        assert DiffOperationType.DELETE in by_type
        assert DiffOperationType.MODIFY in by_type
        assert all(isinstance(v, list) for v in by_type.values())

    def test_summary_method(self, simple_snapshot_a, simple_snapshot_b):
        engine = DirTreeDiffEngine(
            snapshot_a=simple_snapshot_a, snapshot_b=simple_snapshot_b
        )
        summary = engine.summary()

        assert "create" in summary
        assert "delete" in summary
        assert "modify" in summary
        assert "total" in summary
        assert summary["total"] == summary["create"] + summary["delete"] + summary["modify"]
        assert summary["total"] == 3

    def test_diff_operation_to_dict(self):
        from solocoder_py.dirtreediff import DiffOperation, FieldChange

        op = DiffOperation(
            operation_type=DiffOperationType.MODIFY,
            path="file.txt",
            node_type=NodeType.FILE,
            old_attributes={"size": 100},
            new_attributes={"size": 200},
            changed_fields=[FieldChange(field="size", old_value=100, new_value=200)],
        )
        d = op.to_dict()
        assert d["operation"] == "modify"
        assert d["path"] == "file.txt"
        assert d["node_type"] == "file"
        assert d["old_attributes"] == {"size": 100}
        assert d["new_attributes"] == {"size": 200}
        assert len(d["changed_fields"]) == 1
        assert d["changed_fields"][0]["field"] == "size"
