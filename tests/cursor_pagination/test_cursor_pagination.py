from __future__ import annotations

import time

import pytest

from solocoder_py.cursor_pagination import (
    CursorExpiredError,
    CursorPaginationEngine,
    CursorTamperedError,
    DecodedCursor,
    Direction,
    InvalidCursorError,
    InvalidDirectionError,
    InvalidPageSizeError,
    InvalidSortFieldError,
    PageResult,
    PaginationConfig,
    SortField,
    SortOrder,
)


# ============================================================
# 正常流程测试
# ============================================================

class TestNormalFlowForwardPagination:
    def test_first_page_no_cursor(self, basic_engine):
        page = basic_engine.paginate(page_size=3)
        assert isinstance(page, PageResult)
        assert len(page.data) == 3
        assert [r["id"] for r in page.data] == [1, 2, 3]
        assert page.has_next is True
        assert page.has_prev is False
        assert page.page_size == 3
        assert page.start_cursor is not None
        assert page.end_cursor is not None

    def test_second_page_using_end_cursor(self, basic_engine):
        page1 = basic_engine.paginate(page_size=3)
        page2 = basic_engine.paginate(page_size=3, cursor=page1.end_cursor, direction="next")
        assert len(page2.data) == 3
        assert [r["id"] for r in page2.data] == [4, 5, 6]
        assert page2.has_next is True
        assert page2.has_prev is True

    def test_sequential_forward_pagination(self, basic_engine):
        all_ids = []
        cursor = None
        has_more = True
        page_count = 0

        while has_more:
            page = basic_engine.paginate(page_size=3, cursor=cursor, direction="next")
            all_ids.extend(r["id"] for r in page.data)
            cursor = page.end_cursor
            has_more = page.has_next
            page_count += 1

        assert page_count == 4
        assert all_ids == list(range(1, 11))

    def test_last_page_partial(self, basic_engine):
        page1 = basic_engine.paginate(page_size=3)
        page2 = basic_engine.paginate(page_size=3, cursor=page1.end_cursor, direction="next")
        page3 = basic_engine.paginate(page_size=3, cursor=page2.end_cursor, direction="next")
        page4 = basic_engine.paginate(page_size=3, cursor=page3.end_cursor, direction="next")

        assert len(page4.data) == 1
        assert [r["id"] for r in page4.data] == [10]
        assert page4.has_next is False
        assert page4.has_prev is True

    def test_exact_pages_no_partial(self, sample_data_5):
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"])
        page1 = engine.paginate(page_size=5)
        assert len(page1.data) == 5
        assert page1.has_next is False
        assert page1.has_prev is False


class TestNormalFlowBackwardPagination:
    def test_back_to_previous_page(self, basic_engine):
        page1 = basic_engine.paginate(page_size=3)
        page2 = basic_engine.paginate(page_size=3, cursor=page1.end_cursor, direction="next")
        page_prev = basic_engine.paginate(page_size=3, cursor=page2.start_cursor, direction="prev")

        assert [r["id"] for r in page_prev.data] == [1, 2, 3]
        assert page_prev.has_next is True
        assert page_prev.has_prev is False

    def test_round_trip_pagination(self, basic_engine):
        page1 = basic_engine.paginate(page_size=2)
        page2 = basic_engine.paginate(page_size=2, cursor=page1.end_cursor, direction="next")
        page3 = basic_engine.paginate(page_size=2, cursor=page2.end_cursor, direction="next")

        back_to_2 = basic_engine.paginate(page_size=2, cursor=page3.start_cursor, direction="prev")
        assert [r["id"] for r in back_to_2.data] == [3, 4]
        assert back_to_2.data == page2.data

        back_to_1 = basic_engine.paginate(page_size=2, cursor=back_to_2.start_cursor, direction="prev")
        assert [r["id"] for r in back_to_1.data] == [1, 2]
        assert back_to_1.data == page1.data

    def test_backward_from_middle(self, basic_engine):
        page1 = basic_engine.paginate(page_size=4)
        page2 = basic_engine.paginate(page_size=4, cursor=page1.end_cursor, direction="next")
        back = basic_engine.paginate(page_size=2, cursor=page2.start_cursor, direction="prev")

        assert len(back.data) == 2
        assert [r["id"] for r in back.data] == [3, 4]
        assert back.has_prev is True
        assert back.has_next is True

    def test_forward_backward_consistency(self, sample_data_large):
        engine = CursorPaginationEngine(data=sample_data_large, sort_fields=["id"])

        page1 = engine.paginate(page_size=10)
        page2 = engine.paginate(page_size=10, cursor=page1.end_cursor, direction="next")
        page3 = engine.paginate(page_size=10, cursor=page2.end_cursor, direction="next")

        back_to_2 = engine.paginate(page_size=10, cursor=page3.start_cursor, direction="prev")
        assert back_to_2.data == page2.data

        back_to_1 = engine.paginate(page_size=10, cursor=back_to_2.start_cursor, direction="prev")
        assert back_to_1.data == page1.data

    def test_prev_from_last_page(self, basic_engine):
        pages = []
        cursor = None
        while True:
            page = basic_engine.paginate(page_size=3, cursor=cursor, direction="next")
            pages.append(page)
            if not page.has_next:
                break
            cursor = page.end_cursor

        last_page = pages[-1]
        prev_page = basic_engine.paginate(
            page_size=3, cursor=last_page.start_cursor, direction="prev"
        )
        assert prev_page.data == pages[-2].data

    def test_direction_prev_no_cursor(self, sample_data_5):
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"])
        page = engine.paginate(page_size=3, direction="prev")
        assert [r["id"] for r in page.data] == [3, 4, 5]
        assert page.has_prev is True
        assert page.has_next is False


