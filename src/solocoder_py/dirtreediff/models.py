from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pathlib import PurePosixPath

from .exceptions import (
    DuplicatePathError,
    InvalidNodeTypeError,
    MissingRequiredFieldError,
    CaseInsensitivePathConflictError,
    SymlinkNotSupportedError,
)


class NodeType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class DiffOperationType(str, Enum):
    CREATE = "create"
    DELETE = "delete"
    MODIFY = "modify"


REQUIRED_FILE_FIELDS = {"path", "type", "size", "mtime", "content_hash"}
REQUIRED_DIR_FIELDS = {"path", "type", "mtime"}
REQUIRED_COMMON_FIELDS = {"path", "type"}


@dataclass
class FileNode:
    path: str
    size: int
    mtime: float
    content_hash: str
    hash_algorithm: str = "sha256"
    permissions: Optional[int] = None
    type: NodeType = NodeType.FILE

    def __post_init__(self) -> None:
        if self.type != NodeType.FILE:
            raise InvalidNodeTypeError(
                f"FileNode requires type='{NodeType.FILE}', got '{self.type}'"
            )
        if self.size < 0:
            raise ValueError(f"size cannot be negative: {self.size}")
        if not self.content_hash:
            raise MissingRequiredFieldError("content_hash cannot be empty")


@dataclass
class DirectoryNode:
    path: str
    mtime: float
    permissions: Optional[int] = None
    type: NodeType = NodeType.DIRECTORY

    def __post_init__(self) -> None:
        if self.type != NodeType.DIRECTORY:
            raise InvalidNodeTypeError(
                f"DirectoryNode requires type='{NodeType.DIRECTORY}', got '{self.type}'"
            )


@dataclass
class SymlinkNode:
    path: str
    target: str
    mtime: float
    type: NodeType = NodeType.SYMLINK

    def __post_init__(self) -> None:
        if self.type != NodeType.SYMLINK:
            raise InvalidNodeTypeError(
                f"SymlinkNode requires type='{NodeType.SYMLINK}', got '{self.type}'"
            )


TreeNode = Union[FileNode, DirectoryNode, SymlinkNode]


@dataclass
class FieldChange:
    field: str
    old_value: Any
    new_value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


@dataclass
class DiffOperation:
    operation_type: DiffOperationType
    path: str
    node_type: Optional[NodeType] = None
    old_attributes: Optional[Dict[str, Any]] = None
    new_attributes: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[FieldChange]] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "operation": self.operation_type.value,
            "path": self.path,
        }
        if self.node_type is not None:
            result["node_type"] = self.node_type.value
        if self.old_attributes is not None:
            result["old_attributes"] = self.old_attributes
        if self.new_attributes is not None:
            result["new_attributes"] = self.new_attributes
        if self.changed_fields is not None:
            result["changed_fields"] = [cf.to_dict() for cf in self.changed_fields]
        return result

    def __repr__(self) -> str:
        parts = [f"op={self.operation_type.value}", f"path={self.path}"]
        if self.node_type:
            parts.append(f"type={self.node_type.value}")
        if self.changed_fields:
            fields = [cf.field for cf in self.changed_fields]
            parts.append(f"changed={fields}")
        return f"DiffOperation({', '.join(parts)})"


