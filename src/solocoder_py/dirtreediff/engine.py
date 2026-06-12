from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import (
    DirTreeDiffError,
    HashAlgorithmMismatchError,
    SymlinkNotSupportedError,
)
from .models import (
    DirectoryNode,
    DiffOperation,
    DiffOperationType,
    DirectoryTreeSnapshot,
    FieldChange,
    FileNode,
    NodeType,
    SymlinkNode,
    TreeNode,
)


@dataclass
class DiffConfig:
    include_mtime: bool = True
    include_permissions: bool = True
    symlink_strategy: str = "detect"
    allow_hash_algorithm_mismatch: bool = False
    hash_resolver: Optional[Callable[[str, str, str, str], Optional[str]]] = None
    _validate_symlink_strategy = True

    def __post_init__(self) -> None:
        if self.symlink_strategy not in {"follow", "ignore", "detect", "error"}:
            raise ValueError(
                f"Invalid symlink_strategy: '{self.symlink_strategy}'. "
                f"Must be one of: follow, ignore, detect, error"
            )


@dataclass
class DirTreeDiffEngine:
    snapshot_a: DirectoryTreeSnapshot
    snapshot_b: DirectoryTreeSnapshot
    config: DiffConfig = field(default_factory=DiffConfig)

    def __post_init__(self) -> None:
        if self.snapshot_a is None or self.snapshot_b is None:
            raise DirTreeDiffError("Both snapshots must be provided")
        if self.snapshot_a.case_sensitive != self.snapshot_b.case_sensitive:
            raise DirTreeDiffError(
                "Both snapshots must have the same case_sensitive setting"
            )

    def _get_compare_fields(self, node: TreeNode) -> List[str]:
        fields: List[str] = []
        if isinstance(node, FileNode):
            fields.extend(["type", "size", "content_hash", "hash_algorithm"])
            if self.config.include_mtime:
                fields.append("mtime")
            if self.config.include_permissions:
                fields.append("permissions")
        elif isinstance(node, DirectoryNode):
            fields.append("type")
            if self.config.include_mtime:
                fields.append("mtime")
            if self.config.include_permissions:
                fields.append("permissions")
        elif isinstance(node, SymlinkNode):
            fields.extend(["type", "target"])
            if self.config.include_mtime:
                fields.append("mtime")
        return fields

    def _node_to_dict(self, node: TreeNode) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if isinstance(node, FileNode):
            result = {
                "path": node.path,
                "type": node.type.value,
                "size": node.size,
                "mtime": node.mtime,
                "content_hash": node.content_hash,
                "hash_algorithm": node.hash_algorithm,
            }
            if node.permissions is not None:
                result["permissions"] = node.permissions
        elif isinstance(node, DirectoryNode):
            result = {
                "path": node.path,
                "type": node.type.value,
                "mtime": node.mtime,
            }
            if node.permissions is not None:
                result["permissions"] = node.permissions
        elif isinstance(node, SymlinkNode):
            result = {
                "path": node.path,
                "type": node.type.value,
                "target": node.target,
                "mtime": node.mtime,
            }
        return result

    def _compare_nodes(
        self, node_a: TreeNode, node_b: TreeNode
    ) -> Tuple[bool, List[FieldChange]]:
        if type(node_a) != type(node_b):
            changes = [
                FieldChange(
                    field="type",
                    old_value=node_a.type.value,
                    new_value=node_b.type.value,
                )
            ]
            return True, changes

        fields = self._get_compare_fields(node_a)
        changes: List[FieldChange] = []

        for field in fields:
            val_a = getattr(node_a, field, None)
            val_b = getattr(node_b, field, None)

            if field == "hash_algorithm":
                if val_a != val_b:
                    if self.config.allow_hash_algorithm_mismatch:
                        continue
                    if self.config.hash_resolver is not None:
                        file_node_a = node_a if isinstance(node_a, FileNode) else None
                        file_node_b = node_b if isinstance(node_b, FileNode) else None
                        if file_node_a and file_node_b:
                            resolved = self.config.hash_resolver(
                                file_node_a.content_hash,
                                file_node_a.hash_algorithm,
                                file_node_b.content_hash,
                                file_node_b.hash_algorithm,
                            )
                            if resolved is not None:
                                continue
                    raise HashAlgorithmMismatchError(
                        f"Hash algorithm mismatch at path '{node_a.path}': "
                        f"'{val_a}' vs '{val_b}'"
                    )
                continue

            if field == "content_hash":
                file_node_a = node_a if isinstance(node_a, FileNode) else None
                file_node_b = node_b if isinstance(node_b, FileNode) else None
                if file_node_a and file_node_b:
                    if file_node_a.hash_algorithm != file_node_b.hash_algorithm:
                        if self.config.allow_hash_algorithm_mismatch:
                            continue
                        if self.config.hash_resolver is not None:
                            resolved = self.config.hash_resolver(
                                file_node_a.content_hash,
                                file_node_a.hash_algorithm,
                                file_node_b.content_hash,
                                file_node_b.hash_algorithm,
                            )
                            if resolved is not None:
                                if resolved == file_node_a.content_hash:
                                    continue
                                if resolved == file_node_b.content_hash:
                                    continue
                        raise HashAlgorithmMismatchError(
                            f"Hash algorithm mismatch at path '{node_a.path}': "
                            f"'{file_node_a.hash_algorithm}' vs '{file_node_b.hash_algorithm}'"
                        )

            if val_a != val_b:
                changes.append(
                    FieldChange(field=field, old_value=val_a, new_value=val_b)
                )

        return len(changes) > 0, changes

    def _create_operation(
        self,
        op_type: DiffOperationType,
        path: str,
        node_a: Optional[TreeNode] = None,
        node_b: Optional[TreeNode] = None,
        changes: Optional[List[FieldChange]] = None,
    ) -> DiffOperation:
        old_attrs = self._node_to_dict(node_a) if node_a else None
        new_attrs = self._node_to_dict(node_b) if node_b else None

        node_type = None
        if node_b:
            node_type = node_b.type
        elif node_a:
            node_type = node_a.type

        return DiffOperation(
            operation_type=op_type,
            path=path,
            node_type=node_type,
            old_attributes=old_attrs,
            new_attributes=new_attrs,
            changed_fields=changes,
        )

    def _handle_symlink_node(
        self, path: str, node_a: Optional[TreeNode], node_b: Optional[TreeNode]
    ) -> List[DiffOperation]:
        strategy = self.config.symlink_strategy

        if strategy == "error":
            symlink_node = node_b if node_b else node_a
            if symlink_node and isinstance(symlink_node, SymlinkNode):
                raise SymlinkNotSupportedError(
                    f"Symlinks are not supported: '{path}'"
                )

        if strategy == "ignore":
            return []

        if strategy in ("detect", "follow"):
            operations: List[DiffOperation] = []
            if node_a is None and node_b is not None:
                operations.append(
                    self._create_operation(DiffOperationType.CREATE, path, None, node_b)
                )
            elif node_a is not None and node_b is None:
                operations.append(
                    self._create_operation(DiffOperationType.DELETE, path, node_a, None)
                )
            else:
                assert node_a is not None and node_b is not None
                modified, changes = self._compare_nodes(node_a, node_b)
                if modified:
                    operations.append(
                        self._create_operation(
                            DiffOperationType.MODIFY, path, node_a, node_b, changes
                        )
                    )
            return operations

        return []

    def _get_merged_paths(self) -> List[str]:
        if self.snapshot_a.case_sensitive:
            paths_a = set(self.snapshot_a.all_paths())
            paths_b = set(self.snapshot_b.all_paths())
            return sorted(paths_a | paths_b)

        key_to_path_a: Dict[str, str] = {}
        for p in self.snapshot_a.all_paths():
            key = p.lower()
            key_to_path_a[key] = p

        key_to_path_b: Dict[str, str] = {}
        for p in self.snapshot_b.all_paths():
            key = p.lower()
            key_to_path_b[key] = p

        all_keys = sorted(set(key_to_path_a.keys()) | set(key_to_path_b.keys()))
        result: List[str] = []
        for key in all_keys:
            if key in key_to_path_b:
                result.append(key_to_path_b[key])
            else:
                result.append(key_to_path_a[key])
        return result

    def diff(self) -> List[DiffOperation]:
        operations: List[DiffOperation] = []

        all_paths = self._get_merged_paths()

        for path in all_paths:
            node_a = self.snapshot_a.get_node(path)
            node_b = self.snapshot_b.get_node(path)

            effective_path = node_b.path if node_b else (node_a.path if node_a else path)

            if (node_a and isinstance(node_a, SymlinkNode)) or (
                node_b and isinstance(node_b, SymlinkNode)
            ):
                symlink_ops = self._handle_symlink_node(effective_path, node_a, node_b)
                operations.extend(symlink_ops)
                continue

            if node_a is None and node_b is not None:
                operations.append(
                    self._create_operation(DiffOperationType.CREATE, effective_path, None, node_b)
                )
            elif node_a is not None and node_b is None:
                operations.append(
                    self._create_operation(DiffOperationType.DELETE, effective_path, node_a, None)
                )
            else:
                assert node_a is not None and node_b is not None
                modified, changes = self._compare_nodes(node_a, node_b)
                if modified:
                    operations.append(
                        self._create_operation(
                            DiffOperationType.MODIFY, effective_path, node_a, node_b, changes
                        )
                    )

        return operations

    def diff_by_type(
        self,
    ) -> Dict[DiffOperationType, List[DiffOperation]]:
        operations = self.diff()
        result: Dict[DiffOperationType, List[DiffOperation]] = {
            DiffOperationType.CREATE: [],
            DiffOperationType.DELETE: [],
            DiffOperationType.MODIFY: [],
        }
        for op in operations:
            result[op.operation_type].append(op)
        return result

    def summary(self) -> Dict[str, int]:
        by_type = self.diff_by_type()
        return {
            "create": len(by_type[DiffOperationType.CREATE]),
            "delete": len(by_type[DiffOperationType.DELETE]),
            "modify": len(by_type[DiffOperationType.MODIFY]),
            "total": sum(len(ops) for ops in by_type.values()),
        }