# ============================================================
# 排序测试
# ============================================================

class TestMultiFieldSort:
    def test_desc_then_asc_sort(self, sample_data_10):
        data = list(sample_data_10)
        data.append({"id": 11, "name": "user_11", "score": 91})
        engine = CursorPaginationEngine(
            data=data,
            sort_fields=[SortField("score", SortOrder.DESC), SortField("id", SortOrder.ASC)],
        )
        page = engine.paginate(page_size=20, include_total=True)
        ids = [r["id"] for r in page.data]
        scores = [r["score"] for r in page.data]

        for i in range(len(scores) - 1):
            if scores[i] == scores[i + 1]:
                assert ids[i] < ids[i + 1]
            else:
                assert scores[i] >= scores[i + 1]

    def test_tuple_sort_field_spec(self, sample_data_10):
        engine = CursorPaginationEngine(
            data=sample_data_10,
            sort_fields=[("score", "desc"), ("id", "asc")],
        )
        page = engine.paginate(page_size=10)
        assert page.data[0]["score"] == 97
        assert page.data[-1]["score"] == 70

    def test_string_sort_field_default_asc(self, sample_data_5):
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"])
        page = engine.paginate(page_size=5)
        assert [r["id"] for r in page.data] == [1, 2, 3, 4, 5]


# ============================================================
# 页大小边界条件测试
# ============================================================

class TestPageSizeBoundary:
    def test_zero_page_size_raises(self, basic_engine):
        with pytest.raises(InvalidPageSizeError, match="must be positive"):
            basic_engine.paginate(page_size=0)

    def test_negative_page_size_raises(self, basic_engine):
        with pytest.raises(InvalidPageSizeError, match="must be positive"):
            basic_engine.paginate(page_size=-5)

    def test_non_integer_page_size_raises(self, basic_engine):
        with pytest.raises(InvalidPageSizeError):
            basic_engine.paginate(page_size="5")

    def test_page_size_downgrade_to_max(self, engine_with_max_page_size):
        page = engine_with_max_page_size.paginate(page_size=1000)
        assert page.page_size == 10
        assert len(page.data) == 10

    def test_page_size_at_max_boundary(self, engine_with_max_page_size):
        page = engine_with_max_page_size.paginate(page_size=10)
        assert page.page_size == 10
        assert len(page.data) == 10

    def test_page_size_below_max_ok(self, engine_with_max_page_size):
        page = engine_with_max_page_size.paginate(page_size=7)
        assert page.page_size == 7
        assert len(page.data) == 7

    def test_default_page_size_when_none(self, engine_with_max_page_size):
        page = engine_with_max_page_size.paginate()
        assert page.page_size == 5
        assert len(page.data) == 5


