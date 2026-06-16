import pytest

from solocoder_py.diff import DiffGranularity, DiffOperationType
from solocoder_py.diff.models import DiffOperation

from .conftest import make_diff_result, make_unified_diff


class TestLineGranularityInsertDelete:
    def test_single_line_insert(self):
        old = "line1\nline2\nline3"
        new = "line1\nnew_line\nline2\nline3"
        result = make_diff_result(old, new)
        ops = result.operations
        assert len(ops) >= 3
        assert ops[0].is_equal
        assert ops[0].tokens[0].content == "line1"
        assert ops[1].is_insert
        assert ops[1].tokens[0].content == "new_line"
        assert ops[2].is_equal

    def test_single_line_delete(self):
        old = "line1\nto_delete\nline2"
        new = "line1\nline2"
        result = make_diff_result(old, new)
        ops = result.operations
        assert any(op.is_delete and op.tokens[0].content == "to_delete" for op in ops)

    def test_single_line_modify(self):
        old = "line1\nold_line\nline3"
        new = "line1\nnew_line\nline3"
        result = make_diff_result(old, new)
        ops = result.operations
        has_delete = any(op.is_delete and op.tokens[0].content == "old_line" for op in ops)
        has_insert = any(op.is_insert and op.tokens[0].content == "new_line" for op in ops)
        assert has_delete
        assert has_insert

    def test_multiple_lines_insert_and_delete(self):
        old = "A\nB\nC\nD\nE"
        new = "A\nX\nY\nC\nZ\nE"
        result = make_diff_result(old, new)
        ops = result.operations
        contents = [(op.op_type, [t.content for t in op.tokens]) for op in ops]
        assert (DiffOperationType.EQUAL, ["A"]) in contents
        assert (DiffOperationType.DELETE, ["B"]) in contents
        assert (DiffOperationType.INSERT, ["X", "Y"]) in contents or (DiffOperationType.INSERT, ["X"]) in contents
        assert (DiffOperationType.DELETE, ["D"]) in contents
        assert (DiffOperationType.INSERT, ["Z"]) in contents
        assert (DiffOperationType.EQUAL, ["E"]) in contents

    def test_operations_list_structured_output(self):
        old = "hello\nworld"
        new = "hello\nnew\nworld"
        result = make_diff_result(old, new)
        op_list = result.get_operations_list()
        assert isinstance(op_list, list)
        assert len(op_list) >= 3
        assert op_list[0]["type"] == "equal"
        assert op_list[0]["content"] == ["hello"]
        insert_op = [op for op in op_list if op["type"] == "insert"][0]
        assert insert_op["content"] == ["new"]


class TestUnifiedDiffFormat:
    def test_unified_diff_basic_structure(self):
        old = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        diff_str = make_unified_diff(old, new)
        lines = diff_str.split("\n")
        assert lines[0].startswith("--- ")
        assert lines[1].startswith("+++ ")
        assert any(line.startswith("@@") for line in lines)
        assert any(line.startswith("-") and not line.startswith("---") for line in lines)
        assert any(line.startswith("+") and not line.startswith("+++") for line in lines)

    def test_unified_diff_hunk_header_format(self):
        old = "\n".join([f"line{i}" for i in range(1, 21)])
        new_lines = [f"line{i}" for i in range(1, 21)]
        new_lines[9] = "modified_line"
        new = "\n".join(new_lines)
        diff_str = make_unified_diff(old, new, context_lines=3)
        lines = diff_str.split("\n")
        hunk_headers = [l for l in lines if l.startswith("@@")]
        assert len(hunk_headers) > 0
        header = hunk_headers[0]
        assert "@@ -" in header
        assert " +" in header
        assert "@@" in header

    def test_unified_diff_context_lines(self):
        old_lines = [f"L{i}" for i in range(1, 11)]
        new_lines = old_lines[:]
        new_lines[4] = "CHANGED"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        diff_str = make_unified_diff(old, new, context_lines=2)
        lines = diff_str.split("\n")
        content_lines = [l for l in lines if l and l[0] in (" ", "-", "+") and not l.startswith("---") and not l.startswith("+++")]
        assert len(content_lines) <= 2 * 2 + 2

    def test_unified_diff_multiple_hunks(self):
        old_lines = [f"L{i}" for i in range(1, 31)]
        new_lines = old_lines[:]
        new_lines[2] = "CHANGE1"
        new_lines[25] = "CHANGE2"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        diff_str = make_unified_diff(old, new, context_lines=2)
        lines = diff_str.split("\n")
        hunk_headers = [l for l in lines if l.startswith("@@")]
        assert len(hunk_headers) == 2

    def test_unified_diff_empty_diff(self):
        text = "same\ntext\nhere"
        diff_str = make_unified_diff(text, text)
        assert diff_str == ""


class TestWordGranularity:
    def test_word_insert(self):
        old = "hello world"
        new = "hello brave world"
        result = make_diff_result(old, new, DiffGranularity.WORD)
        ops = result.operations
        has_insert = any(op.is_insert and "brave" in [t.content for t in op.tokens] for op in ops)
        assert has_insert

    def test_word_delete(self):
        old = "the quick brown fox"
        new = "the brown fox"
        result = make_diff_result(old, new, DiffGranularity.WORD)
        ops = result.operations
        has_delete = any(op.is_delete and "quick" in [t.content for t in op.tokens] for op in ops)
        assert has_delete

    def test_word_modify(self):
        old = "I like apples"
        new = "I love oranges"
        result = make_diff_result(old, new, DiffGranularity.WORD)
        ops = result.operations
        contents = [(op.op_type.value, [t.content for t in op.tokens]) for op in ops]
        assert ("delete", ["like"]) in contents or ("delete", ["apples"]) in contents
        assert ("insert", ["love"]) in contents or ("insert", ["oranges"]) in contents


class TestCharGranularity:
    def test_char_insert(self):
        old = "abc"
        new = "aXbc"
        result = make_diff_result(old, new, DiffGranularity.CHAR)
        ops = result.operations
        has_insert = any(op.is_insert and "X" in [t.content for t in op.tokens] for op in ops)
        assert has_insert

    def test_char_delete(self):
        old = "abXc"
        new = "abc"
        result = make_diff_result(old, new, DiffGranularity.CHAR)
        ops = result.operations
        has_delete = any(op.is_delete and "X" in [t.content for t in op.tokens] for op in ops)
        assert has_delete

    def test_char_modify(self):
        old = "hello"
        new = "hallo"
        result = make_diff_result(old, new, DiffGranularity.CHAR)
        ops = result.operations
        has_delete_e = any(op.is_delete and "e" in [t.content for t in op.tokens] for op in ops)
        has_insert_a = any(op.is_insert and "a" in [t.content for t in op.tokens] for op in ops)
        assert has_delete_e
        assert has_insert_a
