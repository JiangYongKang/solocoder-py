from solocoder_py.three_way_merge import ThreeWayMerger, merge_texts
from solocoder_py.three_way_merge.models import (
    Block,
    BlockType,
    ChangeType,
    DiffHunk,
    MergeResult,
    TextLine,
)


def make_merger() -> ThreeWayMerger:
    return ThreeWayMerger()


def make_result(base, a, b) -> MergeResult:
    return merge_texts(base, a, b)


def make_lines(strings):
    return [TextLine(content=s, line_number=i) for i, s in enumerate(strings)]