# ============================================================
# 空数据集测试
# ============================================================

class TestEmptyDataset:
    def test_empty_data_paginate_forward(self, empty_data):
        engine = CursorPaginationEngine(data=empty_data, sort_fields=["id"])
        page = engine.paginate(page_size=10)
        assert page.data == []
        assert page.page_size == 10
        assert page.has_next is False
        assert page.has_prev is False
        assert page.start_cursor is None
        assert page.end_cursor is None
        assert page.total is None

    def test_empty_data_with_total(self, empty_data):
        engine = CursorPaginationEngine(data=empty_data, sort_fields=["id"])
        page = engine.paginate(page_size=10, include_total=True)
        assert page.total == 0
        assert page.total_estimated is False

    def test_empty_data_paginate_backward(self, empty_data):
        engine = CursorPaginationEngine(data=empty_data, sort_fields=["id"])
        page = engine.paginate(page_size=10, direction="prev")
        assert page.data == []
        assert page.has_next is False
        assert page.has_prev is False

    def test_empty_data_requires_sort_field(self, empty_data):
        with pytest.raises(InvalidSortFieldError):
            CursorPaginationEngine(data=empty_data, sort_fields=[])


# ============================================================
# 最后一页不足页大小测试
# ============================================================

class TestPartialLastPage:
    def test_partial_last_page_forward(self, sample_data_10):
        engine = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"])
        page1 = engine.paginate(page_size=4)
        page2 = engine.paginate(page_size=4, cursor=page1.end_cursor, direction="next")
        page3 = engine.paginate(page_size=4, cursor=page2.end_cursor, direction="next")

        assert len(page1.data) == 4
        assert len(page2.data) == 4
        assert len(page3.data) == 2
        assert [r["id"] for r in page3.data] == [9, 10]
        assert page3.has_next is False
        assert page3.has_prev is True

    def test_partial_first_page_backward(self, sample_data_10):
        engine = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"])
        p1 = engine.paginate(page_size=4)
        p2 = engine.paginate(page_size=4, cursor=p1.end_cursor, direction="next")
        p3 = engine.paginate(page_size=4, cursor=p2.end_cursor, direction="next")

        back_from_p3 = engine.paginate(page_size=4, cursor=p3.start_cursor, direction="prev")
        assert len(back_from_p3.data) == 4
        assert back_from_p3.data == p2.data

        back_from_p2 = engine.paginate(page_size=4, cursor=back_from_p3.start_cursor, direction="prev")
        assert len(back_from_p2.data) == 4
        assert back_from_p2.data == p1.data

    def test_single_item_last_page(self, sample_data_5):
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"])
        p1 = engine.paginate(page_size=2)
        p2 = engine.paginate(page_size=2, cursor=p1.end_cursor, direction="next")
        p3 = engine.paginate(page_size=2, cursor=p2.end_cursor, direction="next")

        assert len(p3.data) == 1
        assert p3.data[0]["id"] == 5
        assert p3.has_next is False
        assert p3.has_prev is True


# ============================================================
# 游标编解码和安全测试
# ============================================================

class TestCursorTampered:
    def test_tampered_cursor_signature_fails(self, basic_engine):
        page = basic_engine.paginate(page_size=3)
        cursor = page.end_cursor

        tampered = cursor[:-4] + "XXXX"
        with pytest.raises(CursorTamperedError):
            basic_engine.paginate(page_size=3, cursor=tampered, direction="next")

    def test_modified_payload_fails(self, basic_engine):
        page = basic_engine.paginate(page_size=3)
        cursor = page.end_cursor

        payload_b64, _sig = cursor.rsplit(".", 1)
        bad_sig = "A" * len(_sig)
        bad_cursor = f"{payload_b64}.{bad_sig}"

        with pytest.raises(CursorTamperedError):
            basic_engine.paginate(page_size=3, cursor=bad_cursor, direction="next")

    def test_completely_garbage_cursor_fails(self, basic_engine):
        with pytest.raises(InvalidCursorError):
            basic_engine.paginate(page_size=3, cursor="not-a-valid-cursor", direction="next")

    def test_empty_string_cursor_fails(self, basic_engine):
        with pytest.raises(InvalidCursorError):
            basic_engine.paginate(page_size=3, cursor="", direction="next")

    def test_none_cursor_ok(self, basic_engine):
        page = basic_engine.paginate(page_size=3, cursor=None, direction="next")
        assert len(page.data) == 3

    def test_different_secret_invalidates_cursor(self, sample_data_10):
        config1 = PaginationConfig(cursor_secret="secret-A")
        config2 = PaginationConfig(cursor_secret="secret-B")
        engine1 = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"], config=config1)
        engine2 = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"], config=config2)

        page1 = engine1.paginate(page_size=3)
        with pytest.raises(CursorTamperedError):
            engine2.paginate(page_size=3, cursor=page1.end_cursor, direction="next")


