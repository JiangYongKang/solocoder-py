import math

import pytest

from solocoder_py.inverted_index import (
    DocumentExistsError,
    EmptyQueryError,
    InvertedIndex,
    InvalidCursorError,
    Posting,
    SearchResponse,
)


class TestInvertedIndexBuild:
    def test_add_single_document(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        assert idx.document_count == 1

    def test_add_multiple_documents(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "hello python")
        assert idx.document_count == 2

    def test_add_duplicate_document_raises(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(DocumentExistsError):
            idx.add_document("doc1", "another text")

    def test_vocabulary_size(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        assert idx.vocabulary_size == 2

    def test_vocabulary_deduplication(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello world")
        assert idx.vocabulary_size == 2

    def test_incremental_add_preserves_existing(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta")
        idx.add_document("doc2", "alpha gamma")
        postings = idx.get_postings("alpha")
        doc_ids = {p.doc_id for p in postings}
        assert doc_ids == {"doc1", "doc2"}

    def test_tokenization_case_insensitive(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "Hello HELLO hello")
        postings = idx.get_postings("hello")
        assert len(postings) == 1
        assert postings[0].term_freq == 3

    def test_tokenization_ignores_punctuation(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello, world! foo-bar")
        assert idx.vocabulary_size == 4

    def test_empty_content_document(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "")
        assert idx.document_count == 1
        assert idx.vocabulary_size == 0

    def test_get_postings_existing_term(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world hello")
        postings = idx.get_postings("hello")
        assert len(postings) == 1
        assert postings[0].doc_id == "doc1"
        assert postings[0].term_freq == 2

    def test_get_postings_nonexistent_term(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        postings = idx.get_postings("missing")
        assert postings == []


class TestSingleWordSearch:
    def test_single_term_search(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "python world")
        resp = idx.search(["world"])
        assert resp.total_count == 2
        doc_ids = {r.doc_id for r in resp.results}
        assert doc_ids == {"doc1", "doc2"}

    def test_single_term_returns_all_matching(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha")
        idx.add_document("doc2", "beta")
        idx.add_document("doc3", "alpha beta")
        resp = idx.search(["alpha"])
        assert resp.total_count == 2
        doc_ids = {r.doc_id for r in resp.results}
        assert doc_ids == {"doc1", "doc3"}

    def test_single_term_case_insensitive(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "Hello World")
        resp = idx.search(["hello"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"


class TestMultiWordIntersection:
    def test_two_term_intersection(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "hello python")
        idx.add_document("doc3", "world python")
        resp = idx.search(["hello", "world"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_three_term_intersection(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta gamma")
        idx.add_document("doc2", "alpha beta")
        idx.add_document("doc3", "alpha gamma")
        resp = idx.search(["alpha", "beta", "gamma"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_intersection_no_common_docs(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta")
        idx.add_document("doc2", "gamma delta")
        resp = idx.search(["alpha", "gamma"])
        assert resp.total_count == 0
        assert resp.results == []

    def test_one_term_missing_from_index(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["hello", "missing"])
        assert resp.total_count == 0


class TestTFIDFScoring:
    def test_higher_tf_gets_higher_score(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello hello world")
        idx.add_document("doc2", "hello world")
        resp = idx.search(["hello"])
        doc1_score = next(r.score for r in resp.results if r.doc_id == "doc1")
        doc2_score = next(r.score for r in resp.results if r.doc_id == "doc2")
        assert doc1_score > doc2_score

    def test_rare_term_gets_higher_idf(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "common rare")
        idx.add_document("doc2", "common other")
        idx.add_document("doc3", "common another")
        resp_rare = idx.search(["rare"])
        resp_common = idx.search(["common"])
        rare_score = resp_rare.results[0].score
        common_score_per_doc = [r.score for r in resp_common.results]
        rare_idf = math.log((1 + 3) / (1 + 1)) + 1
        common_idf = math.log((1 + 3) / (1 + 3)) + 1
        assert rare_idf > common_idf
        assert rare_score > max(common_score_per_doc)

    def test_results_sorted_by_score_descending(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello hello")
        idx.add_document("doc2", "hello")
        idx.add_document("doc3", "hello hello")
        resp = idx.search(["hello"])
        scores = [r.score for r in resp.results]
        assert scores == sorted(scores, reverse=True)

    def test_tie_breaking_by_doc_id(self):
        idx = InvertedIndex()
        idx.add_document("b", "hello")
        idx.add_document("a", "hello")
        resp = idx.search(["hello"])
        assert resp.results[0].doc_id == "a"
        assert resp.results[1].doc_id == "b"

    def test_multi_term_score_is_sum(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha alpha beta")
        idx.add_document("doc2", "alpha beta")
        resp = idx.search(["alpha", "beta"])
        assert resp.total_count == 2
        doc1_score = next(r.score for r in resp.results if r.doc_id == "doc1")
        doc2_score = next(r.score for r in resp.results if r.doc_id == "doc2")
        assert doc1_score > doc2_score

    def test_tf_idf_formula_correctness(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello world")
        idx.add_document("doc2", "hello world world")
        resp = idx.search(["hello", "world"])
        n = 2
        hello_df = 2
        world_df = 2
        hello_idf = math.log((1 + n) / (1 + hello_df)) + 1
        world_idf = math.log((1 + n) / (1 + world_df)) + 1
        doc1_expected = 2 * hello_idf + 1 * world_idf
        doc2_expected = 1 * hello_idf + 2 * world_idf
        doc1_actual = next(r.score for r in resp.results if r.doc_id == "doc1")
        doc2_actual = next(r.score for r in resp.results if r.doc_id == "doc2")
        assert abs(doc1_actual - doc1_expected) < 1e-9
        assert abs(doc2_actual - doc2_expected) < 1e-9


class TestPagination:
    def test_first_page(self):
        idx = InvertedIndex()
        for i in range(5):
            idx.add_document(f"doc{i}", "hello world")
        resp = idx.search(["hello"], page_size=2)
        assert len(resp.results) == 2
        assert resp.total_count == 5
        assert resp.next_cursor is not None

    def test_second_page_via_cursor(self):
        idx = InvertedIndex()
        for i in range(5):
            idx.add_document(f"doc{i}", "hello world")
        page1 = idx.search(["hello"], page_size=2)
        page2 = idx.search(["hello"], page_size=2, cursor=page1.next_cursor)
        assert len(page2.results) == 2
        page1_ids = {r.doc_id for r in page1.results}
        page2_ids = {r.doc_id for r in page2.results}
        assert page1_ids.isdisjoint(page2_ids)

    def test_last_page_no_cursor(self):
        idx = InvertedIndex()
        for i in range(5):
            idx.add_document(f"doc{i}", "hello world")
        page1 = idx.search(["hello"], page_size=2)
        page2 = idx.search(["hello"], page_size=2, cursor=page1.next_cursor)
        page3 = idx.search(["hello"], page_size=2, cursor=page2.next_cursor)
        assert len(page3.results) == 1
        assert page3.next_cursor is None

    def test_all_pages_cover_all_docs(self):
        idx = InvertedIndex()
        for i in range(7):
            idx.add_document(f"doc{i}", "hello world")
        all_doc_ids: set[str] = set()
        cursor = None
        while True:
            resp = idx.search(["hello"], page_size=3, cursor=cursor)
            all_doc_ids.update(r.doc_id for r in resp.results)
            if resp.next_cursor is None:
                break
            cursor = resp.next_cursor
        assert all_doc_ids == {f"doc{i}" for i in range(7)}

    def test_page_size_larger_than_results(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "hello")
        resp = idx.search(["hello"], page_size=100)
        assert len(resp.results) == 2
        assert resp.next_cursor is None

    def test_page_size_one(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "hello")
        resp = idx.search(["hello"], page_size=1)
        assert len(resp.results) == 1
        assert resp.next_cursor is not None

    def test_cursor_stable_after_new_document(self):
        idx = InvertedIndex()
        for i in range(4):
            idx.add_document(f"doc{i}", "hello world")
        page1 = idx.search(["hello"], page_size=2)
        cursor = page1.next_cursor
        idx.add_document("doc_new", "hello world")
        page2 = idx.search(["hello"], page_size=2, cursor=cursor)
        page1_ids = {r.doc_id for r in page1.results}
        page2_ids = {r.doc_id for r in page2.results}
        assert page1_ids.isdisjoint(page2_ids)

    def test_cursor_preserves_score_ordering(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "hello hello")
        idx.add_document("doc3", "hello hello hello")
        page1 = idx.search(["hello"], page_size=2)
        page2 = idx.search(["hello"], page_size=2, cursor=page1.next_cursor)
        all_results = page1.results + page2.results
        scores = [r.score for r in all_results]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_cursor_raises(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        with pytest.raises(InvalidCursorError):
            idx.search(["hello"], cursor="not-valid-base64!!!")


class TestEmptyIndex:
    def test_search_empty_index(self):
        idx = InvertedIndex()
        resp = idx.search(["hello"])
        assert resp.total_count == 0
        assert resp.results == []

    def test_document_count_empty(self):
        idx = InvertedIndex()
        assert idx.document_count == 0

    def test_vocabulary_size_empty(self):
        idx = InvertedIndex()
        assert idx.vocabulary_size == 0

    def test_get_postings_empty_index(self):
        idx = InvertedIndex()
        assert idx.get_postings("hello") == []


class TestNonexistentTerm:
    def test_search_term_not_in_index(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["missing"])
        assert resp.total_count == 0
        assert resp.results == []


class TestEmptyQuery:
    def test_empty_query_terms_raises(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(EmptyQueryError):
            idx.search([])

    def test_whitespace_only_query_raises(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(EmptyQueryError):
            idx.search(["  ", "  "])


class TestSingleDocumentMultipleWords:
    def test_single_doc_multi_word_search(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta gamma delta")
        resp = idx.search(["alpha", "gamma"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_single_doc_partial_match_no_result(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta")
        resp = idx.search(["alpha", "missing"])
        assert resp.total_count == 0


class TestPageLessThanOnePage:
    def test_results_fewer_than_page_size(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        resp = idx.search(["hello"], page_size=10)
        assert len(resp.results) == 1
        assert resp.next_cursor is None

    def test_results_exactly_page_size(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "hello")
        resp = idx.search(["hello"], page_size=2)
        assert len(resp.results) == 2
        assert resp.next_cursor is None


class TestRepeatedTerms:
    def test_repeated_query_terms_treated_as_one(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["hello", "hello"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_repeated_terms_in_document(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello hello")
        postings = idx.get_postings("hello")
        assert len(postings) == 1
        assert postings[0].term_freq == 3

    def test_deduplicated_query_terms_same_score_as_single(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello hello world")
        resp_single = idx.search(["hello"])
        resp_dup = idx.search(["hello", "hello", "hello"])
        assert resp_single.results[0].score == resp_dup.results[0].score

    def test_deduplicated_multi_term_same_score(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "alpha beta alpha")
        resp_unique = idx.search(["alpha", "beta"])
        resp_dup = idx.search(["alpha", "beta", "alpha", "beta"])
        assert resp_unique.results[0].score == resp_dup.results[0].score


class TestQueryPunctuationNormalization:
    def test_query_with_exclamation_mark(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["hello!"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_query_with_comma(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["hello,"])
        assert resp.total_count == 1

    def test_query_with_hyphen(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "foo bar")
        resp = idx.search(["foo-bar"])
        assert resp.total_count == 1

    def test_query_with_mixed_punctuation(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        resp = idx.search(["(hello)", "world!"])
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_get_postings_with_punctuation(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello world")
        postings = idx.get_postings("hello!")
        assert len(postings) == 1
        assert postings[0].term_freq == 1


class TestCursorEncoding:
    def test_cursor_roundtrip(self):
        cursor = InvertedIndex._encode_cursor(1.5, "doc42")
        score, doc_id = InvertedIndex._decode_cursor(cursor)
        assert score == 1.5
        assert doc_id == "doc42"

    def test_cursor_with_special_doc_id(self):
        cursor = InvertedIndex._encode_cursor(0.0, "doc:with:colons")
        score, doc_id = InvertedIndex._decode_cursor(cursor)
        assert score == 0.0
        assert doc_id == "doc:with:colons"

    def test_cursor_with_negative_score(self):
        cursor = InvertedIndex._encode_cursor(-3.14, "doc1")
        score, doc_id = InvertedIndex._decode_cursor(cursor)
        assert abs(score - (-3.14)) < 1e-9
        assert doc_id == "doc1"


class TestEdgeCases:
    def test_single_char_tokens(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "a b c")
        resp = idx.search(["a", "b"])
        assert resp.total_count == 1

    def test_numeric_tokens(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "item 42 item 42")
        resp = idx.search(["42"])
        assert resp.total_count == 1
        postings = idx.get_postings("42")
        assert postings[0].term_freq == 2

    def test_underscore_tokens(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello_world foo_bar")
        assert idx.vocabulary_size == 2

    def test_large_number_of_documents(self):
        idx = InvertedIndex()
        n = 200
        for i in range(n):
            idx.add_document(f"doc{i}", f"hello term{i}")
        resp = idx.search(["hello"])
        assert resp.total_count == n

    def test_pagination_across_many_pages(self):
        idx = InvertedIndex()
        n = 50
        for i in range(n):
            idx.add_document(f"doc{i}", "hello world")
        collected: list[str] = []
        cursor = None
        pages = 0
        while True:
            resp = idx.search(["hello"], page_size=5, cursor=cursor)
            collected.extend(r.doc_id for r in resp.results)
            pages += 1
            if resp.next_cursor is None:
                break
            cursor = resp.next_cursor
        assert len(collected) == n
        assert len(set(collected)) == n
        assert pages == 10

    def test_score_zero_when_all_terms_common(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "the the the")
        idx.add_document("doc2", "the the")
        idx.add_document("doc3", "the")
        n = 3
        df = 3
        idf = math.log((1 + n) / (1 + df)) + 1
        assert idf > 0
        resp = idx.search(["the"])
        assert all(r.score > 0 for r in resp.results)

    def test_cursor_with_none_returns_first_page(self):
        idx = InvertedIndex()
        idx.add_document("doc1", "hello")
        page1 = idx.search(["hello"], page_size=1)
        assert page1.next_cursor is None
        page2 = idx.search(["hello"], page_size=1, cursor=None)
        assert len(page2.results) == 1
        assert page2.results[0].doc_id == "doc1"
