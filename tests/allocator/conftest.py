import pytest

from solocoder_py.allocator import AllocationStrategy, MemoryPoolAllocator


@pytest.fixture
def pool_100() -> MemoryPoolAllocator:
    return MemoryPoolAllocator(pool_size=100)


@pytest.fixture
def pool_100_best_fit() -> MemoryPoolAllocator:
    return MemoryPoolAllocator(pool_size=100, strategy=AllocationStrategy.BEST_FIT)


@pytest.fixture
def pool_1000() -> MemoryPoolAllocator:
    return MemoryPoolAllocator(pool_size=1000)