class TestCursorExpiry:
    def test_fresh_cursor_valid(self, engine_with_ttl):
        page = engine_with_ttl.paginate(page_size=2)
        page2 = engine_with_ttl.paginate(page_size=2, cursor=page.end_cursor, direction="next")
        assert len(page2.data) == 2

    def test_expired_cursor_rejected(self, sample_data_5):
        config = PaginationConfig(cursor_ttl_seconds=1, cursor_secret="test")
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"], config=config)

        page = engine.paginate(page_size=2)
        time.sleep(1.1)

        with pytest.raises(CursorExpiredError):
            engine.paginate(page_size=2, cursor=page.end_cursor, direction="next")

    def test_no_ttl_cursor_never_expires(self, basic_engine):
        old_ts = 1000000000.0
        cursor = basic_engine.encode_cursor([5], direction=Direction.NEXT, created_at=old_ts)
        page = basic_engine.paginate(page_size=3, cursor=cursor, direction="next")
        assert len(page.data) > 0


class TestCursorEncodeDecode:
    def test_encode_decode_roundtrip(self, basic_engine):
        sort_values = (42, "hello", None, 3.14)
        cursor = basic_engine.encode_cursor(sort_values, direction=Direction.NEXT)
        decoded = basic_engine.decode_cursor(cursor)

        assert isinstance(decoded, DecodedCursor)
        assert decoded.sort_values == sort_values
        assert decoded.direction == Direction.NEXT
        assert decoded.version == 1

    def test_decode_preserves_types(self, basic_engine):
        values = (10, 3.14, True, False, None, "text", b"\x00\x01\x02")
        cursor = basic_engine.encode_cursor(values, direction=Direction.PREV)
        decoded = basic_engine.decode_cursor(cursor)

        assert decoded.sort_values == values
        assert [type(v) for v in decoded.sort_values] == [type(v) for v in values]

    def test_cursor_opaque(self, basic_engine):
        cursor = basic_engine.encode_cursor([1, 2, 3])
        assert isinstance(cursor, str)
        assert "sv" not in cursor
        assert "__type__" not in cursor


# ============================================================
# 异常分支测试
# ============================================================

class TestInvalidDirection:
    def test_invalid_direction_string_raises(self, basic_engine):
        with pytest.raises(InvalidDirectionError):
            basic_engine.paginate(page_size=3, direction="sideways")

    def test_invalid_direction_none_raises(self, basic_engine):
        with pytest.raises(InvalidDirectionError):
            basic_engine.paginate(page_size=3, direction=None)

    def test_direction_case_insensitive(self, basic_engine):
        page1 = basic_engine.paginate(page_size=3)
        page2 = basic_engine.paginate(page_size=3, cursor=page1.end_cursor, direction="NEXT")
        assert len(page2.data) == 3
        page3 = basic_engine.paginate(page_size=3, cursor=page2.start_cursor, direction="PREV")
        assert page3.data == page1.data


class TestInvalidSortField:
    def test_empty_sort_fields_raises(self, sample_data_10):
        with pytest.raises(InvalidSortFieldError, match="At least one"):
            CursorPaginationEngine(data=sample_data_10, sort_fields=[])

    def test_invalid_sort_field_type_raises(self, sample_data_10):
        with pytest.raises(InvalidSortFieldError):
            CursorPaginationEngine(data=sample_data_10, sort_fields=[12345])

    def test_invalid_sort_order_raises(self, sample_data_10):
        with pytest.raises(ValueError):
            CursorPaginationEngine(data=sample_data_10, sort_fields=[("id", "invalid_order")])


