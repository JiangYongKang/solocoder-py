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


class TestCompositeGranularity:
    def test_line_plus_word_single_modified_line(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello world"
        new = "hello brave world"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        assert len(result.operations) == 2
        delete_op = result.operations[0]
        insert_op = result.operations[1]
        assert delete_op.is_delete
        assert insert_op.is_insert
        assert delete_op.has_sub_operations
        assert insert_op.has_sub_operations
        delete_sub_types = [op.op_type for op in delete_op.sub_operations]
        insert_sub_types = [op.op_type for op in insert_op.sub_operations]
        assert DiffOperationType.INSERT not in delete_sub_types
        assert DiffOperationType.DELETE not in insert_sub_types
        assert any(op.is_insert and "brave" in [t.content for t in op.tokens] for op in insert_op.sub_operations)
        assert any(op.is_delete and "world" not in [t.content for t in op.tokens] for op in delete_op.sub_operations) or any(op.is_equal for op in delete_op.sub_operations)

    def test_line_plus_char_single_modified_line(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello"
        new = "hallo"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.CHAR))
        delete_op = [op for op in result.operations if op.is_delete][0]
        insert_op = [op for op in result.operations if op.is_insert][0]
        assert delete_op.has_sub_operations
        assert insert_op.has_sub_operations
        delete_has_e = any(op.is_delete and "e" in [t.content for t in op.tokens] for op in delete_op.sub_operations)
        insert_has_a = any(op.is_insert and "a" in [t.content for t in op.tokens] for op in insert_op.sub_operations)
        assert delete_has_e
        assert insert_has_a
        delete_sub_types = [op.op_type for op in delete_op.sub_operations]
        insert_sub_types = [op.op_type for op in insert_op.sub_operations]
        assert DiffOperationType.INSERT not in delete_sub_types
        assert DiffOperationType.DELETE not in insert_sub_types

    def test_line_plus_word_multiple_modified_lines(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello world\nfoo bar\nbaz"
        new = "hello brave world\nfoo baz bar\nqux"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        delete_ops = [op for op in result.operations if op.is_delete]
        insert_ops = [op for op in result.operations if op.is_insert]
        assert len(delete_ops) >= 1
        assert len(insert_ops) >= 1
        for op in delete_ops:
            assert op.has_sub_operations

    def test_operations_list_with_sub_operations(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello world"
        new = "hello brave world"
        ops = differ.operations_list(
            old, new, (DiffGranularity.LINE, DiffGranularity.WORD), include_sub=True
        )
        assert len(ops) == 2
        assert "sub_operations" in ops[0]
        assert len(ops[0]["sub_operations"]) > 0

    def test_operations_list_without_sub_operations(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello world"
        new = "hello brave world"
        ops = differ.operations_list(
            old, new, (DiffGranularity.LINE, DiffGranularity.WORD), include_sub=False
        )
        assert "sub_operations" not in ops[0]

    def test_composite_pure_insert_no_sub(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "line1\nline2"
        new = "line1\nnew_line\nline2"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        insert_op = [op for op in result.operations if op.is_insert][0]
        assert not insert_op.has_sub_operations

    def test_composite_pure_delete_no_sub(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "line1\nto_delete\nline2"
        new = "line1\nline2"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        delete_op = [op for op in result.operations if op.is_delete][0]
        assert not delete_op.has_sub_operations


class TestContextLinesPartialToken:
    def test_large_equal_block_partial_context_before(self):
        old_lines = [f"L{i}" for i in range(1, 21)]
        new_lines = old_lines[:]
        new_lines[15] = "CHANGED"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        result = differ.diff(old, new, context_lines=3)
        hunk = result.hunks[0]
        context_before = 0
        for op in hunk.operations:
            if op.is_equal:
                if context_before + len(op.tokens) <= 3:
                    context_before += len(op.tokens)
                else:
                    break
            else:
                break
        assert context_before == 3

    def test_large_equal_block_partial_context_after(self):
        old_lines = [f"L{i}" for i in range(1, 21)]
        new_lines = old_lines[:]
        new_lines[3] = "CHANGED"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        result = differ.diff(old, new, context_lines=3)
        hunk = result.hunks[0]
        context_after = 0
        found_change = False
        for op in hunk.operations:
            if not op.is_equal:
                found_change = True
            elif found_change:
                context_after += len(op.tokens)
        assert context_after == 3

    def test_partial_context_hunk_header_correct(self):
        old_lines = [f"L{i}" for i in range(1, 21)]
        new_lines = old_lines[:]
        new_lines[9] = "CHANGED"
        old = "\n".join(old_lines)
        new = "\n".join(new_lines)
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        diff_str = differ.unified_diff(old, new, context_lines=2)
        lines = diff_str.split("\n")
        hunk_line = [l for l in lines if l.startswith("@@")][0]
        assert "@@ -" in hunk_line
        parts = hunk_line.split()
        old_part = parts[1]
        new_part = parts[2]
        old_start = int(old_part.split(",")[0].replace("-", ""))
        new_start = int(new_part.split(",")[0].replace("+", ""))
        assert old_start > 1
        assert new_start > 1


class TestUnifiedDiffConsistentIndexing:
    def test_hunk_header_1based_for_all_granularities(self):
        from solocoder_py.diff import TextDiffer
        from solocoder_py.diff.unified_diff import format_hunk_header
        differ = TextDiffer()

        for gran in [DiffGranularity.LINE, DiffGranularity.WORD, DiffGranularity.CHAR]:
            result = differ.diff("abc", "aXc", gran)
            if result.hunks:
                header = format_hunk_header(result.hunks[0])
                parts = header.split()
                old_start_str = parts[1].split(",")[0]
                new_start_str = parts[2].split(",")[0]
                old_start = int(old_start_str.replace("-", ""))
                new_start = int(new_start_str.replace("+", ""))
                assert old_start >= 1
                assert new_start >= 1


class TestCompositeSubOpSemantics:
    def test_delete_sub_ops_contains_no_insert(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "the old value is here"
        new = "the new value is here"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        delete_op = [op for op in result.operations if op.is_delete][0]
        for sub in delete_op.sub_operations:
            assert not sub.is_insert, f"DELETE sub_operations should not contain INSERT, got {sub.op_type}"

    def test_insert_sub_ops_contains_no_delete(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "the old value is here"
        new = "the new value is here"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        insert_op = [op for op in result.operations if op.is_insert][0]
        for sub in insert_op.sub_operations:
            assert not sub.is_delete, f"INSERT sub_operations should not contain DELETE, got {sub.op_type}"

    def test_both_sub_ops_contain_equal(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "hello world foo"
        new = "hello brave world foo"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        delete_op = [op for op in result.operations if op.is_delete][0]
        insert_op = [op for op in result.operations if op.is_insert][0]
        assert any(sub.is_equal for sub in delete_op.sub_operations)
        assert any(sub.is_equal for sub in insert_op.sub_operations)

    def test_insert_delete_order_handled(self):
        from solocoder_py.diff import TextDiffer, DiffOperation
        differ = TextDiffer()

        fake_ops = [
            DiffOperation(op_type=DiffOperationType.EQUAL, old_start=0, old_end=1, new_start=0, new_end=1,
                         tokens=[__import__('solocoder_py.diff.models', fromlist=['DiffToken']).DiffToken(content="A")]),
            DiffOperation(op_type=DiffOperationType.INSERT, old_start=1, old_end=1, new_start=1, new_end=2,
                         tokens=[__import__('solocoder_py.diff.models', fromlist=['DiffToken']).DiffToken(content="NEW")]),
            DiffOperation(op_type=DiffOperationType.DELETE, old_start=1, old_end=2, new_start=2, new_end=2,
                         tokens=[__import__('solocoder_py.diff.models', fromlist=['DiffToken']).DiffToken(content="OLD")]),
            DiffOperation(op_type=DiffOperationType.EQUAL, old_start=2, old_end=3, new_start=2, new_end=3,
                         tokens=[__import__('solocoder_py.diff.models', fromlist=['DiffToken']).DiffToken(content="B")]),
        ]

        from solocoder_py.diff.models import DiffToken
        fake_old = [DiffToken("A"), DiffToken("OLD"), DiffToken("B")]
        fake_new = [DiffToken("A"), DiffToken("NEW"), DiffToken("B")]

        refined = differ._refine_modified_lines(fake_ops, fake_old, fake_new, DiffGranularity.WORD)

        insert_processed = any(
            op.is_insert and op.has_sub_operations for op in refined
        )
        delete_processed = any(
            op.is_delete and op.has_sub_operations for op in refined
        )
        assert insert_processed, "INSERT-DELETE pair should be processed, INSERT should have sub_operations"
        assert delete_processed, "INSERT-DELETE pair should be processed, DELETE should have sub_operations"

    def test_operations_list_include_sub_semantics(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "abc def"
        new = "abc XYZ def"
        ops = differ.operations_list(
            old, new, (DiffGranularity.LINE, DiffGranularity.WORD), include_sub=True
        )
        delete_op_dict = [op for op in ops if op["type"] == "delete"][0]
        insert_op_dict = [op for op in ops if op["type"] == "insert"][0]
        assert "sub_operations" in delete_op_dict
        assert "sub_operations" in insert_op_dict
        for sub in delete_op_dict["sub_operations"]:
            assert sub["type"] != "insert"
        for sub in insert_op_dict["sub_operations"]:
            assert sub["type"] != "delete"


class TestCompositeMultiLineSubOps:
    def test_multiple_modified_lines_semantics(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "line one here\nline two here"
        new = "line ONE here\nline TWO here"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.WORD))
        delete_op = [op for op in result.operations if op.is_delete][0]
        insert_op = [op for op in result.operations if op.is_insert][0]
        for sub in delete_op.sub_operations:
            assert sub.op_type != DiffOperationType.INSERT
        for sub in insert_op.sub_operations:
            assert sub.op_type != DiffOperationType.DELETE

    def test_char_level_semantics(self):
        from solocoder_py.diff import TextDiffer
        differ = TextDiffer()
        old = "test123"
        new = "test456"
        result = differ.diff(old, new, (DiffGranularity.LINE, DiffGranularity.CHAR))
        delete_op = [op for op in result.operations if op.is_delete][0]
        insert_op = [op for op in result.operations if op.is_insert][0]
        delete_sub_types = set(s.op_type for s in delete_op.sub_operations)
        insert_sub_types = set(s.op_type for s in insert_op.sub_operations)
        assert DiffOperationType.INSERT not in delete_sub_types
        assert DiffOperationType.DELETE not in insert_sub_types
        assert DiffOperationType.EQUAL in delete_sub_types
        assert DiffOperationType.EQUAL in insert_sub_types
