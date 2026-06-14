from __future__ import annotations

import math

import pytest

from solocoder_py.fulltext import (
    DEFAULT_B,
    DEFAULT_K1,
    Document,
    DocumentNotFoundError,
    FullTextIndex,
    InvalidDocumentError,
    SearchResult,
    stem_word,
)


class TestFullTextIndexInit:
    def test_default_params(self):
        idx = FullTextIndex()
        assert idx.k1 == DEFAULT_K1
        assert idx.b == DEFAULT_B
        assert idx.total_docs == 0
        assert idx.avg_doc_length == 0.0

    def test_custom_params(self):
        idx = FullTextIndex(k1=2.0, b=0.5)
        assert idx.k1 == 2.0
        assert idx.b == 0.5

    def test_extra_stopwords(self):
        extra = {"custom1", "custom2"}
        idx = FullTextIndex(extra_stopwords=extra)
        assert idx.stopwords.is_stopword("custom1")
        assert idx.stopwords.is_stopword("custom2")


class TestAddDocumentNormalFlows:
    def test_add_single_document(self):
        idx = FullTextIndex()
        doc = Document(doc_id="doc1", content="hello world")
        idx.add_document(doc)
        assert idx.total_docs == 1
        assert idx.contains_document("doc1")
        assert idx.get_document("doc1") == doc

    def test_add_multiple_documents(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.add_document(Document(doc_id="doc3", content="python programming"))
        assert idx.total_docs == 3

    def test_add_documents_batch(self):
        idx = FullTextIndex()
        docs = [
            Document(doc_id="doc1", content="hello world"),
            Document(doc_id="doc2", content="hello python"),
        ]
        idx.add_documents(docs)
        assert idx.total_docs == 2

    def test_add_document_updates_existing(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc1", content="hello python"))
        assert idx.total_docs == 1
        assert idx.get_document("doc1").content == "hello python"

    def test_document_with_metadata(self):
        idx = FullTextIndex()
        metadata = {"author": "test", "date": "2024-01-01"}
        doc = Document(doc_id="doc1", content="test content", metadata=metadata)
        idx.add_document(doc)
        assert idx.get_document("doc1").metadata == metadata

    def test_term_frequency_recorded(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello hello world"))
        assert idx.get_term_frequency("hello", "doc1") == 2
        assert idx.get_term_frequency("world", "doc1") == 1

    def test_term_positions_recorded(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world hello"))
        positions = idx.get_term_positions("hello", "doc1")
        assert positions == [0, 2]

    def test_document_frequency(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.add_document(Document(doc_id="doc3", content="python programming"))
        assert idx.get_document_frequency("hello") == 2
        assert idx.get_document_frequency("python") == 2
        assert idx.get_document_frequency("world") == 1

    def test_stemming_applied_on_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="running cats played"))
        assert idx.get_term_frequency("run", "doc1") == 1
        assert idx.get_term_frequency("cat", "doc1") == 1
        assert idx.get_term_frequency("play", "doc1") == 1

    def test_stopwords_filtered_on_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="the quick brown fox"))
        assert idx.get_term_frequency("the", "doc1") == 0
        assert idx.get_term_frequency("quick", "doc1") == 1
        assert idx.get_term_frequency("brown", "doc1") == 1

    def test_chinese_document_indexing(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="你好世界"))
        assert idx.get_term_frequency("你", "doc1") == 1
        assert idx.get_term_frequency("好", "doc1") == 1
        assert idx.get_term_frequency("世", "doc1") == 1
        assert idx.get_term_frequency("界", "doc1") == 1

    def test_mixed_language_indexing(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="你好 world 测试 Python"))
        assert idx.get_term_frequency("你", "doc1") == 1
        assert idx.get_term_frequency("world", "doc1") == 1
        assert idx.get_term_frequency("python", "doc1") == 1

    def test_avg_doc_length_updated(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        assert idx.avg_doc_length > 0
        idx.add_document(Document(doc_id="doc2", content="a"))
        assert idx.avg_doc_length > 0


class TestRemoveDocumentNormalFlows:
    def test_remove_existing_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.remove_document("doc1")
        assert idx.total_docs == 0
        assert not idx.contains_document("doc1")
        assert idx.get_document("doc1") is None

    def test_remove_document_cleans_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.remove_document("doc1")
        assert idx.get_term_frequency("hello", "doc1") == 0
        assert idx.get_term_positions("hello", "doc1") == []
        assert idx.get_document_frequency("hello") == 0

    def test_remove_one_of_multiple(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.remove_document("doc1")
        assert idx.total_docs == 1
        assert idx.contains_document("doc2")
        assert idx.get_document_frequency("hello") == 1
        assert idx.get_document_frequency("world") == 0

    def test_remove_shared_term_preserved(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.remove_document("doc1")
        assert idx.get_term_frequency("hello", "doc2") == 1

    def test_clear_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.clear()
        assert idx.total_docs == 0
        assert idx.avg_doc_length == 0.0
        assert not idx.contains_document("doc1")


class TestSearchNormalFlows:
    def test_single_term_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        results = idx.search("hello")
        assert len(results) == 2
        assert all(r.doc_id in {"doc1", "doc2"} for r in results)

    def test_multi_term_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="quick brown fox"))
        idx.add_document(Document(doc_id="doc2", content="lazy dog"))
        idx.add_document(Document(doc_id="doc3", content="quick dog"))
        results = idx.search("quick dog")
        doc_ids = [r.doc_id for r in results]
        assert "doc3" in doc_ids
        assert "doc1" in doc_ids
        assert "doc2" in doc_ids

    def test_search_results_sorted_by_score(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="apple apple apple"))
        idx.add_document(Document(doc_id="doc2", content="apple"))
        results = idx.search("apple")
        assert len(results) == 2
        assert results[0].doc_id == "doc1"
        assert results[0].score > results[1].score

    def test_search_with_top_k(self):
        idx = FullTextIndex()
        for i in range(5):
            idx.add_document(Document(doc_id=f"doc{i}", content=f"test document {i}"))
        results = idx.search("test", top_k=3)
        assert len(results) == 3

    def test_search_returns_matched_terms(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="quick brown fox"))
        results = idx.search("quick fox")
        assert len(results) == 1
        assert "quick" in results[0].matched_terms
        assert "fox" in results[0].matched_terms

    def test_search_returns_metadata(self):
        metadata = {"author": "test"}
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world", metadata=metadata))
        results = idx.search("hello")
        assert len(results) == 1
        assert results[0].metadata == metadata

    def test_stemming_applied_on_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="running cats"))
        results = idx.search("run cat")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_stopwords_filtered_on_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="the quick brown fox"))
        results = idx.search("the quick")
        assert len(results) == 1
        assert "quick" in results[0].matched_terms
        assert "the" not in results[0].matched_terms

    def test_chinese_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="你好世界"))
        idx.add_document(Document(doc_id="doc2", content="你好Python"))
        results = idx.search("你好")
        assert len(results) == 2

    def test_mixed_language_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="你好 world"))
        idx.add_document(Document(doc_id="doc2", content="hello 世界"))
        results = idx.search("hello 世界")
        assert len(results) == 1
        assert results[0].doc_id == "doc2"

    def test_bm25_score_with_higher_freq(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="apple apple apple banana"))
        idx.add_document(Document(doc_id="doc2", content="apple banana"))
        results = idx.search("apple")
        assert results[0].doc_id == "doc1"
        assert results[0].score > results[1].score

    def test_bm25_score_with_idf(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="rare term"))
        idx.add_document(Document(doc_id="doc2", content="common term"))
        idx.add_document(Document(doc_id="doc3", content="common word"))
        idx.add_document(Document(doc_id="doc4", content="common phrase"))
        results = idx.search("rare common")
        doc1 = next(r for r in results if r.doc_id == "doc1")
        doc2 = next(r for r in results if r.doc_id == "doc2")
        assert doc1.score > doc2.score

    def test_stemming_consistency_index_and_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="connecting connections"))
        results1 = idx.search("connect")
        results2 = idx.search("connecting")
        results3 = idx.search("connections")
        assert len(results1) == 1
        assert len(results2) == 1
        assert len(results3) == 1
        assert results1[0].doc_id == results2[0].doc_id == results3[0].doc_id