class TestSortFieldChangeCursorStillWorks:
    def test_cursor_from_smaller_dataset_still_works(self, sample_data_10):
        engine_v1 = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"])
        page1 = engine_v1.paginate(page_size=3)
        cursor_for_id_3 = page1.end_cursor

        extra = [{"id": 100 + i, "name": f"extra_{i}", "score": 50} for i in range(5)]
        new_data = sample_data_10 + extra
        engine_v2 = CursorPaginationEngine(data=new_data, sort_fields=["id"])

        page_after = engine_v2.paginate(page_size=10, cursor=cursor_for_id_3, direction="next")
        ids = [r["id"] for r in page_after.data]
        assert ids[0] == 4
        assert len(ids) == 10
        assert 100 in ids
        assert 102 in ids
        assert 103 not in ids

    def test_cursor_to_removed_item_finds_next(self, sample_data_10):
        engine_full = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"])
        page1 = engine_full.paginate(page_size=3)
        cursor_from_full = page1.end_cursor

        reduced_data = [d for d in sample_data_10 if d["id"] not in (4, 5)]
        engine_reduced = CursorPaginationEngine(data=reduced_data, sort_fields=["id"])

        page = engine_reduced.paginate(page_size=10, cursor=cursor_from_full, direction="next")
        ids = [r["id"] for r in page.data]
        assert ids == [6, 7, 8, 9, 10]

    def test_reverse_cursor_with_changed_data(self, sample_data_10):
        engine_full = CursorPaginationEngine(data=sample_data_10, sort_fields=["id"])
        page = engine_full.paginate(page_size=100)
        cursor_at_end = page.start_cursor

        extra_before = [{"id": -i, "name": f"neg_{i}", "score": 999} for i in range(1, 6)]
        extended_data = list(reversed(extra_before)) + sample_data_10
        engine_extended = CursorPaginationEngine(data=extended_data, sort_fields=["id"])

        prev_page = engine_extended.paginate(
            page_size=20, cursor=cursor_at_end, direction="prev"
        )
        ids = [r["id"] for r in prev_page.data]
        assert -5 in ids
        assert -1 in ids
        assert 0 not in ids


# ============================================================
# 总数提示测试
# ============================================================

class TestTotalCount:
    def test_include_total_exact(self, basic_engine):
        page = basic_engine.paginate(page_size=3, include_total=True)
        assert page.total == 10
        assert page.total_estimated is False

    def test_include_total_estimated_flag(self, basic_engine):
        page = basic_engine.paginate(page_size=3, include_total=True, estimate_total=True)
        assert page.total == 10
        assert page.total_estimated is True

    def test_exclude_total_default(self, basic_engine):
        page = basic_engine.paginate(page_size=3)
        assert page.total is None
        assert page.total_estimated is False

    def test_total_with_empty_dataset(self, empty_data):
        engine = CursorPaginationEngine(data=empty_data, sort_fields=["id"])
        page = engine.paginate(page_size=10, include_total=True)
        assert page.total == 0

    def test_total_on_intermediate_page(self, sample_data_large):
        engine = CursorPaginationEngine(data=sample_data_large, sort_fields=["id"])
        p1 = engine.paginate(page_size=10)
        p2 = engine.paginate(page_size=10, cursor=p1.end_cursor, direction="next", include_total=True)
        assert p2.total == 100
        assert [r["id"] for r in p2.data] == list(range(11, 21))

    def test_count_method(self, sample_data_large):
        engine = CursorPaginationEngine(data=sample_data_large, sort_fields=["id"])
        assert engine.count() == 100


# ============================================================
# PageResult 序列化测试
# ============================================================