class DirectoryTreeSnapshot:
    def __init__(
        self,
        root_path: str,
        timestamp: float,
        hash_algorithm: str = "sha256",
        case_sensitive: bool = True,
    ) -> None:
        self._root_path = root_path
        self._timestamp = timestamp
        self._hash_algorithm = hash_algorithm
        self._case_sensitive = case_sensitive
        self._nodes: Dict[str, TreeNode] = {}
        self._path_index: Dict[str, str] = {}

    @property
    def root_path(self) -> str:
        return self._root_path

    @property
    def timestamp(self) -> float:
        return self._timestamp

    @property
    def hash_algorithm(self) -> str:
        return self._hash_algorithm

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    def _normalize_path(self, path: str) -> str:
        converted = path.replace("\\", "/")
        normalized = PurePosixPath(converted).as_posix()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized == ".":
            normalized = ""
        return normalized

    def _get_index_key(self, path: str) -> str:
        if self._case_sensitive:
            return path
        return path.lower()

    def _validate_dict(self, data: Dict[str, Any]) -> None:
        missing = REQUIRED_COMMON_FIELDS - data.keys()
        if missing:
            raise MissingRequiredFieldError(
                f"Missing required fields: {sorted(missing)}"
            )

        node_type = data.get("type")
        try:
            node_type_enum = NodeType(node_type)
        except ValueError:
            raise InvalidNodeTypeError(
                f"Invalid node type: '{node_type}'. "
                f"Must be one of: {[e.value for e in NodeType]}"
            )

        if node_type_enum == NodeType.FILE:
            missing = REQUIRED_FILE_FIELDS - data.keys()
            if missing:
                raise MissingRequiredFieldError(
                    f"File node missing required fields: {sorted(missing)}"
                )
        elif node_type_enum == NodeType.DIRECTORY:
            missing = REQUIRED_DIR_FIELDS - data.keys()
            if missing:
                raise MissingRequiredFieldError(
                    f"Directory node missing required fields: {sorted(missing)}"
                )
        elif node_type_enum == NodeType.SYMLINK:
            if "target" not in data:
                raise MissingRequiredFieldError(
                    "Symlink node missing required field: 'target'"
                )

    def add_node_from_dict(self, data: Dict[str, Any]) -> None:
        self._validate_dict(data)
        path = self._normalize_path(data["path"])
        index_key = self._get_index_key(path)

        if index_key in self._path_index:
            existing_path = self._path_index[index_key]
            if existing_path != path:
                raise CaseInsensitivePathConflictError(
                    f"Path conflict due to case insensitivity: "
                    f"'{existing_path}' vs '{path}'"
                )
            raise DuplicatePathError(f"Duplicate path in snapshot: '{path}'")

        node_type = NodeType(data["type"])

        if node_type == NodeType.FILE:
            node: TreeNode = FileNode(
                path=path,
                size=data["size"],
                mtime=data["mtime"],
                content_hash=data["content_hash"],
                hash_algorithm=data.get("hash_algorithm", self._hash_algorithm),
                permissions=data.get("permissions"),
            )
        elif node_type == NodeType.DIRECTORY:
            node = DirectoryNode(
                path=path,
                mtime=data["mtime"],
                permissions=data.get("permissions"),
            )
        elif node_type == NodeType.SYMLINK:
            node = SymlinkNode(
                path=path,
                target=data["target"],
                mtime=data["mtime"],
            )
        else:
            raise InvalidNodeTypeError(f"Unsupported node type: {node_type}")

        self._nodes[path] = node
        self._path_index[index_key] = path

    def add_node(self, node: TreeNode) -> None:
        path = self._normalize_path(node.path)
        index_key = self._get_index_key(path)

        if index_key in self._path_index:
            existing_path = self._path_index[index_key]
            if existing_path != path:
                raise CaseInsensitivePathConflictError(
                    f"Path conflict due to case insensitivity: "
                    f"'{existing_path}' vs '{path}'"
                )
            raise DuplicatePathError(f"Duplicate path in snapshot: '{path}'")

        if isinstance(node, FileNode):
            node.path = path
        elif isinstance(node, DirectoryNode):
            node.path = path
        elif isinstance(node, SymlinkNode):
            node.path = path

        self._nodes[path] = node
        self._path_index[index_key] = path

    def get_node(self, path: str) -> Optional[TreeNode]:
        normalized = self._normalize_path(path)
        if not self._case_sensitive:
            index_key = normalized.lower()
            actual_path = self._path_index.get(index_key)
            if actual_path:
                return self._nodes.get(actual_path)
            return None
        return self._nodes.get(normalized)

    def has_path(self, path: str) -> bool:
        normalized = self._normalize_path(path)
        if not self._case_sensitive:
            return normalized.lower() in self._path_index
        return normalized in self._nodes

    def all_paths(self) -> List[str]:
        return sorted(self._nodes.keys())

    def all_nodes(self) -> Dict[str, TreeNode]:
        return dict(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes.values())

    def __contains__(self, path: str) -> bool:
        return self.has_path(path)