class TestBoundaryConditions:
    def test_empty_document_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content=""))
        assert idx.total_docs == 1
        assert idx.avg_doc_length == 0.0
        assert idx.get_document("doc1").content == ""

    def test_empty_document_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content=""))
        idx.add_document(Document(doc_id="doc2", content="hello world"))
        results = idx.search("hello")
        assert len(results) == 1
        assert results[0].doc_id == "doc2"

    def test_stopword_only_query_returns_empty(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="the quick brown fox"))
        results = idx.search("the a an is")
        assert len(results) == 0

    def test_document_deleted_not_searchable(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        idx.remove_document("doc1")
        results = idx.search("world")
        assert len(results) == 0
        results_hello = idx.search("hello")
        assert len(results_hello) == 1
        assert results_hello[0].doc_id == "doc2"

    def test_empty_index_search_returns_empty(self):
        idx = FullTextIndex()
        results = idx.search("hello")
        assert results == []

    def test_search_term_not_in_any_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("nonexistenttermxyz")
        assert results == []

    def test_add_empty_content_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content=""))
        assert idx.contains_document("doc1")
        assert idx.total_docs == 1

    def test_stopwords_filtered_in_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="the and is are of to"))
        assert idx.get_term_frequency("the", "doc1") == 0
        assert idx.get_term_frequency("and", "doc1") == 0
        assert idx.get_term_frequency("is", "doc1") == 0
        assert idx.avg_doc_length == 0.0

    def test_bm25_k1_zero(self):
        idx = FullTextIndex(k1=0.0, b=0.75)
        idx.add_document(Document(doc_id="doc1", content="apple apple apple"))
        idx.add_document(Document(doc_id="doc2", content="apple"))
        results = idx.search("apple")
        assert len(results) == 2
        assert abs(results[0].score - results[1].score) < 0.001

    def test_bm25_b_one(self):
        idx = FullTextIndex(k1=1.5, b=1.0)
        idx.add_document(Document(doc_id="doc1", content="apple banana cherry date elderberry"))
        idx.add_document(Document(doc_id="doc2", content="apple"))
        results = idx.search("apple")
        assert len(results) == 2
        assert results[0].doc_id == "doc2"

    def test_bm25_k1_zero_b_one(self):
        idx = FullTextIndex(k1=0.0, b=1.0)
        idx.add_document(Document(doc_id="doc1", content="apple apple apple"))
        idx.add_document(Document(doc_id="doc2", content="apple banana cherry"))
        results = idx.search("apple")
        assert len(results) == 2

    def test_single_term_single_doc(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="test"))
        results = idx.search("test")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_all_docs_contain_term(self):
        idx = FullTextIndex()
        for i in range(5):
            idx.add_document(Document(doc_id=f"doc{i}", content=f"common term {i}"))
        results = idx.search("common")
        assert len(results) == 5

    def test_empty_query_string(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("")
        assert results == []

    def test_only_spaces_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("     ")
        assert results == []

    def test_only_punctuation_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("!!!???,,,")
        assert results == []

    def test_whitespace_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="     "))
        assert idx.total_docs == 1
        assert idx.avg_doc_length == 0.0

    def test_punctuation_only_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="!!!???,,,.."))
        assert idx.total_docs == 1
        assert idx.avg_doc_length == 0.0

    def test_top_k_larger_than_results(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("hello", top_k=100)
        assert len(results) == 1

    def test_top_k_zero(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("hello", top_k=0)
        assert len(results) == 0


class TestExceptionBranches:
    def test_add_document_without_doc_id(self):
        idx = FullTextIndex()
        with pytest.raises(InvalidDocumentError):
            idx.add_document(Document(doc_id="", content="test"))

    def test_add_none_document(self):
        idx = FullTextIndex()
        with pytest.raises(InvalidDocumentError):
            idx.add_document(None)

    def test_remove_nonexistent_document(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello"))
        with pytest.raises(DocumentNotFoundError):
            idx.remove_document("nonexistent")

    def test_remove_from_empty_index(self):
        idx = FullTextIndex()
        with pytest.raises(DocumentNotFoundError):
            idx.remove_document("doc1")

    def test_update_document_preserves_total(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc1", content="hello python"))
        assert idx.total_docs == 1

    def test_update_document_cleans_old_terms(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        idx.add_document(Document(doc_id="doc1", content="hello python"))
        assert idx.get_term_frequency("world", "doc1") == 0
        assert idx.get_term_frequency("python", "doc1") == 1
        assert idx.get_document_frequency("world") == 0

    def test_query_terms_case_insensitive(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="Hello WORLD"))
        results1 = idx.search("hello")
        results2 = idx.search("HELLO")
        results3 = idx.search("Hello")
        assert len(results1) == 1
        assert len(results2) == 1
        assert len(results3) == 1

    def test_digit_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="test 123 document"))
        results = idx.search("123")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_contraction_search(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="don't stop believing"))
        results = idx.search("don't")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_term_not_in_index_returns_zero(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        assert idx.get_term_frequency("missing", "doc1") == 0
        assert idx.get_term_positions("missing", "doc1") == []
        assert idx.get_document_frequency("missing") == 0

    def test_bm25_with_different_length_docs(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="apple"))
        idx.add_document(Document(doc_id="doc2", content="apple " * 100))
        results = idx.search("apple")
        assert len(results) == 2
        assert results[0].score > results[1].score or results[1].score > results[0].score

    def test_duplicate_terms_in_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results = idx.search("hello hello world")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"

    def test_custom_stopword_in_query(self):
        idx = FullTextIndex(extra_stopwords={"apple"})
        idx.add_document(Document(doc_id="doc1", content="apple banana"))
        results = idx.search("apple")
        assert len(results) == 0
        results_banana = idx.search("banana")
        assert len(results_banana) == 1

    def test_incremental_add_search(self):
        idx = FullTextIndex()
        results1 = idx.search("hello")
        assert len(results1) == 0
        idx.add_document(Document(doc_id="doc1", content="hello world"))
        results2 = idx.search("hello")
        assert len(results2) == 1
        idx.add_document(Document(doc_id="doc2", content="hello python"))
        results3 = idx.search("hello")
        assert len(results3) == 2

    def test_remove_then_search_term_removed(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="unique term here"))
        idx.add_document(Document(doc_id="doc2", content="common term"))
        idx.remove_document("doc1")
        results = idx.search("unique")
        assert len(results) == 0

    def test_stopword_added_after_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="apple banana"))
        results_before = idx.search("apple")
        assert len(results_before) == 1
        idx.stopwords.add("apple")
        results_after = idx.search("apple")
        assert len(results_after) == 0

    def test_non_english_word_not_stemmed(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="你好世界"))
        assert stem_word("你好") == "你好"
        assert idx.get_term_frequency("你好", "doc1") == 0
        assert idx.get_term_frequency("你", "doc1") == 1


