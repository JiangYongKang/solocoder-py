import pytest

from solocoder_py.cancel_token import CancelToken


@pytest.fixture
def make_root_token():
    def _make(token_id: str | None = None) -> CancelToken:
        return CancelToken(token_id=token_id)
    return _make


@pytest.fixture
def make_two_level_tree():
    def _make() -> tuple[CancelToken, list[CancelToken]]:
        root = CancelToken(token_id="root")
        child1 = root.create_child(token_id="child1")
        child2 = root.create_child(token_id="child2")
        child3 = root.create_child(token_id="child3")
        return root, [child1, child2, child3]
    return _make


@pytest.fixture
def make_three_level_tree():
    def _make() -> tuple[CancelToken, list[CancelToken], list[CancelToken]]:
        root = CancelToken(token_id="root")
        level1_a = root.create_child(token_id="l1_a")
        level1_b = root.create_child(token_id="l1_b")
        level2_a1 = level1_a.create_child(token_id="l2_a1")
        level2_a2 = level1_a.create_child(token_id="l2_a2")
        level2_b1 = level1_b.create_child(token_id="l2_b1")
        level1 = [level1_a, level1_b]
        level2 = [level2_a1, level2_a2, level2_b1]
        return root, level1, level2
    return _make


@pytest.fixture
def make_deep_nested_tree():
    def _make(depth: int = 10) -> tuple[CancelToken, list[CancelToken]]:
        root = CancelToken(token_id="root")
        chain: list[CancelToken] = []
        current = root
        for i in range(1, depth):
            current = current.create_child(token_id=f"depth_{i}")
            chain.append(current)
        return root, chain
    return _make
