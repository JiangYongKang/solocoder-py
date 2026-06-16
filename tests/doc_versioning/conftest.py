import pytest

from solocoder_py.doc_versioning import DocumentVersionStore


@pytest.fixture
def store():
    return DocumentVersionStore()


@pytest.fixture
def sample_store(store):
    content_v1 = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    store.create_document("doc1", content_v1)
    return store


@pytest.fixture
def multi_version_store(store):
    content_v1 = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    store.create_document("doc1", content_v1)

    content_v2 = "Line 1\nLine 2 modified\nLine 3\nLine 4\nLine 5"
    store.commit_version("doc1", content_v2)

    content_v3 = "Line 1\nLine 2 modified\nLine 3\nLine 4 new\nLine 5\nLine 6"
    store.commit_version("doc1", content_v3)

    return store
