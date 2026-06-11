import pytest

from solocoder_py.three_way_merge import merge_texts

from .conftest import make_result


class TestAEqualsBase:
    def test_a_equals_base_b_modifies(self):
        base = "line1\nline2\nline3"
        a = "line1\nline2\nline3"
        b = "line1\nline2_modified\nline3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "line1\nline2_modified\nline3"

    def test_a_equals_base_b_inserts_and_deletes(self):
        base = "L1\nL2\nL3\nL4"
        a = "L1\nL2\nL3\nL4"
        b = "L1\nB_NEW\nL2\nL4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nB_NEW\nL2\nL4"


class TestBEqualsBase:
    def test_b_equals_base_a_modifies(self):
        base = "line1\nline2\nline3\nline4"
        a = "line1\nline2\nline3_new\nline4"
        b = "line1\nline2\nline3\nline4"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "line1\nline2\nline3_new\nline4"

    def test_b_equals_base_a_deletes_range(self):
        base = "L1\nL2\nL3\nL4\nL5"
        a = "L1\nL5"
        b = "L1\nL2\nL3\nL4\nL5"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "L1\nL5"


class TestAllThreeIdentical:
    def test_three_identical_simple(self):
        base = "line1\nline2"
        a = "line1\nline2"
        b = "line1\nline2"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.get_merged_text() == "line1\nline2"

    def test_three_identical_many_lines(self):
        lines = [f"line{i}" for i in range(1, 101)]
        base = "\n".join(lines)
        a = "\n".join(lines)
        b = "\n".join(lines)
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == base
        assert len(result.merged_lines) == 100

    def test_three_identical_empty(self):
        result = make_result("", "", "")
        assert result.has_conflicts is False
        assert result.conflict_count == 0
        assert result.merged_lines == []
        assert result.get_merged_text() == ""


class TestBaseEmpty:
    def test_base_empty_a_has_content_b_empty(self):
        base = ""
        a = "a_line1\na_line2"
        b = ""
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "a_line1\na_line2"

    def test_base_empty_b_has_content_a_empty(self):
        base = ""
        a = ""
        b = "b_line1\nb_line2\nb_line3"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "b_line1\nb_line2\nb_line3"

    def test_base_empty_both_have_content_is_conflict(self):
        base = ""
        a = "a_line1\na_line2"
        b = "b_line1"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count == 1

    def test_base_empty_both_identical_no_conflict(self):
        base = ""
        a = "SAME1\nSAME2"
        b = "SAME1\nSAME2"
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == "SAME1\nSAME2"


class TestABBothEmptyInput:
    def test_base_nonempty_ab_empty(self):
        base = "L1\nL2\nL3"
        a = ""
        b = ""
        result = make_result(base, a, b)
        assert result.has_conflicts is False
        assert result.get_merged_text() == ""

    def test_base_nonempty_a_empty_b_modify(self):
        base = "L1\nL2\nL3"
        a = ""
        b = "L1\nL2_changed\nL3"
        result = make_result(base, a, b)
        assert result.has_conflicts is True
        assert result.conflict_count == 1