class TestPageResultSerialization:
    def test_to_dict_without_total(self, basic_engine):
        page = basic_engine.paginate(page_size=2)
        d = page.to_dict()
        assert "data" in d
        assert "page_size" in d
        assert "has_next" in d
        assert "has_prev" in d
        assert "start_cursor" in d
        assert "end_cursor" in d
        assert "total" not in d
        assert "total_estimated" not in d

    def test_to_dict_with_total(self, basic_engine):
        page = basic_engine.paginate(page_size=2, include_total=True)
        d = page.to_dict()
        assert d["total"] == 10
        assert d["total_estimated"] is False

    def test_to_dict_empty_page(self, empty_data):
        engine = CursorPaginationEngine(data=empty_data, sort_fields=["id"])
        page = engine.paginate(page_size=10)
        d = page.to_dict()
        assert d["data"] == []
        assert d["start_cursor"] is None
        assert d["end_cursor"] is None


# ============================================================
# HMAC 配置测试
# ============================================================

class TestHmacConfig:
    def test_hmac_disabled_no_signature(self, sample_data_5):
        config = PaginationConfig(enable_hmac=False)
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"], config=config)
        page = engine.paginate(page_size=2)
        cursor = page.end_cursor
        assert "." not in cursor

    def test_hmac_disabled_tampered_accepted(self, sample_data_5):
        config = PaginationConfig(enable_hmac=False)
        engine = CursorPaginationEngine(data=sample_data_5, sort_fields=["id"], config=config)
        page = engine.paginate(page_size=2)
        cursor = page.end_cursor

        modified = "A" + cursor[1:]
        try:
            engine.paginate(page_size=2, cursor=modified, direction="next")
            assert True
        except InvalidCursorError:
            assert True


# ============================================================
# 综合场景测试
# ============================================================

class TestComplexScenario:
    def test_traverse_all_forward_and_back(self, sample_data_large):
        engine = CursorPaginationEngine(data=sample_data_large, sort_fields=["id"])
        page_size = 7

        forward_pages = []
        cursor = None
        while True:
            page = engine.paginate(page_size=page_size, cursor=cursor, direction="next")
            forward_pages.append(page)
            if not page.has_next:
                break
            cursor = page.end_cursor

        all_forward_ids = []
        for p in forward_pages:
            all_forward_ids.extend(r["id"] for r in p.data)
        assert all_forward_ids == list(range(1, 101))

        backward_pages = []
        cursor = forward_pages[-1].start_cursor
        backward_pages.append(forward_pages[-1])
        while True:
            page = engine.paginate(page_size=page_size, cursor=cursor, direction="prev")
            backward_pages.insert(0, page)
            if not page.has_prev:
                break
            cursor = page.start_cursor

        all_backward_ids = []
        for p in backward_pages:
            all_backward_ids.extend(r["id"] for r in p.data)
        assert all_backward_ids == list(range(1, 101))

    def test_variable_page_sizes(self, basic_engine):
        p1 = basic_engine.paginate(page_size=1)
        assert len(p1.data) == 1 and p1.data[0]["id"] == 1

        p2 = basic_engine.paginate(page_size=5, cursor=p1.end_cursor, direction="next")
        assert len(p2.data) == 5 and [r["id"] for r in p2.data] == [2, 3, 4, 5, 6]

        p3 = basic_engine.paginate(page_size=2, cursor=p2.end_cursor, direction="next")
        assert len(p3.data) == 2 and [r["id"] for r in p3.data] == [7, 8]

        back = basic_engine.paginate(page_size=10, cursor=p3.start_cursor, direction="prev")
        assert [r["id"] for r in back.data] == [1, 2, 3, 4, 5, 6]

    def test_none_value_in_sort_field(self):
        data = [
            {"id": 1, "priority": None},
            {"id": 2, "priority": 10},
            {"id": 3, "priority": 5},
            {"id": 4, "priority": None},
            {"id": 5, "priority": 5},
        ]
        engine = CursorPaginationEngine(
            data=data,
            sort_fields=[SortField("priority", SortOrder.ASC), SortField("id", SortOrder.ASC)],
        )
        page = engine.paginate(page_size=10, include_total=True)
        ids = [r["id"] for r in page.data]
        priorities = [r["priority"] for r in page.data]

        assert page.total == 5
        assert ids[0] == 1 and priorities[0] is None
        assert ids[1] == 4 and priorities[1] is None

        non_none = [(i, p) for i, p in zip(ids, priorities) if p is not None]
        for i in range(len(non_none) - 1):
            assert non_none[i][1] <= non_none[i + 1][1]