class TestMultiCharChineseStopwordsInIndex:
    def test_multi_char_chinese_stopwords_filtered_on_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="我们是一个测试"))
        assert idx.get_term_frequency("我", "doc1") == 0
        assert idx.get_term_frequency("们", "doc1") == 0
        assert idx.get_term_frequency("一", "doc1") == 0
        assert idx.get_term_frequency("个", "doc1") == 0
        assert idx.get_term_frequency("我们", "doc1") == 0
        assert idx.get_term_frequency("一个", "doc1") == 0
        assert idx.get_term_frequency("测", "doc1") == 1
        assert idx.get_term_frequency("试", "doc1") == 1

    def test_three_char_chinese_stopwords_filtered_on_index(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="为什么这样测试"))
        assert idx.get_term_frequency("为", "doc1") == 0
        assert idx.get_term_frequency("什", "doc1") == 0
        assert idx.get_term_frequency("么", "doc1") == 0
        assert idx.get_term_frequency("为什么", "doc1") == 0
        assert idx.get_term_frequency("测", "doc1") == 1
        assert idx.get_term_frequency("试", "doc1") == 1

    def test_multi_char_chinese_stopwords_filtered_on_query(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="Python 是一个编程测试"))
        results = idx.search("一个编程测试")
        assert len(results) == 1
        assert results[0].doc_id == "doc1"
        assert "一" not in results[0].matched_terms
        assert "个" not in results[0].matched_terms

    def test_multi_char_stopword_only_query_returns_empty(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="我们是一个测试"))
        results = idx.search("我们一个为什么")
        assert len(results) == 0

    def test_combined_single_and_multi_char_stopwords(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="我们的一个很好的测试"))
        assert idx.get_term_frequency("我", "doc1") == 0
        assert idx.get_term_frequency("们", "doc1") == 0
        assert idx.get_term_frequency("的", "doc1") == 0
        assert idx.get_term_frequency("一", "doc1") == 0
        assert idx.get_term_frequency("个", "doc1") == 0
        assert idx.get_term_frequency("很", "doc1") == 1
        assert idx.get_term_frequency("好", "doc1") == 1
        assert idx.get_term_frequency("测", "doc1") == 1
        assert idx.get_term_frequency("试", "doc1") == 1

    def test_custom_multi_char_stopword_in_index(self):
        idx = FullTextIndex(extra_stopwords={"测试词"})
        idx.add_document(Document(doc_id="doc1", content="这是测试词编程"))
        assert idx.get_term_frequency("测", "doc1") == 0
        assert idx.get_term_frequency("试", "doc1") == 0
        assert idx.get_term_frequency("词", "doc1") == 0
        assert idx.get_term_frequency("编", "doc1") == 1
        assert idx.get_term_frequency("程", "doc1") == 1

    def test_custom_multi_char_stopword_dynamically_added(self):
        idx = FullTextIndex()
        idx.add_document(Document(doc_id="doc1", content="测试词编程"))
        results_before = idx.search("测试词")
        assert len(results_before) == 1
        idx.stopwords.add("测试词")
        idx.add_document(Document(doc_id="doc2", content="另一个测试词"))
        assert idx.get_term_frequency("测", "doc2") == 0
        assert idx.get_term_frequency("试", "doc2") == 0
        assert idx.get_term_frequency("词", "doc2") == 0
