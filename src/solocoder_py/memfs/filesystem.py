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

    def _resolve_single_symlink(
        self,
        symlink: Symlink,
        link_path: str,
        visited: set[str],
        depth: int,
    ) -> Tuple[str, INode, int, list[Directory]]:
        depth += 1
        if depth >= MAX_SYMLINK_DEPTH:
            raise SymlinkLoopError(
                f"Symlink loop detected after {MAX_SYMLINK_DEPTH} hops"
            )
        base_dir = link_path.rsplit("/", 1)[0] or "/"
        abs_target = self._normalize_path(symlink.target, base_dir)
        if abs_target in visited:
            raise SymlinkLoopError(f"Symlink loop detected at {abs_target}")
        visited.add(abs_target)
        resolved_path, resolved_node, new_depth, traversed = self._walk_path_components(
            abs_target,
            visited=visited,
            depth=depth,
            resolve_final_symlink=True,
            allow_missing_last=False,
        )
        return resolved_path, resolved_node, new_depth, traversed

    def _walk_path_components(
        self,
        path: str,
        visited: Optional[set[str]] = None,
        depth: int = 0,
        resolve_final_symlink: bool = True,
        allow_missing_last: bool = False,
    ) -> Tuple[str, INode, int, list[Directory]]:
        path = self._normalize_path(path)
        if visited is None:
            visited = set()

        traversed: list[Directory] = []

        if path == "/":
            traversed.append(self.root)
            return "/", self.root, depth, traversed

        parts = path.lstrip("/").split("/")
        current: INode = self.root
        current_path = "/"
        total_parts = len(parts)

        for idx, part in enumerate(parts):
            is_last = idx == total_parts - 1

            if isinstance(current, Symlink):
                current_path, current, depth, sym_traversed = self._resolve_single_symlink(
                    current, current_path, visited, depth
                )
                traversed.extend(sym_traversed[:-1])

            if not isinstance(current, Directory):
                raise NotADirectoryError(f"{current_path} is not a directory")

            traversed.append(current)

            child = current.get_child(part)
            if child is None:
                if allow_missing_last and is_last:
                    return current_path, current, depth, traversed
                raise PathNotFoundError(f"Path not found: {path}")

            current = child
            current_path = current_path.rstrip("/") + "/" + part

        if isinstance(current, Symlink) and resolve_final_symlink:
            current_path, current, depth, sym_traversed = self._resolve_single_symlink(
                current, current_path, visited, depth
            )
            traversed.extend(sym_traversed[:-1])
            if isinstance(current, Directory):
                traversed.append(current)

        return current_path, current, depth, traversed

    def _lookup_node(
        self,
        path: str,
        visited: Optional[set[str]] = None,
        depth: int = 0,
        resolve_symlinks: bool = True,
    ) -> Tuple[str, INode]:
        resolved_path, node, _, _ = self._walk_path_components(
            path,
            visited=visited,
            depth=depth,
            resolve_final_symlink=resolve_symlinks,
            allow_missing_last=False,
        )
        return resolved_path, node

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
        path = self._normalize_path(path)
        if path == "/":
            return

        _, _, _, traversed = self._walk_path_components(
            path,
            visited=None,
            depth=0,
            resolve_final_symlink=False,
            allow_missing_last=True,
        )

        for dir_node in traversed:
            self._check_permission(dir_node, Permission.EXECUTE)

    def mkdir(self, path: str, mode: int = 0o755) -> None:
        path = self._normalize_path(path)
        if path == "/":
            raise DirectoryExistsError("Directory already exists: /")
        try:
            self._check_path_permissions(path, Permission.WRITE)
        except PathNotFoundError:
            raise DirectoryNotFoundError(f"Parent directory not found: {path}")
        try:
            _, parent, name = self._lookup_parent(path)
        except PathNotFoundError:
            raise DirectoryNotFoundError(f"Parent directory not found: {path}")
        if parent.get_child(name) is not None:
            raise DirectoryExistsError(f"Directory already exists: {path}")
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
                _, resolved, _, _ = self._resolve_single_symlink(
                    child, current_path, set(), 0
                )
                if not isinstance(resolved, Directory):
                    raise NotADirectoryError(
                        f"{current_path.rstrip('/') + '/' + part} is not a directory"
                    )
                current = resolved
            else:
                raise FileExistsError(
                    f"File exists: {current_path.rstrip('/') + '/' + part}"
                )
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
            _, resolved, _, _ = self._resolve_single_symlink(node, path, set(), 0)
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
            _, resolved, _, _ = self._resolve_single_symlink(node, path, set(), 0)
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
            _, resolved, _, _ = self._resolve_single_symlink(node, path, set(), 0)
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
