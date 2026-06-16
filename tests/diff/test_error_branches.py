import pytest

from solocoder_py.diff import TextDiffer
from solocoder_py.diff.exceptions import (
    DiffError,
    InvalidContextLinesError,
    InvalidGranularityError,
)
from solocoder_py.diff.granularity import validate_granularity


class TestInvalidGranularity:
    def test_invalid_granularity_string_raises(self):
        with pytest.raises(InvalidGranularityError) as exc_info:
            validate_granularity("invalid_granularity")
        assert exc_info.value.granularity == "invalid_granularity"
        assert "Unsupported granularity" in str(exc_info.value)

    def test_diff_method_invalid_granularity_raises(self):
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.diff("a", "b", granularity="paragraph")

    def test_unified_diff_invalid_granularity_raises(self):
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.unified_diff("a", "b", granularity="sentence")

    def test_invalid_granularity_is_diff_error_subclass(self):
        assert issubclass(InvalidGranularityError, DiffError)


class TestInvalidContextLines:
    def test_negative_context_lines_raises(self):
        differ = TextDiffer()
        with pytest.raises(InvalidContextLinesError) as exc_info:
            differ.diff("a", "b", context_lines=-1)
        assert exc_info.value.context_lines == -1
        assert "Invalid context lines" in str(exc_info.value)

    def test_unified_diff_negative_context_raises(self):
        differ = TextDiffer()
        with pytest.raises(InvalidContextLinesError):
            differ.unified_diff("a", "b", context_lines=-5)

    def test_invalid_context_is_diff_error_subclass(self):
        assert issubclass(InvalidContextLinesError, DiffError)

    def test_zero_context_lines_accepted(self):
        differ = TextDiffer()
        result = differ.diff("a\nb", "a\nc", context_lines=0)
        assert result is not None
        assert len(result.hunks) >= 0


class TestValidGranularityValues:
    def test_line_granularity_valid(self):
        g = validate_granularity("line")
        assert g.value == "line"

    def test_word_granularity_valid(self):
        g = validate_granularity("word")
        assert g.value == "word"

    def test_char_granularity_valid(self):
        g = validate_granularity("char")
        assert g.value == "char"

    def test_case_sensitive_granularity(self):
        with pytest.raises(InvalidGranularityError):
            validate_granularity("LINE")
        with pytest.raises(InvalidGranularityError):
            validate_granularity("Line")


class TestOperationsListErrorHandling:
    def test_operations_list_with_invalid_granularity(self):
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.operations_list("a", "b", granularity="unknown")


class TestDiffResultGetOperationsList:
    def test_empty_diff_returns_empty_list(self):
        differ = TextDiffer()
        result = differ.diff("", "")
        op_list = result.get_operations_list()
        assert isinstance(op_list, list)
        assert len(op_list) == 0

    def test_operations_list_structure(self):
        differ = TextDiffer()
        result = differ.diff("old", "new")
        op_list = result.get_operations_list()
        for op in op_list:
            assert "type" in op
            assert "old_start" in op
            assert "old_end" in op
            assert "new_start" in op
            assert "new_end" in op
            assert "content" in op
            assert isinstance(op["content"], list)


class TestCompositeGranularityErrors:
    def test_composite_with_word_as_coarse_raises(self):
        from solocoder_py.diff import DiffGranularity
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.diff("a", "b", (DiffGranularity.WORD, DiffGranularity.LINE))

    def test_composite_with_line_as_fine_raises(self):
        from solocoder_py.diff import DiffGranularity
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.diff("a", "b", (DiffGranularity.LINE, DiffGranularity.LINE))

    def test_composite_invalid_length_tuple_raises(self):
        from solocoder_py.diff import DiffGranularity
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.diff("a", "b", (DiffGranularity.LINE,))

    def test_composite_operations_list_invalid_raises(self):
        from solocoder_py.diff import DiffGranularity
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.operations_list("a", "b", ("line", "invalid"))

    def test_composite_unified_diff_invalid_raises(self):
        from solocoder_py.diff import DiffGranularity
        differ = TextDiffer()
        with pytest.raises(InvalidGranularityError):
            differ.unified_diff("a", "b", (DiffGranularity.CHAR, DiffGranularity.WORD))
