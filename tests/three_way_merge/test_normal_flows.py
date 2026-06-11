import pytest

from solocoder_py.three_way_merge import merge_texts
from solocoder_py.three_way_merge.models import BlockType

from .conftest import make_result


class TestANewLinesBUnchanged:
    def test_a_inserts_one_line_b_unchanged(self):
        base = "line1\nline2\nline3"
        a = "line1\nline2\nnew_line_a\nline3"
        b = "line1\nline2\nline3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.get_merged_text() == "line1\nline2\nnew_line_a\nline3"

    def test_a_inserts_multiple_lines_b_unchanged(self):
        base = "L1\nL2\nL3"
        a = "L1\nA1\nA2\nA3\nL2\nL3"
        b = "L1\nL2\nL3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nA1\nA2\nA3\nL2\nL3"

    def test_b_inserts_one_line_a_unchanged(self):
        base = "line1\nline2\nline3"
        a = "line1\nline2\nline3"
        b = "line1\nline2\nnew_line_b\nline3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.get_merged_text() == "line1\nline2\nnew_line_b\nline3"


class TestAModifyLineBDeleteAnother:
    def test_a_modifies_b_deletes_non_overlapping(self):
        base = "line1\nline2\nline3\nline4"
        a = "line1\nline2_modified\nline3\nline4"
        b = "line1\nline2\nline4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "line1\nline2_modified\nline4"

    def test_a_modifies_end_b_deletes_beginning(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nL2\nL3\nL4\nL5_changed"
        b = "L2\nL3\nL4\nL5"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L2\nL3\nL4\nL5_changed"

    def test_a_deletes_range_b_modifies_outside(self):
        base = "L1\nL2\nL3\nL4\nL5\nL6"
        a = "L1\nL4\nL5\nL6"
        b = "L1\nL2\nL3\nL4\nL5_b\nL6"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nL4\nL5_b\nL6"


class TestABSameModificationDedup:
    def test_ab_make_same_single_line_change(self):
        base = "line1\nline2\nline3"
        a = "line1\nsame_change\nline3"
        b = "line1\nsame_change\nline3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.get_merged_text() == "line1\nsame_change\nline3"

    def test_ab_make_same_multi_line_insertion(self):
        base = "L1\nL2\nL3"
        a = "L1\nX1\nX2\nL2\nL3"
        b = "L1\nX1\nX2\nL2\nL3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nX1\nX2\nL2\nL3"

    def test_ab_delete_same_line(self):
        base = "L1\nL2\nL3\nL4"
        a = "L1\nL3\nL4"
        b = "L1\nL3\nL4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nL3\nL4"

    def test_ab_replace_same_block_with_identical_content(self):
        base = "L1\nOLD1\nOLD2\nOLD3\nL5"
        a = "L1\nNEW1\nNEW2\nNEW3\nL5"
        b = "L1\nNEW1\nNEW2\nNEW3\nL5"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nNEW1\nNEW2\nNEW3\nL5"


class TestMultipleNonOverlappingChanges:
    def test_a_changes_beginning_b_changes_end(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "A_start\nL1\nL2\nL3\nL4\nL5"
        b = "L1\nL2\nL3\nL4\nL5\nB_end"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "A_start\nL1\nL2\nL3\nL4\nL5\nB_end"

    def test_four_disjoint_changes(self):
        base = "\n".join([f"L{i}" for i in range(1, 11)])
        a = "A1\nL1\nL2\nA3\nL3\nL4\nL5\nL6\nL7\nL8\nL9\nL10"
        b = "L1\nL2\nL3\nL4\nB5\nL5\nL6\nL7\nL8\nL9\nB10\nL10"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        expected = "A1\nL1\nL2\nA3\nL3\nL4\nB5\nL5\nL6\nL7\nL8\nL9\nB10\nL10"
        assert result.get_merged_text() == expected

    def test_list_input_works_like_string(self):
        base = ["L1", "L2", "L3"]
        a = ["L1", "A2", "L3"]
        b = ["L1", "L2", "L3"]
        result_str = make_result("\n".join(base), "\n".join(a), "\n".join(b))
        result_list = make_result(base, a, b)
        assert result_str.get_merged_text() == result_list.get_merged_text()
        assert result_list.has_conflicts is False


class TestAdjacentInsertAndModify:
    def test_modify_then_insert_right_after_no_conflict(self):
        base = "line1\nline2\nline3\nline4"
        a = "line1\nline2_modified\nline3\nline4"
        b = "line1\nline2\ninserted_after_line2\nline3\nline4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.get_merged_text() == "line1\nline2_modified\ninserted_after_line2\nline3\nline4"

    def test_insert_then_modify_next_block_no_conflict(self):
        base = "A\nB\nC\nD"
        a = "A\nA_inserted\nB\nC\nD"
        b = "A\nB\nC_changed\nD"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "A\nA_inserted\nB\nC_changed\nD"

    def test_delete_range_then_insert_after_no_conflict(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nL4\nL5"
        b = "L1\nL2\nL3\nB_after_L3\nL4\nL5"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        expected = "L1\nB_after_L3\nL4\nL5"
        assert result.get_merged_text() == expected

    def test_modify_range_insert_at_end_no_conflict(self):
        base_lines = [f"L{i}" for i in range(1, 11)]
        base = "\n".join(base_lines)
        a_list = [f"L{i}" for i in range(1, 5)] + ["A5", "A6"] + [f"L{i}" for i in range(7, 11)]
        a = "\n".join(a_list)
        b_list = base_lines[:] + ["B_tail"]
        b = "\n".join(b_list)
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        expected = (
            "L1\nL2\nL3\nL4\nA5\nA6\nL7\nL8\nL9\nL10\nB_tail"
        )
        assert result.get_merged_text() == expected

    def test_insert_at_beginning_modify_middle_no_conflict(self):
        base = "M1\nM2\nM3\nM4"
        a = "HEAD\nM1\nM2\nM3\nM4"
        b = "M1\nM2\nM3_new\nM4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "HEAD\nM1\nM2\nM3_new\nM4"

    def test_insert_inside_modified_range_is_conflict(self):
        base = "L1\nL2\nL3\nL4"
        a = "L1\nL2_mod\nL3_mod\nL4"
        b = "L1\nL2\nINSERT\nL3\nL4"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count >= 1
