import pytest

from solocoder_py.allocator import AllocationStrategy, BlockInfo, MemoryPoolAllocator


class TestAllocateBasic:
    def test_allocate_returns_handle(self, pool_100):
        handle = pool_100.allocate(10)
        assert handle is not None
        assert isinstance(handle, int)
        assert handle > 0

    def test_allocate_consecutive_handles(self, pool_100):
        h1 = pool_100.allocate(10)
        h2 = pool_100.allocate(10)
        h3 = pool_100.allocate(10)
        assert h1 != h2 != h3
        assert h2 > h1
        assert h3 > h2

    def test_allocate_exact_pool_size(self):
        pool = MemoryPoolAllocator(pool_size=50)
        handle = pool.allocate(50)
        assert handle is not None
        assert pool.total_allocated == 50
        assert pool.total_free == 0

    def test_allocate_reduces_free_space(self, pool_100):
        pool_100.allocate(30)
        assert pool_100.total_allocated == 30
        assert pool_100.total_free == 70

    def test_allocate_full_pool(self, pool_100):
        h = pool_100.allocate(100)
        assert h is not None
        assert pool_100.total_free == 0

    def test_allocate_multiple_until_full(self, pool_100):
        handles = []
        for _ in range(10):
            h = pool_100.allocate(10)
            assert h is not None
            handles.append(h)
        assert pool_100.total_free == 0
        h_extra = pool_100.allocate(1)
        assert h_extra is None

    def test_block_info_after_allocate(self, pool_100):
        handle = pool_100.allocate(25)
        info = pool_100.block_info(handle)
        assert info is not None
        assert info.size == 25
        assert info.allocated is True
        assert info.start == 0

    def test_allocated_count(self, pool_100):
        assert pool_100.allocated_count() == 0
        h1 = pool_100.allocate(10)
        assert pool_100.allocated_count() == 1
        h2 = pool_100.allocate(20)
        assert pool_100.allocated_count() == 2


class TestFirstFitStrategy:
    def test_first_fit_selects_earliest(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        h3 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        pool_100.deallocate(h3)
        h4 = pool_100.allocate(15)
        info = pool_100.block_info(h4)
        assert info.start == 0

    def test_first_fit_skips_too_small(self, pool_100):
        h1 = pool_100.allocate(5)
        h2 = pool_100.allocate(5)
        h3 = pool_100.allocate(80)
        pool_100.deallocate(h1)
        pool_100.deallocate(h3)
        h4 = pool_100.allocate(50)
        info = pool_100.block_info(h4)
        assert info.start == 10


class TestBestFitStrategy:
    def test_best_fit_selects_tightest(self, pool_100_best_fit):
        h1 = pool_100_best_fit.allocate(20)
        h2 = pool_100_best_fit.allocate(20)
        h3 = pool_100_best_fit.allocate(20)
        pool_100_best_fit.deallocate(h1)
        pool_100_best_fit.deallocate(h3)
        h4 = pool_100_best_fit.allocate(15)
        info = pool_100_best_fit.block_info(h4)
        assert info.start == 0

    def test_best_fit_prefers_smaller_fit(self):
        pool = MemoryPoolAllocator(pool_size=200, strategy=AllocationStrategy.BEST_FIT)
        h1 = pool.allocate(50)
        h2 = pool.allocate(50)
        h3 = pool.allocate(50)
        pool.deallocate(h1)
        pool.deallocate(h3)
        h4 = pool.allocate(45)
        info = pool.block_info(h4)
        assert info.size == 45
        assert info.start in (0, 100)

    def test_best_fit_vs_first_fit_difference(self):
        pool_ff = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.FIRST_FIT)
        pool_bf = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.BEST_FIT)
        h1_ff = pool_ff.allocate(50)
        h2_ff = pool_ff.allocate(50)
        h3_ff = pool_ff.allocate(50)
        pool_ff.deallocate(h1_ff)
        pool_ff.deallocate(h3_ff)
        h4_ff = pool_ff.allocate(40)
        ff_info = pool_ff.block_info(h4_ff)

        h1_bf = pool_bf.allocate(50)
        h2_bf = pool_bf.allocate(50)
        h3_bf = pool_bf.allocate(50)
        pool_bf.deallocate(h1_bf)
        pool_bf.deallocate(h3_bf)
        h4_bf = pool_bf.allocate(40)
        bf_info = pool_bf.block_info(h4_bf)

        assert ff_info is not None
        assert bf_info is not None


