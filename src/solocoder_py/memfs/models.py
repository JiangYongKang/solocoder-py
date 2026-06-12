from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class NodeType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class Permission(str, Enum):
    READ = "r"
    WRITE = "w"
    EXECUTE = "x"


@dataclass
class Permissions:
    owner_read: bool = True
    owner_write: bool = True
    owner_execute: bool = False
    group_read: bool = True
    group_write: bool = False
    group_execute: bool = False
    other_read: bool = True
    other_write: bool = False
    other_execute: bool = False

    @classmethod
    def from_mode(cls, mode: int) -> "Permissions":
        if mode < 0 or mode > 0o777:
            raise ValueError(f"Invalid mode: {mode}")
        owner = (mode >> 6) & 0o7
        group = (mode >> 3) & 0o7
        other = mode & 0o7
        return cls(
            owner_read=bool(owner & 0o4),
            owner_write=bool(owner & 0o2),
            owner_execute=bool(owner & 0o1),
            group_read=bool(group & 0o4),
            group_write=bool(group & 0o2),
            group_execute=bool(group & 0o1),
            other_read=bool(other & 0o4),
            other_write=bool(other & 0o2),
            other_execute=bool(other & 0o1),
        )

    def to_mode(self) -> int:
        mode = 0
        if self.owner_read:
            mode |= 0o400
        if self.owner_write:
            mode |= 0o200
        if self.owner_execute:
            mode |= 0o100
        if self.group_read:
            mode |= 0o040
        if self.group_write:
            mode |= 0o020
        if self.group_execute:
            mode |= 0o010
        if self.other_read:
            mode |= 0o004
        if self.other_write:
            mode |= 0o002
        if self.other_execute:
            mode |= 0o001
        return mode

    def can_read(self, is_owner: bool, is_group: bool) -> bool:
        if is_owner:
            return self.owner_read
        if is_group:
            return self.group_read
        return self.other_read

    def can_write(self, is_owner: bool, is_group: bool) -> bool:
        if is_owner:
            return self.owner_write
        if is_group:
            return self.group_write
        return self.other_write

    def can_execute(self, is_owner: bool, is_group: bool) -> bool:
        if is_owner:
            return self.owner_execute
        if is_group:
            return self.group_execute
        return self.other_execute


@dataclass
class INode:
    name: str
    owner: str
    group: str
    permissions: Permissions = field(default_factory=Permissions)
    node_type: NodeType = NodeType.FILE

    def check_permission(self, perm: Permission, user: str, user_groups: set[str]) -> bool:
        is_owner = user == self.owner
        is_group = self.group in user_groups
        if perm == Permission.READ:
            return self.permissions.can_read(is_owner, is_group)
        if perm == Permission.WRITE:
            return self.permissions.can_write(is_owner, is_group)
        if perm == Permission.EXECUTE:
            return self.permissions.can_execute(is_owner, is_group)
        return False


@dataclass
class File(INode):
    content: bytes = field(default_factory=bytes)
    node_type: NodeType = NodeType.FILE

    def read(self) -> bytes:
        return self.content

    def write(self, data: bytes) -> None:
        self.content = data

    def append(self, data: bytes) -> None:
        self.content += data


@dataclass
class Directory(INode):
    children: Dict[str, INode] = field(default_factory=dict)
    node_type: NodeType = NodeType.DIRECTORY

    def list(self) -> list[str]:
        return sorted(self.children.keys())

    def get_child(self, name: str) -> Optional[INode]:
        return self.children.get(name)

    def add_child(self, node: INode) -> None:
        self.children[node.name] = node

    def remove_child(self, name: str) -> None:
        if name in self.children:
            del self.children[name]

    def is_empty(self) -> bool:
        return len(self.children) == 0


@dataclass
class Symlink(INode):
    target: str = ""
    node_type: NodeType = NodeType.SYMLINK
