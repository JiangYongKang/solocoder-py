from __future__ import annotations

from typing import Any, List, Optional

from .exceptions import DuplicateValueError, ValueNotFoundError
from .node import TreeNode


class BinarySearchTree:
    def __init__(self) -> None:
        self._root: Optional[TreeNode] = None
        self._size: int = 0

    @property
    def root(self) -> Optional[TreeNode]:
        return self._root

    def is_empty(self) -> bool:
        return self._root is None

    def size(self) -> int:
        return self._size

    def insert(self, value: Any) -> None:
        if self._root is None:
            self._root = TreeNode(value=value)
            self._size = 1
            return

        self._insert_recursive(self._root, value)

    def _insert_recursive(self, node: TreeNode, value: Any) -> None:
        if value == node.value:
            raise DuplicateValueError(f"Value {value} already exists in the tree")
        elif value < node.value:
            if node.left is None:
                node.left = TreeNode(value=value)
                self._size += 1
            else:
                self._insert_recursive(node.left, value)
        else:
            if node.right is None:
                node.right = TreeNode(value=value)
                self._size += 1
            else:
                self._insert_recursive(node.right, value)

    def search(self, value: Any) -> bool:
        return self._search_recursive(self._root, value)

    def _search_recursive(self, node: Optional[TreeNode], value: Any) -> bool:
        if node is None:
            return False
        if value == node.value:
            return True
        elif value < node.value:
            return self._search_recursive(node.left, value)
        else:
            return self._search_recursive(node.right, value)

    def delete(self, value: Any) -> None:
        if not self.search(value):
            raise ValueNotFoundError(f"Value {value} not found in the tree")

        self._root = self._delete_recursive(self._root, value)
        self._size -= 1

    def _delete_recursive(self, node: Optional[TreeNode], value: Any) -> Optional[TreeNode]:
        if node is None:
            return None

        if value < node.value:
            node.left = self._delete_recursive(node.left, value)
            return node
        elif value > node.value:
            node.right = self._delete_recursive(node.right, value)
            return node
        else:
            if node.left is None and node.right is None:
                return None
            elif node.left is None:
                return node.right
            elif node.right is None:
                return node.left
            else:
                successor = self._find_min(node.right)
                node.value = successor.value
                node.right = self._delete_recursive(node.right, successor.value)
                return node

    def _find_min(self, node: TreeNode) -> TreeNode:
        current = node
        while current.left is not None:
            current = current.left
        return current

    def preorder_traversal(self) -> List[Any]:
        result: List[Any] = []
        self._preorder_recursive(self._root, result)
        return result

    def _preorder_recursive(self, node: Optional[TreeNode], result: List[Any]) -> None:
        if node is None:
            return
        result.append(node.value)
        self._preorder_recursive(node.left, result)
        self._preorder_recursive(node.right, result)

    def inorder_traversal(self) -> List[Any]:
        result: List[Any] = []
        self._inorder_recursive(self._root, result)
        return result

    def _inorder_recursive(self, node: Optional[TreeNode], result: List[Any]) -> None:
        if node is None:
            return
        self._inorder_recursive(node.left, result)
        result.append(node.value)
        self._inorder_recursive(node.right, result)

    def postorder_traversal(self) -> List[Any]:
        result: List[Any] = []
        self._postorder_recursive(self._root, result)
        return result

    def _postorder_recursive(self, node: Optional[TreeNode], result: List[Any]) -> None:
        if node is None:
            return
        self._postorder_recursive(node.left, result)
        self._postorder_recursive(node.right, result)
        result.append(node.value)

    def clear(self) -> None:
        self._root = None
        self._size = 0
