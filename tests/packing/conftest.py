import pytest

from solocoder_py.packing import Bin, Item, PackingScheduler


@pytest.fixture
def make_item():
    def _make_item(size: int, name: str | None = None) -> Item:
        return Item.create(size=size, name=name)
    return _make_item


@pytest.fixture
def make_bin():
    def _make_bin(capacity: int, name: str | None = None) -> Bin:
        return Bin.create(capacity=capacity, name=name)
    return _make_bin


@pytest.fixture
def make_scheduler():
    def _make_scheduler() -> PackingScheduler:
        return PackingScheduler()
    return _make_scheduler
