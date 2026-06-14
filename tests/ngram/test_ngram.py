import pytest

from solocoder_py.ngram import (
    DocumentExistsError,
    DocumentNotFoundError,
    EmptyQueryError,
    InvalidContextSizeError,
    InvalidNValueError,
    NGramIndex,
)


class TestNGramIndexInit:
    def test_default_n_is_2(self):
        idx = NGramIndex()
        assert idx.n == 2

    def test_custom_n_value(self):
        idx = NGramIndex(n=3)
        assert idx.n == 3

    def test_n_equals_1_is_valid(self):
        idx = NGramIndex(n=1)
        assert idx.n == 1

    def test_n_zero_raises(self):
        with pytest.raises(InvalidNValueError):
            NGramIndex(n=0)

    def test_n_negative_raises(self):
        with pytest.raises(InvalidNValueError):
            NGramIndex(n=-1)


class TestAddDocument:
    def test_add_single_document(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        assert idx.document_count == 1

    def test_add_multiple_documents(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "hello python")
        assert idx.document_count == 2

    def test_add_duplicate_document_raises(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(DocumentExistsError):
            idx.add_document("doc1", "another text")

    def test_add_empty_document(self):
        idx = NGramIndex()
        idx.add_document("doc1", "")
        assert idx.document_count == 1
        assert idx.gram_count == 0

    def test_add_document_shorter_than_n(self):
        idx = NGramIndex(n=5)
        idx.add_document("doc1", "abc")
        assert idx.document_count == 1
        assert idx.gram_count == 0


class TestRemoveDocument:
    def test_remove_existing_document(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        idx.remove_document("doc1")
        assert idx.document_count == 0

    def test_remove_nonexistent_document_raises(self):
        idx = NGramIndex()
        with pytest.raises(DocumentNotFoundError):
            idx.remove_document("missing")

    def test_remove_document_removes_grams(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello")
        gram_count_before = idx.gram_count
        assert gram_count_before > 0
        idx.remove_document("doc1")
        assert idx.gram_count == 0

    def test_remove_document_shared_grams_preserved(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "hello python")
        idx.remove_document("doc1")
        assert idx.document_count == 1
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc2"


class TestNormalFlowBigramSearch:
    def test_search_returns_correct_document(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "the quick brown fox")
        idx.add_document("doc2", "the lazy dog")
        resp = idx.search("quick")
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"

    def test_search_hit_positions_correct(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "the quick quick brown")
        resp = idx.search("quick")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [4, 10]

    def test_search_highlight_wraps_substring(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("world", context_size=3)
        assert resp.total_count == 1
        frag = resp.results[0].fragments[0]
        assert "[[world]]" in frag.text

    def test_search_highlight_with_custom_markers(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search(
            "world", context_size=3,
            highlight_start="<b>", highlight_end="</b>",
        )
        frag = resp.results[0].fragments[0]
        assert "<b>world</b>" in frag.text

    def test_search_multiple_matches_in_multiple_docs(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "apple pie and apple juice")
        idx.add_document("doc2", "apple banana orange")
        idx.add_document("doc3", "orange grape")
        resp = idx.search("apple")
        assert resp.total_count == 2
        doc_ids = {r.doc_id for r in resp.results}
        assert doc_ids == {"doc1", "doc2"}
        doc1 = next(r for r in resp.results if r.doc_id == "doc1")
        assert doc1.hit_positions == [0, 14]


class TestBoundaryConditions:
    def test_n_equals_text_length(self):
        idx = NGramIndex(n=5)
        idx.add_document("doc1", "hello")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]

    def test_n_greater_than_text_length(self):
        idx = NGramIndex(n=10)
        idx.add_document("doc1", "hello")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]

    def test_n_equals_1_unigram(self):
        idx = NGramIndex(n=1)
        idx.add_document("doc1", "abcde")
        idx.add_document("doc2", "fghij")
        resp = idx.search("bcd")
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"
        assert resp.results[0].hit_positions == [1]

    def test_unigram_search_single_char(self):
        idx = NGramIndex(n=1)
        idx.add_document("doc1", "hello")
        resp = idx.search("l")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [2, 3]

    def test_empty_text_in_index(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "")
        idx.add_document("doc2", "hello world")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc2"

    def test_search_nonexistent_substring(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("missing")
        assert resp.total_count == 0
        assert resp.results == []

    def test_query_length_1_single_gram_search(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        resp = idx.search("h")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]

    def test_query_at_end_of_text(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("world")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [6]

    def test_query_at_start_of_text(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]

    def test_query_equal_to_text(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]


class TestExceptionBranches:
    def test_empty_query_raises(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(EmptyQueryError):
            idx.search("")

    def test_negative_context_size_raises(self):
        idx = NGramIndex()
        idx.add_document("doc1", "hello world")
        with pytest.raises(InvalidContextSizeError):
            idx.search("hello", context_size=-1)

    def test_remove_then_search_not_found(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "goodbye world")
        idx.remove_document("doc1")
        resp = idx.search("hello")
        assert resp.total_count == 0
        resp_world = idx.search("world")
        assert resp_world.total_count == 1
        assert resp_world.results[0].doc_id == "doc2"

    def test_cross_doc_gram_no_false_match(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "ab")
        idx.add_document("doc2", "bc")
        resp = idx.search("abc")
        assert resp.total_count == 0

    def test_cross_doc_position_no_pollution(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "world hello")
        resp = idx.search("hello")
        assert resp.total_count == 2
        doc1 = next(r for r in resp.results if r.doc_id == "doc1")
        doc2 = next(r for r in resp.results if r.doc_id == "doc2")
        assert doc1.hit_positions == [0]
        assert doc2.hit_positions == [6]

    def test_highlight_bounds_safe_start(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("hello", context_size=100)
        frag = resp.results[0].fragments[0]
        assert frag.text.startswith("[[hello]]")

    def test_highlight_bounds_safe_end(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("world", context_size=100)
        frag = resp.results[0].fragments[0]
        assert frag.text.endswith("[[world]]")

    def test_highlight_context_zero(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        resp = idx.search("world", context_size=0)
        frag = resp.results[0].fragments[0]
        assert frag.text == "[[world]]"

    def test_add_then_remove_then_add_again(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        idx.remove_document("doc1")
        idx.add_document("doc1", "hello again")
        resp_world = idx.search("world")
        assert resp_world.total_count == 0
        resp_again = idx.search("again")
        assert resp_again.total_count == 1


class TestGramPostings:
    def test_get_gram_postings_existing(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        postings = idx.get_gram_postings("he")
        assert len(postings) == 1
        assert postings[0].doc_id == "doc1"
        assert postings[0].positions == [0]

    def test_get_gram_postings_multiple_docs(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "help")
        postings = idx.get_gram_postings("he")
        doc_ids = {p.doc_id for p in postings}
        assert doc_ids == {"doc1", "doc2"}

    def test_get_gram_postings_nonexistent(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        postings = idx.get_gram_postings("xyz")
        assert postings == []


class TestTrigramIndex:
    def test_trigram_search(self):
        idx = NGramIndex(n=3)
        idx.add_document("doc1", "the quick brown fox")
        idx.add_document("doc2", "the lazy dog")
        resp = idx.search("quick")
        assert resp.total_count == 1
        assert resp.results[0].doc_id == "doc1"
        assert resp.results[0].hit_positions == [4]

    def test_trigram_positions_multiple(self):
        idx = NGramIndex(n=3)
        idx.add_document("doc1", "abcabcabc")
        resp = idx.search("abc")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0, 3, 6]


class TestOverlappingHits:
    def test_overlapping_substrings(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "aaaaa")
        resp = idx.search("aa")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0, 1, 2, 3]

    def test_overlapping_substrings_unigram(self):
        idx = NGramIndex(n=1)
        idx.add_document("doc1", "aaaaa")
        resp = idx.search("aa")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0, 1, 2, 3]


class TestIncrementalAddPreservesExisting:
    def test_incremental_add(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "alpha beta")
        idx.add_document("doc2", "alpha gamma")
        resp = idx.search("alpha")
        assert resp.total_count == 2
        doc_ids = {r.doc_id for r in resp.results}
        assert doc_ids == {"doc1", "doc2"}

    def test_gram_count_increments(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        count1 = idx.gram_count
        idx.add_document("doc2", "world")
        count2 = idx.gram_count
        assert count2 > count1


class TestSearchResultsOrdering:
    def test_results_sorted_by_hit_count_descending(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "apple apple apple")
        idx.add_document("doc2", "apple")
        resp = idx.search("apple")
        assert resp.results[0].doc_id == "doc1"
        assert resp.results[1].doc_id == "doc2"

    def test_tie_breaking_by_doc_id(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc2", "hello")
        idx.add_document("doc1", "hello")
        resp = idx.search("hello")
        assert resp.results[0].doc_id == "doc1"
        assert resp.results[1].doc_id == "doc2"


class TestUnicodeAndSpecialChars:
    def test_unicode_text_search(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "你好世界")
        resp = idx.search("世界")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [2]

    def test_special_chars_search(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "foo-bar.baz")
        resp = idx.search("-bar")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [3]

    def test_spaces_in_query(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world foo")
        resp = idx.search("o wo")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [4]


class TestHighlightFragmentOffsets:
    def test_fragment_hit_offsets_correct(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "AAAhelloBBB")
        resp = idx.search("hello", context_size=3)
        frag = resp.results[0].fragments[0]
        assert frag.hit_start == 3
        assert frag.hit_end == 3 + len("[[") + len("hello") + len("]]")
        assert frag.text[3:3 + len("[[") + len("hello") + len("]]")] == "[[hello]]"

    def test_fragment_hit_offsets_no_context(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        resp = idx.search("hello", context_size=0)
        frag = resp.results[0].fragments[0]
        assert frag.hit_start == 0
        assert frag.text == "[[hello]]"


class TestUpdateDocument:
    def test_update_replaces_content(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        idx.update_document("doc1", "hello python")
        resp_world = idx.search("world")
        assert resp_world.total_count == 0
        resp_python = idx.search("python")
        assert resp_python.total_count == 1
        assert resp_python.results[0].doc_id == "doc1"
        assert resp_python.results[0].hit_positions == [6]

    def test_update_old_content_not_searchable(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "the quick brown fox")
        idx.update_document("doc1", "the lazy dog")
        resp_fox = idx.search("fox")
        assert resp_fox.total_count == 0
        resp_brown = idx.search("brown")
        assert resp_brown.total_count == 0
        resp_quick = idx.search("quick")
        assert resp_quick.total_count == 0

    def test_update_new_content_searchable(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "old text here")
        idx.update_document("doc1", "brand new content")
        resp_new = idx.search("new")
        assert resp_new.total_count == 1
        assert resp_new.results[0].hit_positions == [6]
        resp_brand = idx.search("brand")
        assert resp_brand.total_count == 1
        assert resp_brand.results[0].hit_positions == [0]

    def test_update_other_docs_unaffected(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "apple banana")
        idx.add_document("doc2", "cherry date")
        idx.update_document("doc1", "apricot elderberry")
        resp_banana = idx.search("banana")
        assert resp_banana.total_count == 0
        resp_cherry = idx.search("cherry")
        assert resp_cherry.total_count == 1
        assert resp_cherry.results[0].doc_id == "doc2"
        resp_apricot = idx.search("apricot")
        assert resp_apricot.total_count == 1
        assert resp_apricot.results[0].doc_id == "doc1"

    def test_update_nonexistent_doc_raises(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        with pytest.raises(DocumentNotFoundError):
            idx.update_document("missing", "new content")

    def test_update_preserves_document_count(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        idx.add_document("doc2", "world")
        count_before = idx.document_count
        idx.update_document("doc1", "hello updated")
        assert idx.document_count == count_before

    def test_update_same_shared_grams_preserved(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        idx.add_document("doc2", "hello python")
        idx.update_document("doc1", "hello java")
        resp_hello = idx.search("hello")
        assert resp_hello.total_count == 2
        doc_ids = {r.doc_id for r in resp_hello.results}
        assert doc_ids == {"doc1", "doc2"}

    def test_update_hit_positions_correct_after_change(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "abcdef")
        idx.update_document("doc1", "xyzabc")
        resp = idx.search("abc")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [3]

    def test_update_from_empty_to_nonempty(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "")
        idx.update_document("doc1", "hello world")
        resp = idx.search("hello")
        assert resp.total_count == 1
        assert resp.results[0].hit_positions == [0]

    def test_update_from_nonempty_to_empty(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello world")
        idx.update_document("doc1", "")
        resp = idx.search("hello")
        assert resp.total_count == 0
        assert idx.document_count == 1

    def test_update_highlights_correct_after_update(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "AAAhelloBBB")
        idx.update_document("doc1", "XXXhelloYYY")
        resp = idx.search("hello", context_size=3)
        frag = resp.results[0].fragments[0]
        assert "XXX[[hello]]YYY" in frag.text

    def test_update_multiple_times(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "version one")
        idx.update_document("doc1", "version two")
        idx.update_document("doc1", "version three")
        resp_one = idx.search("one")
        assert resp_one.total_count == 0
        resp_two = idx.search("two")
        assert resp_two.total_count == 0
        resp_three = idx.search("three")
        assert resp_three.total_count == 1
        assert resp_three.results[0].hit_positions == [8]

    def test_update_gram_count_updated(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "hello")
        count_before = idx.gram_count
        idx.update_document("doc1", "hello world")
        count_after = idx.gram_count
        assert count_after > count_before

    def test_update_trigram_index(self):
        idx = NGramIndex(n=3)
        idx.add_document("doc1", "abcdef")
        idx.update_document("doc1", "xyzabcdef")
        resp_abc = idx.search("abc")
        assert resp_abc.total_count == 1
        assert resp_abc.results[0].hit_positions == [3]
        resp_xyz = idx.search("xyz")
        assert resp_xyz.total_count == 1
        assert resp_xyz.results[0].hit_positions == [0]

    def test_update_overlapping_content(self):
        idx = NGramIndex(n=2)
        idx.add_document("doc1", "aaaaa")
        idx.update_document("doc1", "aaabaaa")
        resp_aaa = idx.search("aaa")
        assert resp_aaa.total_count == 1
        assert resp_aaa.results[0].hit_positions == [0, 4]
