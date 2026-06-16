import pytest

from solocoder_py.tag_hierarchy import TagHierarchy


@pytest.fixture
def tag_hierarchy():
    return TagHierarchy()
