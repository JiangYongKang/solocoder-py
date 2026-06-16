from solocoder_py.diff import TextDiffer, diff_texts, unified_diff_texts
from solocoder_py.diff.models import DiffGranularity, DiffOperationType


def make_differ() -> TextDiffer:
    return TextDiffer()


def make_diff_result(old, new, granularity=DiffGranularity.LINE, context_lines=3):
    return diff_texts(old, new, granularity, context_lines)


def make_unified_diff(old, new, granularity=DiffGranularity.LINE, context_lines=3):
    return unified_diff_texts(old, new, granularity, context_lines)