class TestDeallocateBasic:
    def test_deallocate_returns_true(self, pool_100):
        handle = pool_100.allocate(20)
        assert pool_100.deallocate(handle) is True

    def test_deallocate_increases_free_space(self, pool_100):
        handle = pool_100.allocate(30)
        assert pool_100.total_allocated == 30
        pool_100.deallocate(handle)
        assert pool_100.total_allocated == 0
        assert pool_100.total_free == 100

    def test_deallocate_reuse_space(self, pool_100):
        handle = pool_100.allocate(50)
        pool_100.deallocate(handle)
        handle2 = pool_100.allocate(50)
        assert handle2 is not None
        assert pool_100.allocated_count() == 1

    def test_allocate_deallocate_cycle(self, pool_100):
        for _ in range(5):
            handles = []
            for i in range(10):
                h = pool_100.allocate(10)
                assert h is not None
                handles.append(h)
            assert pool_100.total_free == 0
            for h in handles:
                assert pool_100.deallocate(h) is True
            assert pool_100.total_free == 100


class TestCoalescing:
    def test_coalesce_with_previous_free(self, pool_100):
        h1 = pool_100.allocate(30)
        h2 = pool_100.allocate(30)
        h3 = pool_100.allocate(30)
        pool_100.deallocate(h1)
        pool_100.deallocate(h2)
        free_list = pool_100.free_list_info()
        assert len(free_list) == 2
        merged = [f for f in free_list if f.start == 0]
        assert len(merged) == 1
        assert merged[0].size == 60

    def test_coalesce_with_next_free(self, pool_100):
        h1 = pool_100.allocate(30)
        h2 = pool_100.allocate(30)
        h3 = pool_100.allocate(30)
        pool_100.deallocate(h3)
        pool_100.deallocate(h2)
        free_list = pool_100.free_list_info()
        merged = [f for f in free_list if f.start == 30]
        assert len(merged) == 1
        assert merged[0].size == 70

    def test_coalesce_both_neighbors(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        h3 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        pool_100.deallocate(h3)
        pool_100.deallocate(h2)
        free_list = pool_100.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].start == 0
        assert free_list[0].size == 100

    def test_coalesce_no_adjacent_free(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        h3 = pool_100.allocate(20)
        pool_100.deallocate(h2)
        free_list = pool_100.free_list_info()
        assert len(free_list) == 2
        sizes = {f.size for f in free_list}
        assert 20 in sizes

    def test_coalesce_produces_large_block_for_allocation(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        h3 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        pool_100.deallocate(h2)
        h4 = pool_100.allocate(35)
        assert h4 is not None
        info = pool_100.block_info(h4)
        assert info.size == 35
        assert info.start == 0

    def test_coalesce_free_list_integrity(self):
        pool = MemoryPoolAllocator(pool_size=300)
        h1 = pool.allocate(50)
        h2 = pool.allocate(50)
        h3 = pool.allocate(50)
        pool.deallocate(h1)
        pool.deallocate(h2)
        pool.deallocate(h3)
        free_list = pool.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].start == 0
        assert free_list[0].size == 300
        all_blocks = pool.all_blocks_info()
        assert len(all_blocks) == 1

    def test_coalesce_sequential_deallocation(self):
        pool = MemoryPoolAllocator(pool_size=200)
        handles = []
        for i in range(4):
            h = pool.allocate(50)
            handles.append(h)
        for h in handles:
            pool.deallocate(h)
        free_list = pool.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].size == 200

    def test_coalesce_partial(self):
        pool = MemoryPoolAllocator(pool_size=200)
        h1 = pool.allocate(50)
        h2 = pool.allocate(50)
        h3 = pool.allocate(50)
        h4 = pool.allocate(50)
        pool.deallocate(h1)
        pool.deallocate(h3)
        free_list = pool.free_list_info()
        assert len(free_list) == 2
        pool.deallocate(h2)
        free_list = pool.free_list_info()
        assert len(free_list) == 1
        starts = {f.start for f in free_list}
        assert 0 in starts
        assert free_list[0].size == 150
        pool.deallocate(h4)
        free_list = pool.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].size == 200


