import hashlib
import time

import pytest

from solocoder_py.dirtreediff import (
    DirectoryNode,
    DirectoryTreeSnapshot,
    DirTreeDiffEngine,
    FileNode,
    NodeType,
    SymlinkNode,
)


def compute_hash(content: str, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    h.update(content.encode("utf-8"))
    return h.hexdigest()


@pytest.fixture
def empty_snapshot():
    return DirectoryTreeSnapshot(root_path="/", timestamp=time.time())


@pytest.fixture
def simple_snapshot_a():
    snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=time.time())
    snapshot.add_node_from_dict({
        "path": "src",
        "type": NodeType.DIRECTORY.value,
        "mtime": 1000.0,
    })
    snapshot.add_node_from_dict({
        "path": "src/main.py",
        "type": NodeType.FILE.value,
        "size": 100,
        "mtime": 1000.0,
        "content_hash": compute_hash("print('hello')"),
    })
    snapshot.add_node_from_dict({
        "path": "docs",
        "type": NodeType.DIRECTORY.value,
        "mtime": 1000.0,
    })
    snapshot.add_node_from_dict({
        "path": "docs/readme.md",
        "type": NodeType.FILE.value,
        "size": 200,
        "mtime": 1000.0,
        "content_hash": compute_hash("# README"),
    })
    return snapshot


@pytest.fixture
def simple_snapshot_b():
    snapshot = DirectoryTreeSnapshot(root_path="/", timestamp=time.time() + 100)
    snapshot.add_node_from_dict({
        "path": "src",
        "type": NodeType.DIRECTORY.value,
        "mtime": 1000.0,
    })
    snapshot.add_node_from_dict({
        "path": "src/main.py",
        "type": NodeType.FILE.value,
        "size": 150,
        "mtime": 1100.0,
        "content_hash": compute_hash("print('hello world')"),
    })
    snapshot.add_node_from_dict({
        "path": "src/utils.py",
        "type": NodeType.FILE.value,
        "size": 50,
        "mtime": 1100.0,
        "content_hash": compute_hash("def util(): pass"),
    })
    snapshot.add_node_from_dict({
        "path": "docs/readme.md",
        "type": NodeType.FILE.value,
        "size": 200,
        "mtime": 1000.0,
        "content_hash": compute_hash("# README"),
    })
    return snapshot


@pytest.fixture
def engine(simple_snapshot_a, simple_snapshot_b):
    return DirTreeDiffEngine(
        snapshot_a=simple_snapshot_a, snapshot_b=simple_snapshot_b
    )
