import pytest

from solocoder_py.three_way_merge.models import (
    Block,
    BlockType,
    ChangeType,
    DiffHunk,
    MergeResult,
    TextLine,
)
from solocoder_py.three_way_merge.lcs import lcs_table, backtrack_lcs, diff_hunks
from solocoder_py.three_way_merge.exceptions import (
    InvalidInputError,
    ThreeWayMergeError,
)

from .conftest import make_lines


class TestTextLineModel:
    def test_text_line_equality_by_content(self):
        a = TextLine(content="hello", line_number=0)
        b = TextLine(content="hello", line_number=99)
        assert a == b

    def test_text_line_inequality_by_content(self):
        a = TextLine(content="hello", line_number=0)
        b = TextLine(content="world", line_number=0)
        assert a != b

    def test_text_line_hash_consistent_with_equality(self):
        a = TextLine(content="hello", line_number=0)
        b = TextLine(content="hello", line_number=99)
        assert hash(a) == hash(b)

    def test_text_line_not_equal_to_non_textline(self):
        a = TextLine(content="hello", line_number=0)
        assert a != "hello"
        assert a.__eq__(123) is NotImplemented


class TestChangeTypeEnum:
    def test_change_type_values(self):
        assert ChangeType.UNCHANGED.value == "unchanged"
        assert ChangeType.INSERTED.value == "inserted"
        assert ChangeType.DELETED.value == "deleted"
        assert ChangeType.MODIFIED.value == "modified"


class TestBlockTypeEnum:
    def test_block_type_values(self):
        assert BlockType.COMMON.value == "common"
        assert BlockType.CHANGE_A.value == "change_a"
        assert BlockType.CHANGE_B.value == "change_b"
        assert BlockType.CONFLICT.value == "conflict"


class TestDiffHunk:
    def test_base_range_property(self):
        hunk = DiffHunk(
            base_start=2,
            base_end=5,
            other_start=10,
            other_end=12,
            change_type=ChangeType.MODIFIED,
        )
        assert hunk.base_range == (2, 5)

    def test_other_range_property(self):
        hunk = DiffHunk(
            base_start=2,
            base_end=5,
            other_start=10,
            other_end=12,
            change_type=ChangeType.MODIFIED,
        )
        assert hunk.other_range == (10, 12)

    def test_is_empty_when_no_lines(self):
        hunk = DiffHunk(0, 0, 0, 0, ChangeType.INSERTED)
        assert hunk.is_empty is True

    def test_is_empty_when_has_lines(self):
        lines = make_lines(["a", "b"])
        hunk = DiffHunk(0, 1, 0, 1, ChangeType.MODIFIED, lines=lines)
        assert hunk.is_empty is False


class TestBlock:
    def test_is_conflict_true(self):
        block = Block(block_type=BlockType.CONFLICT)
        assert block.is_conflict is True

    def test_is_conflict_false_for_other_types(self):
        for t in [BlockType.COMMON, BlockType.CHANGE_A, BlockType.CHANGE_B]:
            block = Block(block_type=t)
            assert block.is_conflict is False


class TestMergeResult:
    def test_get_merged_text_default_separator(self):
        result = MergeResult(merged_lines=["a", "b", "c"])
        assert result.get_merged_text() == "a\nb\nc"

    def test_get_merged_text_custom_separator(self):
        result = MergeResult(merged_lines=["a", "b", "c"])
        assert result.get_merged_text("|") == "a|b|c"

    def test_conflict_blocks_filters_correctly(self):
        blocks = [
            Block(block_type=BlockType.COMMON),
            Block(block_type=BlockType.CONFLICT),
            Block(block_type=BlockType.CHANGE_A),
            Block(block_type=BlockType.CONFLICT),
        ]
        result = MergeResult(blocks=blocks)
        assert len(result.conflict_blocks) == 2

    def test_has_conflicts_derived_from_count(self):
        r1 = MergeResult(conflict_count=0)
        assert r1.has_conflicts is False
        r2 = MergeResult(conflict_count=3)
        assert r2.has_conflicts is True


class TestLCSTable:
    def test_identical_sequences(self):
        a = make_lines(["a", "b", "c"])
        b = make_lines(["a", "b", "c"])
        dp = lcs_table(a, b)
        assert dp[len(a)][len(b)] == 3

    def test_completely_different_sequences(self):
        a = make_lines(["a", "b", "c"])
        b = make_lines(["x", "y", "z"])
        dp = lcs_table(a, b)
        assert dp[len(a)][len(b)] == 0

    def test_partial_match(self):
        a = make_lines(["a", "b", "c", "d"])
        b = make_lines(["x", "b", "c", "y"])
        dp = lcs_table(a, b)
        assert dp[len(a)][len(b)] == 2

    def test_empty_sequences(self):
        a = make_lines([])
        b = make_lines(["x"])
        dp = lcs_table(a, b)
        assert dp[0][1] == 0


class TestBacktrackLCS:
    def test_identical_sequences_matches_all(self):
        a = make_lines(["a", "b"])
        b = make_lines(["a", "b"])
        dp = lcs_table(a, b)
        matches = backtrack_lcs(dp, a, b)
        assert matches == [(0, 0), (1, 1)]

    def test_no_matches(self):
        a = make_lines(["a"])
        b = make_lines(["b"])
        dp = lcs_table(a, b)
        matches = backtrack_lcs(dp, a, b)
        assert matches == []

    def test_subsequence_match(self):
        a = make_lines(["a", "x", "b", "y", "c"])
        b = make_lines(["a", "b", "c"])
        dp = lcs_table(a, b)
        matches = backtrack_lcs(dp, a, b)
        assert matches == [(0, 0), (2, 1), (4, 2)]


class TestDiffHunks:
    def test_identical_texts_no_hunks(self):
        base = make_lines(["a", "b", "c"])
        other = make_lines(["a", "b", "c"])
        hunks = diff_hunks(base, other)
        assert hunks == []

    def test_both_empty_no_hunks(self):
        hunks = diff_hunks(make_lines([]), make_lines([]))
        assert hunks == []

    def test_single_insertion(self):
        base = make_lines(["a", "c"])
        other = make_lines(["a", "b", "c"])
        hunks = diff_hunks(base, other)
        assert len(hunks) == 1
        assert hunks[0].change_type == ChangeType.INSERTED
        assert [l.content for l in hunks[0].lines] == ["b"]

    def test_single_deletion(self):
        base = make_lines(["a", "b", "c"])
        other = make_lines(["a", "c"])
        hunks = diff_hunks(base, other)
        assert len(hunks) == 1
        assert hunks[0].change_type == ChangeType.DELETED

    def test_single_modification(self):
        base = make_lines(["a", "old", "c"])
        other = make_lines(["a", "new", "c"])
        hunks = diff_hunks(base, other)
        assert len(hunks) == 1
        assert hunks[0].change_type == ChangeType.MODIFIED
        assert [l.content for l in hunks[0].lines] == ["new"]

    def test_multiple_disjoint_changes(self):
        base = make_lines(["a", "b", "c", "d", "e"])
        other = make_lines(["A", "b", "c", "D", "e"])
        hunks = diff_hunks(base, other)
        assert len(hunks) == 2


class TestExceptions:
    def test_invalid_input_is_merge_error(self):
        assert issubclass(InvalidInputError, ThreeWayMergeError)

    def test_can_raise_and_catch(self):
        with pytest.raises(ThreeWayMergeError):
            raise InvalidInputError("bad")
