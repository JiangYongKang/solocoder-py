import pytest

from solocoder_py.diff import DiffGranularity

from .conftest import make_diff_result, make_unified_diff


class TestIdenticalText:
    def test_identical_text_line_granularity(self):
        text = "line1\nline2\nline3"
        result = make_diff_result(text, text)
        ops = result.operations
        assert len(ops) == 1
        assert ops[0].is_equal
        assert len(ops[0].tokens) == 3

    def test_identical_text_word_granularity(self):
        text = "hello world test"
        result = make_diff_result(text, text, DiffGranularity.WORD)
        ops = result.operations
        assert all(op.is_equal for op in ops)

    def test_identical_text_char_granularity(self):
        text = "abcdef"
        result = make_diff_result(text, text, DiffGranularity.CHAR)
        ops = result.operations
        assert all(op.is_equal for op in ops)

    def test_identical_text_hunks_empty(self):
        text = "same\ntext"
        result = make_diff_result(text, text)
        assert len(result.hunks) == 0


class TestEmptyText:
    def test_both_empty(self):
        result = make_diff_result("", "")
        assert len(result.operations) == 0
        assert len(result.hunks) == 0

    def test_old_empty_new_has_content(self):
        old = ""
        new = "line1\nline2"
        result = make_diff_result(old, new)
        ops = result.operations
        assert len(ops) == 1
        assert ops[0].is_insert
        assert len(ops[0].tokens) == 2

    def test_new_empty_old_has_content(self):
        old = "line1\nline2"
        new = ""
        result = make_diff_result(old, new)
        ops = result.operations
        assert len(ops) == 1
        assert ops[0].is_delete
        assert len(ops[0].tokens) == 2

    def test_empty_text_word_granularity(self):
        result = make_diff_result("", "", DiffGranularity.WORD)
        assert len(result.operations) == 0


class TestOnlyEmptyLines:
    def test_single_empty_line(self):
        old = ""
        new = "\n"
        result = make_diff_result(old, new)
        ops = result.operations
        assert len(ops) == 1
        assert ops[0].is_insert

    def test_multiple_empty_lines(self):
        old = "\n\n"
        new = "\n\n\n"
        result = make_diff_result(old, new)
        ops = result.operations
        assert len(ops) >= 1
        has_equal = any(op.is_equal for op in ops)
        has_insert = any(op.is_insert for op in ops)
        assert has_equal
        assert has_insert

    def test_empty_lines_with_content(self):
        old = "\nline1\n\nline2\n"
        new = "\nline1\n\nline2\n\n"
        result = make_diff_result(old, new)
        ops = result.operations
        assert any(op.is_insert for op in ops)


class TestLargeText:
    def test_large_identical_text(self):
        lines = [f"line_{i}" for i in range(1000)]
        text = "\n".join(lines)
        result = make_diff_result(text, text)
        assert len(result.operations) == 1
        assert result.operations[0].is_equal
        assert len(result.operations[0].tokens) == 1000

    def test_large_text_with_changes(self):
        old_lines = [f"line_{i}" for i in range(500)]
        new_lines = old_lines[:]
        for i in range(10, 20):
            new_lines[i] = f"modified_{i}"
        for i in range(100, 110):
            new_lines.insert(i + 10, f"inserted_{i}")
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        result = make_diff_result(old, new)
        assert len(result.operations) > 0
        assert any(op.is_delete for op in result.operations)
        assert any(op.is_insert for op in result.operations)
        assert any(op.is_equal for op in result.operations)

    def test_large_text_unified_diff_completes(self):
        old_lines = [f"L{i}" for i in range(2000)]
        new_lines = old_lines[:]
        new_lines[500] = "CHANGED"
        new_lines[1500] = "ANOTHER_CHANGE"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        diff_str = make_unified_diff(old, new, context_lines=2)
        assert isinstance(diff_str, str)
        assert len(diff_str) > 0
        assert "@@" in diff_str


class TestGranularityConsistency:
    def test_line_granularity_on_single_line(self):
        old = "hello world"
        new = "hello brave world"
        line_result = make_diff_result(old, new, DiffGranularity.LINE)
        assert len(line_result.operations) == 2
        assert line_result.operations[0].is_delete
        assert line_result.operations[1].is_insert

    def test_char_granularity_detects_small_changes(self):
        old = "hello"
        new = "hallo"
        char_result = make_diff_result(old, new, DiffGranularity.CHAR)
        total_chars_equal = sum(
            len(op.tokens) for op in char_result.operations if op.is_equal
        )
        assert total_chars_equal >= 3

    def test_word_granularity_between_line_and_char(self):
        old = "the quick fox jumps"
        new = "the slow fox leaps"
        word_result = make_diff_result(old, new, DiffGranularity.WORD)
        char_result = make_diff_result(old, new, DiffGranularity.CHAR)
        word_ops = len([op for op in word_result.operations if not op.is_equal])
        char_ops = len([op for op in char_result.operations if not op.is_equal])
        assert word_ops <= char_ops


class TestContextLinesEdgeCases:
    def test_zero_context_lines(self):
        old = "A\nB\nC\nD\nE"
        new = "A\nB\nX\nD\nE"
        result = make_diff_result(old, new, context_lines=0)
        assert len(result.hunks) == 1
        hunk = result.hunks[0]
        assert hunk.old_count == 1
        assert hunk.new_count == 1

    def test_context_larger_than_diff(self):
        old = "A\nB\nC"
        new = "A\nX\nC"
        result = make_diff_result(old, new, context_lines=100)
        assert len(result.hunks) == 1

    def test_changes_at_beginning(self):
        old = "old1\nold2\nA\nB\nC"
        new = "new1\nnew2\nA\nB\nC"
        result = make_diff_result(old, new, context_lines=2)
        assert len(result.hunks) >= 1
        assert result.hunks[0].old_start == 0

    def test_changes_at_end(self):
        old = "A\nB\nC\nold1\nold2"
        new = "A\nB\nC\nnew1\nnew2"
        diff_str = make_unified_diff(old, new, context_lines=2)
        assert "@@" in diff_str
