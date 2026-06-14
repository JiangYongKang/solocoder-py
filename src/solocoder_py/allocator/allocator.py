from __future__ import annotations

from typing import Optional

from .exceptions import AllocationFailedError, DeallocationFailedError, InvalidHandleError
from .free_list import FreeList, FreeListNode
from .models import AllocationStrategy, Block, BlockInfo


class MemoryPoolAllocator:
    def __init__(
        self,
        pool_size: int,
        strategy: AllocationStrategy = AllocationStrategy.FIRST_FIT,
    ) -> None:
        if pool_size <= 0:
            raise ValueError("pool_size must be a positive integer")

        self._pool_size = pool_size
        self._pool = bytearray(pool_size)
        self._strategy = strategy

        initial_block = Block(start=0, size=pool_size)
        self._blocks: list[Block] = [initial_block]

        self._free_list = FreeList()
        initial_node = FreeListNode(initial_block)
        initial_block.free_node = initial_node
        self._free_list.insert_sorted(initial_node)

        self._next_handle = 1
        self._handle_to_block: dict[int, Block] = {}

    @property
    def pool_size(self) -> int:
        return self._pool_size

    @property
    def strategy(self) -> AllocationStrategy:
        return self._strategy

    @property
    def total_free(self) -> int:
        return sum(b.size for b in self._blocks if not b.allocated)

    @property
    def total_allocated(self) -> int:
        return sum(b.size for b in self._blocks if b.allocated)

    @property
    def fragmentation_ratio(self) -> float:
        free_blocks = [b for b in self._blocks if not b.allocated]
        if not free_blocks:
            return 0.0
        total_free = sum(b.size for b in free_blocks)
        if total_free == 0:
            return 0.0
        max_free = max(b.size for b in free_blocks)
        return 1.0 - (max_free / total_free)

    def allocate(self, size: int) -> Optional[int]:
        if size <= 0:
            return None

        if size > self._pool_size:
            return None

        if self._strategy == AllocationStrategy.FIRST_FIT:
            node = self._free_list.find_first_fit(size)
        else:
            node = self._free_list.find_best_fit(size)

        if node is None:
            return None

        block = node.block
        self._free_list.remove(node)
        block.free_node = None

        if block.size > size:
            remaining = Block(start=block.start + size, size=block.size - size)
            remaining_node = FreeListNode(remaining)
            remaining.free_node = remaining_node

            idx = self._blocks.index(block)
            block.size = size
            self._blocks.insert(idx + 1, remaining)
            self._free_list.insert_sorted(remaining_node)

        block.allocated = True
        block.written = 0
        handle = self._next_handle
        self._next_handle += 1
        self._handle_to_block[handle] = block

        return handle

    def deallocate(self, handle: int) -> bool:
        if handle not in self._handle_to_block:
            return False

        block = self._handle_to_block.pop(handle)
        if not block.allocated:
            return False

        block.allocated = False

        node = FreeListNode(block)
        block.free_node = node
        self._free_list.insert_sorted(node)

        self._coalesce(block)

        return True

    def _coalesce(self, block: Block) -> None:
        idx = self._blocks.index(block)

        if idx > 0:
            prev_block = self._blocks[idx - 1]
            if not prev_block.allocated:
                self._merge_blocks(prev_block, block)
                block = prev_block
                idx -= 1

        if idx < len(self._blocks) - 1:
            next_block = self._blocks[idx + 1]
            if not next_block.allocated:
                self._merge_blocks(block, next_block)

    def _merge_blocks(self, left: Block, right: Block) -> None:
        if left.free_node is not None:
            self._free_list.remove(left.free_node)
            left.free_node = None

        if right.free_node is not None:
            self._free_list.remove(right.free_node)
            right.free_node = None

        left.size += right.size
        self._blocks.remove(right)

        merged_node = FreeListNode(left)
        left.free_node = merged_node
        self._free_list.insert_sorted(merged_node)

    def compact(self) -> None:
        allocated_blocks = [b for b in self._blocks if b.allocated]

        if not allocated_blocks:
            return

        new_offset = 0
        for block in allocated_blocks:
            if block.start != new_offset:
                self._pool[new_offset:new_offset + block.size] = (
                    self._pool[block.start:block.start + block.size]
                )
                block.start = new_offset
            new_offset += block.size

        self._blocks = list(allocated_blocks)

        if new_offset < self._pool_size:
            free_block = Block(start=new_offset, size=self._pool_size - new_offset)
            self._blocks.append(free_block)

        self._free_list.clear()
        for block in self._blocks:
            if not block.allocated:
                node = FreeListNode(block)
                block.free_node = node
                self._free_list.insert_sorted(node)

    def read(self, handle: int, size: Optional[int] = None) -> Optional[bytes]:
        if handle not in self._handle_to_block:
            return None
        block = self._handle_to_block[handle]
        if size is not None:
            read_size = min(size, block.size)
        else:
            read_size = min(block.written, block.size)
        return bytes(self._pool[block.start:block.start + read_size])

    def write(self, handle: int, data: bytes) -> bool:
        if handle not in self._handle_to_block:
            return False
        block = self._handle_to_block[handle]
        write_size = min(len(data), block.size)
        self._pool[block.start:block.start + write_size] = data[:write_size]
        if write_size > block.written:
            block.written = write_size
        return True

    def block_info(self, handle: int) -> Optional[BlockInfo]:
        if handle not in self._handle_to_block:
            return None
        block = self._handle_to_block[handle]
        return BlockInfo(start=block.start, size=block.size, allocated=block.allocated, written=block.written)

    def allocated_count(self) -> int:
        return len(self._handle_to_block)

    def free_list_info(self) -> list[BlockInfo]:
        result = []
        for node in self._free_list.nodes():
            result.append(
                BlockInfo(start=node.block.start, size=node.block.size, allocated=False)
            )
        return result

    def all_blocks_info(self) -> list[BlockInfo]:
        return [
            BlockInfo(start=b.start, size=b.size, allocated=b.allocated)
            for b in self._blocks
        ]
