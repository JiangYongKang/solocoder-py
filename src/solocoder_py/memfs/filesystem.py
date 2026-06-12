from __future__ import annotations

from typing import Optional, Tuple

from .exceptions import (
    DirectoryExistsError,
    DirectoryNotEmptyError,
    DirectoryNotFoundError,
    FileExistsError,
    FileNotFoundError,
    IsADirectoryError,
    NotADirectoryError,
    OperationNotPermittedError,
    PathNotFoundError,
    PermissionError as MemFSPermissionError,
    SymlinkLoopError,
)
from .models import (
    Directory,
    File,
    INode,
    NodeType,
    Permission,
    Permissions,
    Symlink,
)


MAX_SYMLINK_DEPTH = 40


class MemoryFileSystem:
    def __init__(self, default_owner: str = "root", default_group: str = "root") -> None:
        self.default_owner = default_owner
        self.default_group = default_group
        self.root = Directory(
            name="/",
            owner=default_owner,
            group=default_group,
            permissions=Permissions.from_mode(0o755),
        )
        self.current_user = default_owner
        self.current_groups: set[str] = {default_group}

    def set_user(self, user: str, groups: Optional[set[str]] = None) -> None:
        self.current_user = user
        self.current_groups = groups if groups is not None else set()

    def _normalize_path(self, path: str, cwd: str = "/") -> str:
        if not path:
            return "/"
        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path
        parts: list[str] = []
        for part in path.split("/"):
            if part == "" or part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return "/" + "/".join(parts)

    def _resolve_symlink(
        self,
        target: str,
        current_path: str,
        visited: set[str],
        depth: int = 0,
    ) -> Tuple[str, INode]:
        depth += 1
        if depth >= MAX_SYMLINK_DEPTH:
            raise SymlinkLoopError(f"Symlink loop detected after {MAX_SYMLINK_DEPTH} hops")
        abs_target = self._normalize_path(target, current_path.rsplit("/", 1)[0] or "/")
        if abs_target in visited:
            raise SymlinkLoopError(f"Symlink loop detected at {abs_target}")
        visited.add(abs_target)
        return self._lookup_node(abs_target, visited, depth + 1)

    def _lookup_node(
        self,
        path: str,
        visited: Optional[set[str]] = None,
        depth: int = 0,
        resolve_symlinks: bool = True,
    ) -> Tuple[str, INode]:
        path = self._normalize_path(path)
        if visited is None:
            visited = set()
        if path == "/":
            return "/", self.root
        parts = path.lstrip("/").split("/")
        current: INode = self.root
        current_path = "/"
        for part in parts:
            if isinstance(current, Symlink):
                if not resolve_symlinks:
                    break
                current_path, current = self._resolve_symlink(
                    current.target, current_path, visited, depth
                )
            if not isinstance(current, Directory):
                raise NotADirectoryError(f"{current_path} is not a directory")
            child = current.get_child(part)
            if child is None:
                raise PathNotFoundError(f"Path not found: {path}")
            current = child
            current_path = current_path.rstrip("/") + "/" + part
        if isinstance(current, Symlink) and resolve_symlinks:
            current_path, current = self._resolve_symlink(
                current.target, current_path, visited, depth
            )
        return current_path, current

    def _lookup_parent(self, path: str) -> Tuple[str, Directory, str]:
        path = self._normalize_path(path)
        if path == "/":
            raise OperationNotPermittedError("Cannot get parent of root directory")
        parent_path = path.rsplit("/", 1)[0] or "/"
        name = path.rsplit("/", 1)[1]
        _, parent_node = self._lookup_node(parent_path, resolve_symlinks=True)
        if not isinstance(parent_node, Directory):
            raise NotADirectoryError(f"{parent_path} is not a directory")
        return parent_path, parent_node, name

    def _check_permission(self, node: INode, perm: Permission) -> None:
        if not node.check_permission(perm, self.current_user, self.current_groups):
            raise MemFSPermissionError(
                f"Permission denied: {perm.value} access to {node.name} for user {self.current_user}"
            )

    def _check_path_permissions(self, path: str, perm: Permission) -> None:
        parts = path.lstrip("/").split("/")
        current = self.root
        current_path = "/"
        for i, part in enumerate(parts):
            if isinstance(current, Symlink):
                _, current = self._resolve_symlink(
                    current.target, current_path, set()
                )
            if not isinstance(current, Directory):
                raise NotADirectoryError(f"{current_path} is not a directory")
            self._check_permission(current, Permission.EXECUTE)
            child = current.get_child(part)
            if child is None:
                if i == len(parts) - 1:
                    return
                raise PathNotFoundError(f"Path not found: {path}")
            current = child
            current_path = current_path.rstrip("/") + "/" + part

    def mkdir(self, path: str, mode: int = 0o755) -> None:
        path = self._normalize_path(path)
        if path == "/":
            raise DirectoryExistsError("Directory already exists: /")
        try:
            _, parent, name = self._lookup_parent(path)
        except PathNotFoundError:
            raise DirectoryNotFoundError(f"Parent directory not found: {path}")
        if parent.get_child(name) is not None:
            raise DirectoryExistsError(f"Directory already exists: {path}")
        self._check_path_permissions(path, Permission.WRITE)
        self._check_permission(parent, Permission.WRITE)
        dir_node = Directory(
            name=name,
            owner=self.current_user,
            group=self.default_group,
            permissions=Permissions.from_mode(mode),
        )
        parent.add_child(dir_node)

    def mkdir_p(self, path: str, mode: int = 0o755) -> None:
        path = self._normalize_path(path)
        if path == "/":
            return
        try:
            _, node = self._lookup_node(path)
            if isinstance(node, Directory):
                return
            raise FileExistsError(f"File exists: {path}")
        except PathNotFoundError:
            pass
        parts = path.lstrip("/").split("/")
        current_path = "/"
        current = self.root
        for part in parts:
            self._check_permission(current, Permission.WRITE)
            child = current.get_child(part)
            if child is None:
                dir_node = Directory(
                    name=part,
                    owner=self.current_user,
                    group=self.default_group,
                    permissions=Permissions.from_mode(mode),
                )
                current.add_child(dir_node)
                current = dir_node
            elif isinstance(child, Directory):
                self._check_permission(child, Permission.EXECUTE)
                current = child
            elif isinstance(child, Symlink):
                resolved_path, resolved_node = self._resolve_symlink(
                    child.target, current_path, set()
                )
                if not isinstance(resolved_node, Directory):
                    raise NotADirectoryError(f"{resolved_path} is not a directory")
                current = resolved_node
            else:
                raise FileExistsError(f"File exists: {current_path}/{part}")
            current_path = current_path.rstrip("/") + "/" + part

    def create_file(self, path: str, content: bytes = b"", mode: int = 0o644) -> None:
        path = self._normalize_path(path)
        self._check_path_permissions(path, Permission.WRITE)
        _, parent, name = self._lookup_parent(path)
        if parent.get_child(name) is not None:
            raise FileExistsError(f"File already exists: {path}")
        self._check_permission(parent, Permission.WRITE)
        file_node = File(
            name=name,
            owner=self.current_user,
            group=self.default_group,
            permissions=Permissions.from_mode(mode),
            content=content,
        )
        parent.add_child(file_node)

    def write_file(self, path: str, content: bytes) -> None:
        path = self._normalize_path(path)
        _, node = self._lookup_node(path)
        if isinstance(node, Directory):
            raise IsADirectoryError(f"{path} is a directory")
        self._check_permission(node, Permission.WRITE)
        if isinstance(node, Symlink):
            _, resolved = self._resolve_symlink(node.target, path, set())
            if isinstance(resolved, Directory):
                raise IsADirectoryError(f"{path} resolves to a directory")
            if not isinstance(resolved, File):
                raise FileNotFoundError(f"{path} does not resolve to a file")
            self._check_permission(resolved, Permission.WRITE)
            resolved.write(content)
        else:
            if not isinstance(node, File):
                raise FileNotFoundError(f"{path} is not a file")
            node.write(content)

    def read_file(self, path: str) -> bytes:
        path = self._normalize_path(path)
        self._check_path_permissions(path, Permission.READ)
        _, node = self._lookup_node(path)
        if isinstance(node, Directory):
            raise IsADirectoryError(f"{path} is a directory")
        self._check_permission(node, Permission.READ)
        if isinstance(node, Symlink):
            _, resolved = self._resolve_symlink(node.target, path, set())
            if isinstance(resolved, Directory):
                raise IsADirectoryError(f"{path} resolves to a directory")
            if not isinstance(resolved, File):
                raise FileNotFoundError(f"{path} does not resolve to a file")
            self._check_permission(resolved, Permission.READ)
            return resolved.read()
        else:
            if not isinstance(node, File):
                raise FileNotFoundError(f"{path} is not a file")
            return node.read()

    def list_dir(self, path: str = "/") -> list[str]:
        path = self._normalize_path(path)
        self._check_path_permissions(path, Permission.READ)
        _, node = self._lookup_node(path)
        if isinstance(node, Symlink):
            _, resolved = self._resolve_symlink(node.target, path, set())
            if not isinstance(resolved, Directory):
                raise NotADirectoryError(f"{path} is not a directory")
            self._check_permission(resolved, Permission.READ)
            self._check_permission(resolved, Permission.EXECUTE)
            return resolved.list()
        if not isinstance(node, Directory):
            raise NotADirectoryError(f"{path} is not a directory")
        self._check_permission(node, Permission.READ)
        self._check_permission(node, Permission.EXECUTE)
        return node.list()

    def symlink(self, target: str, link_path: str) -> None:
        link_path = self._normalize_path(link_path)
        self._check_path_permissions(link_path, Permission.WRITE)
        _, parent, name = self._lookup_parent(link_path)
        if parent.get_child(name) is not None:
            raise FileExistsError(f"Path already exists: {link_path}")
        self._check_permission(parent, Permission.WRITE)
        symlink_node = Symlink(
            name=name,
            owner=self.current_user,
            group=self.default_group,
            permissions=Permissions.from_mode(0o777),
            target=target,
        )
        parent.add_child(symlink_node)

    def readlink(self, path: str) -> str:
        path = self._normalize_path(path)
        _, node = self._lookup_node(path, resolve_symlinks=False)
        if not isinstance(node, Symlink):
            raise OperationNotPermittedError(f"{path} is not a symlink")
        return node.target

    def chmod(self, path: str, mode: int) -> None:
        path = self._normalize_path(path)
        _, node = self._lookup_node(path, resolve_symlinks=False)
        if self.current_user != node.owner and self.current_user != self.default_owner:
            raise OperationNotPermittedError(
                f"Only owner can change permissions of {path}"
            )
        node.permissions = Permissions.from_mode(mode)

    def chown(self, path: str, owner: str, group: str) -> None:
        path = self._normalize_path(path)
        if self.current_user != self.default_owner:
            raise OperationNotPermittedError("Only root can change ownership")
        _, node = self._lookup_node(path, resolve_symlinks=False)
        node.owner = owner
        node.group = group

    def unlink(self, path: str) -> None:
        path = self._normalize_path(path)
        if path == "/":
            raise OperationNotPermittedError("Cannot unlink root directory")
        self._check_path_permissions(path, Permission.WRITE)
        _, parent, name = self._lookup_parent(path)
        child = parent.get_child(name)
        if child is None:
            raise PathNotFoundError(f"Path not found: {path}")
        if isinstance(child, Directory):
            raise IsADirectoryError(f"{path} is a directory")
        self._check_permission(parent, Permission.WRITE)
        parent.remove_child(name)

    def rmdir(self, path: str) -> None:
        path = self._normalize_path(path)
        if path == "/":
            raise OperationNotPermittedError("Cannot remove root directory")
        self._check_path_permissions(path, Permission.WRITE)
        _, parent, name = self._lookup_parent(path)
        child = parent.get_child(name)
        if child is None:
            raise PathNotFoundError(f"Path not found: {path}")
        if not isinstance(child, Directory):
            raise NotADirectoryError(f"{path} is not a directory")
        if not child.is_empty():
            raise DirectoryNotEmptyError(f"Directory not empty: {path}")
        self._check_permission(parent, Permission.WRITE)
        parent.remove_child(name)

    def remove(self, path: str) -> None:
        path = self._normalize_path(path)
        try:
            _, node = self._lookup_node(path, resolve_symlinks=False)
        except PathNotFoundError:
            raise
        if isinstance(node, Directory):
            self.rmdir(path)
        else:
            self.unlink(path)

    def exists(self, path: str) -> bool:
        try:
            self._lookup_node(path)
            return True
        except PathNotFoundError:
            return False

    def is_file(self, path: str) -> bool:
        try:
            _, node = self._lookup_node(path)
            return isinstance(node, File)
        except PathNotFoundError:
            return False

    def is_dir(self, path: str) -> bool:
        try:
            _, node = self._lookup_node(path)
            return isinstance(node, Directory)
        except PathNotFoundError:
            return False

    def is_symlink(self, path: str) -> bool:
        try:
            _, node = self._lookup_node(path, resolve_symlinks=False)
            return isinstance(node, Symlink)
        except PathNotFoundError:
            return False

    def get_mode(self, path: str) -> int:
        _, node = self._lookup_node(path, resolve_symlinks=False)
        return node.permissions.to_mode()

    def get_owner(self, path: str) -> str:
        _, node = self._lookup_node(path, resolve_symlinks=False)
        return node.owner

    def get_group(self, path: str) -> str:
        _, node = self._lookup_node(path, resolve_symlinks=False)
        return node.group

    def stat(self, path: str) -> dict:
        resolved_path, node = self._lookup_node(path, resolve_symlinks=False)
        return {
            "path": resolved_path,
            "name": node.name,
            "type": node.node_type,
            "owner": node.owner,
            "group": node.group,
            "mode": node.permissions.to_mode(),
            "size": len(node.content) if isinstance(node, File) else 0,
        }
