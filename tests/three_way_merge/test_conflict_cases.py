import pytest

from solocoder_py.three_way_merge import ThreeWayMerger, merge_texts
from solocoder_py.three_way_merge.models import BlockType

from .conftest import make_merger, make_result


class TestSameLineDifferentChanges:
    def test_single_line_conflict_markers(self):
        base = "line1\nline2\nline3"
        a = "line1\nchanged_by_a\nline3"
        b = "line1\nchanged_by_b\nline3"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count == 1
        text = result.get_merged_text()
        assert "<<<<<<< A" in text
        assert "=======" in text
        assert ">>>>>>> B" in text
        assert "changed_by_a" in text
        assert "changed_by_b" in text

    def test_conflict_a_side_comes_before_separator(self):
        base = "L1\nL2\nL3"
        a = "L1\nAAA\nL3"
        b = "L1\nBBB\nL3"
        result = make_result(base, a, b)
        lines = result.merged_lines
        idx_start = lines.index("<<<<<<< A")
        idx_sep = lines.index("=======")
        idx_end = lines.index(">>>>>>> B")
        assert idx_start < idx_sep < idx_end
        assert "AAA" in lines[idx_start:idx_sep]
        assert "BBB" in lines[idx_sep:idx_end]

    def test_multiple_separate_conflicts(self):
        base = "L1\nL2\nL3\nL4\nL5\nL6"
        a = "A_changed_L1\nL2\nL3\nA_changed_L4\nL5\nL6"
        b = "B_changed_L1\nL2\nL3\nB_changed_L4\nL5\nL6"
        result = make_result(base, a, b)
        assert result.conflict_count == 2
        assert result.has_conflicts is True
        blocks_conflict = [b for b in result.blocks if b.block_type == BlockType.CONFLICT]
        assert len(blocks_conflict) == 2


class TestSamePositionAdjacentInserts:
    def test_ab_insert_same_position_different_content_conflict(self):
        base = "L1\nL2\nL3"
        a = "L1\nA_insert\nL2\nL3"
        b = "L1\nB_insert\nL2\nL3"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count == 1
        text = result.get_merged_text()
        assert "<<<<<<< A" in text
        assert "A_insert" in text
        assert "B_insert" in text

    def test_ab_insert_same_position_identical_content_dedup(self):
        base = "L1\nL2\nL3"
        a = "L1\nSAME\nL2\nL3"
        b = "L1\nSAME\nL2\nL3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nSAME\nL2\nL3"


class TestModifyVersusDeleteConflict:
    def test_same_line_a_modifies_b_deletes(self):
        base = "L1\nL2\nL3\nL4"
        a = "L1\nL2_changed\nL3\nL4"
        b = "L1\nL3\nL4"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count == 1
        text = result.get_merged_text()
        assert "<<<<<<< A" in text
        assert "L2_changed" in text

    def test_same_range_a_modifies_b_deletes(self):
        base = "L1\nMID1\nMID2\nMID3\nL5"
        a = "L1\nNEW1\nNEW2\nL5"
        b = "L1\nL5"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        text = result.get_merged_text()
        assert "NEW1" in text
        assert "NEW2" in text


class TestLargeBlockAlignment:
    def test_two_large_independent_blocks_no_conflict(self):
        base = "\n".join([f"L{i}" for i in range(1, 31)])
        a_list = [f"L{i}" for i in range(1, 5)] + [f"A{i}" for i in range(5, 11)] + [f"L{i}" for i in range(11, 31)]
        a = "\n".join(a_list)
        b_list = [f"L{i}" for i in range(1, 20)] + [f"B{i}" for i in range(20, 26)] + [f"L{i}" for i in range(26, 31)]
        b = "\n".join(b_list)
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        expected_list = (
            [f"L{i}" for i in range(1, 5)]
            + [f"A{i}" for i in range(5, 11)]
            + [f"L{i}" for i in range(11, 20)]
            + [f"B{i}" for i in range(20, 26)]
            + [f"L{i}" for i in range(26, 31)]
        )
        assert result.get_merged_text() == "\n".join(expected_list)
        assert len(result.blocks) == 5

    def test_block_type_sequence_is_correct(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nA2\nL3\nL4\nL5"
        b = "L1\nL2\nL3\nB4\nL5"
        result = make_result(base, a, b)
        block_types = [blk.block_type for blk in result.blocks]
        assert block_types == [
            BlockType.COMMON,
            BlockType.CHANGE_A,
            BlockType.COMMON,
            BlockType.CHANGE_B,
            BlockType.COMMON,
        ]

    def test_very_large_document_scales(self):
        lines = [f"original_line_{i}" for i in range(500)]
        base = "\n".join(lines)
        a_lines = lines[:]
        for i in range(10, 20):
            a_lines[i] = f"A_modified_{i}"
        for i in range(400, 410):
            a_lines[i] = f"A_modified_{i}"
        a = "\n".join(a_lines)
        b_lines = lines[:]
        for i in range(100, 110):
            b_lines[i] = f"B_modified_{i}"
        for i in range(300, 310):
            b_lines[i] = f"B_modified_{i}"
        b = "\n".join(b_lines)
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        for i in range(10, 20):
            assert f"A_modified_{i}" in result.merged_lines
        for i in range(400, 410):
            assert f"A_modified_{i}" in result.merged_lines
        for i in range(100, 110):
            assert f"B_modified_{i}" in result.merged_lines
        for i in range(300, 310):
            assert f"B_modified_{i}" in result.merged_lines


class TestConflictBlockFormatting:
    def test_multi_line_conflict_block_format(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nA1\nA2\nA3\nL5"
        b = "L1\nB1\nB2\nB3\nL5"
        result = make_result(base, a, b)
        lines = result.merged_lines
        idx_start = lines.index("<<<<<<< A")
        idx_sep = lines.index("=======")
        idx_end = lines.index(">>>>>>> B")
        assert lines[idx_start + 1: idx_sep] == ["A1", "A2", "A3"]
        assert lines[idx_sep + 1: idx_end] == ["B1", "B2", "B3"]

    def test_custom_conflict_markers(self):
        merger = ThreeWayMerger(
            conflict_start="<<< OURS",
            conflict_separator="---",
            conflict_end=">>> THEIRS",
            label_a="",
            label_b="",
        )
        base = "line1\nline2"
        a = "line1\nA_line2"
        b = "line1\nB_line2"
        result = merger.merge(base, a, b)
        text = result.get_merged_text()
        assert "<<< OURS" in text
        assert "---" in text
        assert ">>> THEIRS" in text
        assert "<<<<<<< A" not in text


class TestMergeResultProperties:
    def test_conflict_blocks_property(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nA2\nL3\nA4\nL5"
        b = "L1\nB2\nL3\nB4\nL5"
        result = make_result(base, a, b)
        assert result.conflict_count == 2
        assert len(result.conflict_blocks) == 2
        for cb in result.conflict_blocks:
            assert cb.is_conflict is True

    def test_no_conflict_conflict_blocks_empty(self):
        base = "L1\nL2"
        a = "L1\nL2_mod"
        b = "L1\nL2_mod"
        result = make_result(base, a, b)
        assert result.conflict_blocks == []

    def test_get_merged_text_separator(self):
        base = ["A", "B", "C"]
        a = ["A", "B", "C"]
        b = ["A", "B", "C"]
        result = make_result(base, a, b)
        assert result.get_merged_text("\n") == "A\nB\nC"
        assert result.get_merged_text("|") == "A|B|C"