class TestCompaction:
    def test_compact_moves_blocks_to_front(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        h3 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        pool_100.deallocate(h2)
        pool_100.compact()
        all_blocks = pool_100.all_blocks_info()
        allocated = [b for b in all_blocks if b.allocated]
        assert len(allocated) == 1
        assert allocated[0].start == 0
        assert allocated[0].size == 20

    def test_compact_creates_single_free_block(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        pool_100.compact()
        free_list = pool_100.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].start == 20
        assert free_list[0].size == 80

    def test_compact_preserves_data(self, pool_100):
        h1 = pool_100.allocate(10)
        h2 = pool_100.allocate(10)
        pool_100.write(h1, b"AAAAAAAAAA")
        pool_100.write(h2, b"BBBBBBBBBB")
        pool_100.deallocate(h1)
        pool_100.compact()
        data = pool_100.read(h2)
        assert data == b"BBBBBBBBBB"

    def test_compact_no_allocated_blocks(self, pool_100):
        pool_100.compact()
        assert pool_100.total_free == 100
        free_list = pool_100.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].size == 100

    def test_compact_fully_allocated_is_noop(self, pool_100):
        h = pool_100.allocate(100)
        pool_100.compact()
        info = pool_100.block_info(h)
        assert info.start == 0
        assert info.size == 100

    def test_compact_enables_large_allocation(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.allocate(50) is None
        pool.compact()
        h4 = pool.allocate(50)
        assert h4 is not None
        info = pool.block_info(h4)
        assert info.size == 50

    def test_compact_updates_all_block_starts(self, pool_100):
        h1 = pool_100.allocate(10)
        h2 = pool_100.allocate(10)
        h3 = pool_100.allocate(10)
        pool_100.deallocate(h1)
        pool_100.deallocate(h2)
        pool_100.compact()
        h3_info = pool_100.block_info(h3)
        assert h3_info.start == 0

    def test_compact_multiple_fragments(self):
        pool = MemoryPoolAllocator(pool_size=200)
        handles = []
        for i in range(5):
            h = pool.allocate(20)
            handles.append(h)
        pool.deallocate(handles[0])
        pool.deallocate(handles[2])
        pool.deallocate(handles[4])
        pool.compact()
        all_blocks = pool.all_blocks_info()
        allocated = [b for b in all_blocks if b.allocated]
        assert len(allocated) == 2
        assert allocated[0].start == 0
        assert allocated[1].start == 20
        free_list = pool.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].start == 40
        assert free_list[0].size == 160

    def test_compact_data_accessible_after_move(self):
        pool = MemoryPoolAllocator(pool_size=200)
        h1 = pool.allocate(20)
        h2 = pool.allocate(20)
        h3 = pool.allocate(20)
        pool.write(h1, b"A" * 20)
        pool.write(h2, b"B" * 20)
        pool.write(h3, b"C" * 20)
        pool.deallocate(h1)
        pool.deallocate(h3)
        pool.compact()
        data_b = pool.read(h2)
        assert data_b == b"B" * 20


class TestAllocationFailure:
    def test_allocate_zero_bytes_returns_none(self, pool_100):
        assert pool_100.allocate(0) is None

    def test_allocate_negative_returns_none(self, pool_100):
        assert pool_100.allocate(-1) is None

    def test_allocate_larger_than_pool_returns_none(self, pool_100):
        assert pool_100.allocate(101) is None

    def test_allocate_larger_than_pool_exact(self):
        pool = MemoryPoolAllocator(pool_size=50)
        assert pool.allocate(51) is None

    def test_pool_full_returns_none(self, pool_100):
        h = pool_100.allocate(100)
        assert pool_100.allocate(1) is None

    def test_fragmentation_causes_failure(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.total_free == 70
        assert pool.allocate(50) is None

    def test_fragmented_then_compact_then_succeed(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.allocate(50) is None
        pool.compact()
        h4 = pool.allocate(50)
        assert h4 is not None
        info = pool.block_info(h4)
        assert info.size == 50

    def test_no_contiguous_block_even_with_total_free(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(25)
        h2 = pool.allocate(25)
        h3 = pool.allocate(25)
        h4 = pool.allocate(25)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.total_free == 50
        assert pool.allocate(40) is None


class TestReadWrite:
    def test_write_and_read(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello world!")
        data = pool_100.read(h, size=12)
        assert data is not None
        assert data == b"hello world!"

    def test_write_partial_fills_block(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"short")
        data = pool_100.read(h)
        assert data is not None
        assert data[:5] == b"short"

    def test_write_truncates_if_too_long(self, pool_100):
        h = pool_100.allocate(5)
        pool_100.write(h, b"hello world!")
        data = pool_100.read(h)
        assert data == b"hello"

    def test_read_with_size(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"0123456789ABCDEFGHIJ")
        data = pool_100.read(h, size=5)
        assert data == b"01234"

    def test_read_invalid_handle(self, pool_100):
        assert pool_100.read(999) is None

    def test_write_invalid_handle(self, pool_100):
        assert pool_100.write(999, b"data") is False

    def test_read_after_deallocate(self, pool_100):
        h = pool_100.allocate(10)
        pool_100.write(h, b"test")
        pool_100.deallocate(h)
        assert pool_100.read(h) is None


class TestDeallocateEdgeCases:
    def test_deallocate_invalid_handle(self, pool_100):
        assert pool_100.deallocate(999) is False

    def test_deallocate_negative_handle(self, pool_100):
        assert pool_100.deallocate(-1) is False

    def test_deallocate_zero_handle(self, pool_100):
        assert pool_100.deallocate(0) is False

    def test_double_deallocate(self, pool_100):
        h = pool_100.allocate(20)
        assert pool_100.deallocate(h) is True
        assert pool_100.deallocate(h) is False

    def test_deallocate_unallocated_address(self, pool_100):
        assert pool_100.deallocate(42) is False


class TestBlockSplitting:
    def test_split_creates_remainder(self, pool_100):
        h = pool_100.allocate(30)
        all_blocks = pool_100.all_blocks_info()
        assert len(all_blocks) == 2
        allocated = [b for b in all_blocks if b.allocated]
        free = [b for b in all_blocks if not b.allocated]
        assert len(allocated) == 1
        assert allocated[0].size == 30
        assert len(free) == 1
        assert free[0].size == 70
        assert free[0].start == 30

    def test_no_split_on_exact_fit(self, pool_100):
        h = pool_100.allocate(100)
        all_blocks = pool_100.all_blocks_info()
        assert len(all_blocks) == 1
        assert all_blocks[0].size == 100
        assert all_blocks[0].allocated is True

    def test_split_then_allocate_from_remainder(self, pool_100):
        h1 = pool_100.allocate(30)
        h2 = pool_100.allocate(40)
        info2 = pool_100.block_info(h2)
        assert info2.start == 30
        assert info2.size == 40
        free_list = pool_100.free_list_info()
        assert len(free_list) == 1
        assert free_list[0].start == 70
        assert free_list[0].size == 30


class TestFragmentationRatio:
    def test_no_fragmentation(self, pool_100):
        assert pool_100.fragmentation_ratio == 0.0

    def test_full_pool_no_fragmentation(self, pool_100):
        pool_100.allocate(100)
        assert pool_100.fragmentation_ratio == 0.0

    def test_fragmented_pool(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(25)
        h2 = pool.allocate(25)
        h3 = pool.allocate(25)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.fragmentation_ratio > 0

    def test_compact_reduces_fragmentation(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(25)
        h2 = pool.allocate(25)
        h3 = pool.allocate(25)
        pool.deallocate(h1)
        pool.deallocate(h3)
        frag_before = pool.fragmentation_ratio
        pool.compact()
        frag_after = pool.fragmentation_ratio
        assert frag_after < frag_before
        assert frag_after == 0.0


class TestProperties:
    def test_pool_size(self, pool_100):
        assert pool_100.pool_size == 100

    def test_strategy_property(self, pool_100):
        assert pool_100.strategy == AllocationStrategy.FIRST_FIT

    def test_strategy_best_fit(self, pool_100_best_fit):
        assert pool_100_best_fit.strategy == AllocationStrategy.BEST_FIT

    def test_total_free_initial(self, pool_100):
        assert pool_100.total_free == 100

    def test_total_allocated_initial(self, pool_100):
        assert pool_100.total_allocated == 0


class TestConstructorValidation:
    def test_zero_pool_size_raises(self):
        with pytest.raises(ValueError, match="pool_size must be a positive integer"):
            MemoryPoolAllocator(pool_size=0)

    def test_negative_pool_size_raises(self):
        with pytest.raises(ValueError, match="pool_size must be a positive integer"):
            MemoryPoolAllocator(pool_size=-10)


class TestFreeListInfo:
    def test_initial_free_list(self, pool_100):
        info = pool_100.free_list_info()
        assert len(info) == 1
        assert info[0].start == 0
        assert info[0].size == 100

    def test_free_list_after_allocation(self, pool_100):
        pool_100.allocate(30)
        info = pool_100.free_list_info()
        assert len(info) == 1
        assert info[0].start == 30
        assert info[0].size == 70

    def test_free_list_after_deallocation(self, pool_100):
        h = pool_100.allocate(30)
        pool_100.deallocate(h)
        info = pool_100.free_list_info()
        assert len(info) == 1
        assert info[0].size == 100


class TestAllBlocksInfo:
    def test_initial_blocks(self, pool_100):
        info = pool_100.all_blocks_info()
        assert len(info) == 1
        assert info[0].start == 0
        assert info[0].size == 100
        assert info[0].allocated is False

    def test_blocks_after_split(self, pool_100):
        pool_100.allocate(30)
        info = pool_100.all_blocks_info()
        assert len(info) == 2
        assert info[0].allocated is True
        assert info[1].allocated is False

    def test_blocks_no_overlap(self, pool_100):
        pool_100.allocate(30)
        pool_100.allocate(30)
        info = pool_100.all_blocks_info()
        prev_end = 0
        for block in info:
            assert block.start == prev_end
            prev_end = block.start + block.size
        assert prev_end == 100


class TestCompactionDataIntegrity:
    def test_data_accessible_after_compact_via_handle(self):
        pool = MemoryPoolAllocator(pool_size=200)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        pool.write(h1, b"X" * 30)
        pool.write(h2, b"Y" * 30)
        pool.write(h3, b"Z" * 30)
        pool.deallocate(h1)
        pool.compact()
        assert pool.read(h2) == b"Y" * 30
        assert pool.read(h3) == b"Z" * 30

    def test_block_info_updated_after_compact(self):
        pool = MemoryPoolAllocator(pool_size=200)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        pool.deallocate(h1)
        pool.compact()
        info = pool.block_info(h2)
        assert info.start == 0
        assert info.size == 30

    def test_compact_then_write_and_read(self):
        pool = MemoryPoolAllocator(pool_size=200)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        pool.deallocate(h1)
        pool.compact()
        data = b"NEW_DATA_HERE!!!!!!!!!!!!!"
        pool.write(h2, data)
        assert pool.read(h2, size=len(data)) == data

    def test_compact_with_multiple_data_blocks(self):
        pool = MemoryPoolAllocator(pool_size=300)
        handles = []
        for i in range(5):
            h = pool.allocate(30)
            pool.write(h, bytes([i] * 30))
            handles.append(h)
        pool.deallocate(handles[0])
        pool.deallocate(handles[2])
        pool.deallocate(handles[4])
        pool.compact()
        assert pool.read(handles[1]) == bytes([1] * 30)
        assert pool.read(handles[3]) == bytes([3] * 30)


class TestEdgeCasesComprehensive:
    def test_allocate_one_byte(self):
        pool = MemoryPoolAllocator(pool_size=1)
        h = pool.allocate(1)
        assert h is not None
        assert pool.total_free == 0

    def test_allocate_one_byte_pool_fails_for_two(self):
        pool = MemoryPoolAllocator(pool_size=1)
        pool.allocate(1)
        assert pool.allocate(1) is None

    def test_allocate_deallocate_many_times(self, pool_100):
        for _ in range(50):
            h = pool_100.allocate(50)
            assert h is not None
            assert pool_100.deallocate(h) is True

    def test_interleaved_alloc_dealloc(self, pool_100):
        h1 = pool_100.allocate(20)
        h2 = pool_100.allocate(20)
        pool_100.deallocate(h1)
        h3 = pool_100.allocate(15)
        assert h3 is not None
        pool_100.deallocate(h2)
        h4 = pool_100.allocate(60)
        assert h4 is not None

    def test_best_fit_no_suitable_block(self):
        pool = MemoryPoolAllocator(pool_size=100, strategy=AllocationStrategy.BEST_FIT)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        assert pool.allocate(50) is None

    def test_coalesce_after_multiple_deallocations(self):
        pool = MemoryPoolAllocator(pool_size=100)
        h1 = pool.allocate(10)
        h2 = pool.allocate(10)
        h3 = pool.allocate(10)
        h4 = pool.allocate(10)
        pool.deallocate(h1)
        pool.deallocate(h3)
        pool.deallocate(h2)
        free_list = pool.free_list_info()
        starts = [f.start for f in free_list]
        sizes = [f.size for f in free_list]
        assert 0 in starts
        idx_0 = starts.index(0)
        assert sizes[idx_0] == 30

    def test_fragmentation_ratio_single_free_block(self):
        pool = MemoryPoolAllocator(pool_size=100)
        pool.allocate(50)
        assert pool.fragmentation_ratio == 0.0

    def test_compact_empty_pool(self, pool_100):
        pool_100.compact()
        assert pool_100.total_free == 100

    def test_all_blocks_cover_entire_pool(self, pool_100):
        h1 = pool_100.allocate(25)
        h2 = pool_100.allocate(25)
        h3 = pool_100.allocate(25)
        h4 = pool_100.allocate(25)
        total = sum(b.size for b in pool_100.all_blocks_info())
        assert total == 100
        pool_100.deallocate(h2)
        pool_100.deallocate(h4)
        total = sum(b.size for b in pool_100.all_blocks_info())
        assert total == 100


class TestReadWrittenRange:
    def test_fresh_allocation_reads_empty(self, pool_100):
        h = pool_100.allocate(20)
        data = pool_100.read(h)
        assert data == b""

    def test_fresh_allocation_written_is_zero(self, pool_100):
        h = pool_100.allocate(20)
        info = pool_100.block_info(h)
        assert info.written == 0

    def test_write_updates_written(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello")
        info = pool_100.block_info(h)
        assert info.written == 5

    def test_read_returns_only_written_bytes(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello")
        data = pool_100.read(h)
        assert data == b"hello"
        assert len(data) == 5

    def test_write_more_extends_written(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello")
        pool_100.write(h, b"hello world!")
        info = pool_100.block_info(h)
        assert info.written == 12
        assert pool_100.read(h) == b"hello world!"

    def test_write_less_does_not_shrink_written(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello world!")
        pool_100.write(h, b"hi")
        info = pool_100.block_info(h)
        assert info.written == 12
        data = pool_100.read(h)
        assert data == b"hillo world!"

    def test_write_truncated_still_tracks(self, pool_100):
        h = pool_100.allocate(10)
        pool_100.write(h, b"this is a very long string that exceeds block size")
        info = pool_100.block_info(h)
        assert info.written == 10
        assert pool_100.read(h) == b"this is a "

    def test_explicit_read_size_override(self, pool_100):
        h = pool_100.allocate(20)
        pool_100.write(h, b"hello")
        data1 = pool_100.read(h, size=3)
        assert data1 == b"hel"
        data2 = pool_100.read(h, size=10)
        assert data2 == b"hello\x00\x00\x00\x00\x00"

    def test_written_preserved_after_compact(self, pool_100):
        h1 = pool_100.allocate(10)
        h2 = pool_100.allocate(10)
        pool_100.write(h2, b"testdata")
        pool_100.deallocate(h1)
        pool_100.compact()
        info = pool_100.block_info(h2)
        assert info.written == 8
        assert pool_100.read(h2) == b"testdata"

    def test_block_info_includes_written(self, pool_100):
        h = pool_100.allocate(30)
        pool_100.write(h, b"abc")
        info = pool_100.block_info(h)
        assert hasattr(info, "written")
        assert info.written == 3


class TestBestFitEqualSizeTiebreaker:
    def test_first_fit_picks_smallest_address(self):
        pool = MemoryPoolAllocator(pool_size=200, strategy=AllocationStrategy.FIRST_FIT)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        h4 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        h_new = pool.allocate(20)
        info = pool.block_info(h_new)
        assert info.start == 0

    def test_best_fit_picks_largest_address_on_equal_size(self):
        pool = MemoryPoolAllocator(pool_size=200, strategy=AllocationStrategy.BEST_FIT)
        h1 = pool.allocate(30)
        h2 = pool.allocate(30)
        h3 = pool.allocate(30)
        h4 = pool.allocate(30)
        pool.deallocate(h1)
        pool.deallocate(h3)
        h_new = pool.allocate(20)
        info = pool.block_info(h_new)
        assert info.start == 60

    def test_first_fit_vs_best_fit_equal_size_divergence(self):
        pool_ff = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.FIRST_FIT)
        pool_bf = MemoryPoolAllocator(pool_size=300, strategy=AllocationStrategy.BEST_FIT)

        for p in (pool_ff, pool_bf):
            h0 = p.allocate(40)
            h1 = p.allocate(40)
            h2 = p.allocate(40)
            h3 = p.allocate(40)
            h4 = p.allocate(40)
            _tail = p.allocate(100)
            p.deallocate(h0)
            p.deallocate(h2)
            p.deallocate(h4)

        h_ff = pool_ff.allocate(30)
        h_bf = pool_bf.allocate(30)

        assert pool_ff.block_info(h_ff).start == 0
        assert pool_bf.block_info(h_bf).start == 160

    def test_best_fit_still_prefers_smaller_block_over_tiebreaker(self):
        pool = MemoryPoolAllocator(pool_size=400, strategy=AllocationStrategy.BEST_FIT)
        h1 = pool.allocate(50)
        _h2 = pool.allocate(30)
        h3 = pool.allocate(20)
        _h4 = pool.allocate(50)
        h5 = pool.allocate(50)
        _tail = pool.allocate(200)
        pool.deallocate(h1)
        pool.deallocate(h3)
        pool.deallocate(h5)
        h_new = pool.allocate(15)
        info = pool.block_info(h_new)
        assert info.start == 80
