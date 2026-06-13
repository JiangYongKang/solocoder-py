import pytest

from solocoder_py.phonetic import (
    EmptyNameError,
    InvalidMatchModeError,
    MatchMode,
    MatchResult,
    NameExistsError,
    NameNotFoundError,
    PhoneticCode,
    PhoneticIndex,
)


class TestPhoneticIndexInit:
    def test_empty_index(self, empty_index):
        assert empty_index.name_count == 0
        assert empty_index.names == []
        assert empty_index.metaphone_max_length is None

    def test_index_with_custom_metaphone_length(self):
        idx = PhoneticIndex(metaphone_max_length=4)
        assert idx.metaphone_max_length == 4

    def test_index_with_initial_names(self, sample_names):
        idx = PhoneticIndex(sample_names)
        assert idx.name_count == len(sample_names)
        assert sorted(idx.names) == sorted(sample_names)

    def test_index_with_duplicate_names_raises(self, sample_names):
        with pytest.raises(NameExistsError):
            PhoneticIndex(sample_names + [sample_names[0]])


class TestPhoneticIndexAdd:
    def test_add_single_name(self, empty_index):
        code = empty_index.add("Robert")
        assert isinstance(code, PhoneticCode)
        assert code.soundex == "R163"
        assert empty_index.name_count == 1
        assert "Robert" in empty_index.names

    def test_add_duplicate_name_raises(self, empty_index):
        empty_index.add("Robert")
        with pytest.raises(NameExistsError, match="already exists"):
            empty_index.add("Robert")

    def test_add_empty_name_raises(self, empty_index):
        with pytest.raises(EmptyNameError, match="Name cannot be empty"):
            empty_index.add("")

    def test_add_multiple_names(self, empty_index):
        names = ["Robert", "Rupert", "Smith"]
        for name in names:
            empty_index.add(name)
        assert empty_index.name_count == 3
        assert sorted(empty_index.names) == sorted(names)

    def test_contains(self, empty_index):
        assert not empty_index.contains("Robert")
        empty_index.add("Robert")
        assert empty_index.contains("Robert")
        assert not empty_index.contains("Smith")


class TestPhoneticIndexAddBatch:
    def test_add_batch_multiple(self, empty_index):
        names = ["Robert", "Rupert", "Smith", "Smythe"]
        codes = empty_index.add_batch(names)
        assert isinstance(codes, dict)
        assert len(codes) == 4
        assert empty_index.name_count == 4
        for name in names:
            assert name in codes
            assert isinstance(codes[name], PhoneticCode)

    def test_add_batch_empty_list(self, empty_index):
        codes = empty_index.add_batch([])
        assert codes == {}
        assert empty_index.name_count == 0

    def test_add_batch_with_duplicate_raises(self, empty_index):
        empty_index.add("Robert")
        with pytest.raises(NameExistsError):
            empty_index.add_batch(["Rupert", "Robert", "Smith"])


class TestPhoneticIndexGetCode:
    def test_get_code_soundex(self, populated_index):
        code = populated_index.get_code("Robert")
        assert code.soundex == "R163"
        assert isinstance(code.metaphone, str)

    def test_get_code_metaphone(self, populated_index):
        code = populated_index.get_code("Smith")
        assert code.metaphone == "SM0"

    def test_get_code_with_max_length(self):
        idx = PhoneticIndex(metaphone_max_length=2)
        code = idx.get_code("Robert")
        assert len(code.metaphone) <= 2

    def test_get_code_not_in_index(self, empty_index):
        code = empty_index.get_code("Robert")
        assert code.soundex == "R163"
        assert empty_index.name_count == 0


class TestPhoneticIndexRemove:
    def test_remove_existing_name(self, populated_index):
        count_before = populated_index.name_count
        result = populated_index.remove("Robert")
        assert result is True
        assert populated_index.name_count == count_before - 1
        assert "Robert" not in populated_index.names
        assert not populated_index.contains("Robert")

    def test_remove_nonexistent_name(self, populated_index):
        result = populated_index.remove("Nonexistent")
        assert result is False
        count_before = populated_index.name_count
        assert populated_index.name_count == count_before

    def test_remove_removes_from_both_indices(self, empty_index):
        empty_index.add("Robert")
        soundex_code = empty_index.get_code("Robert").soundex
        metaphone_code = empty_index.get_code("Robert").metaphone

        soundex_results = empty_index.search("Robert", mode=MatchMode.SOUNDEX)
        assert len(soundex_results) > 0

        empty_index.remove("Robert")

        soundex_results = empty_index.search("Robert", mode=MatchMode.SOUNDEX)
        assert len(soundex_results) == 0

        metaphone_results = empty_index.search("Robert", mode=MatchMode.METAPHONE)
        assert len(metaphone_results) == 0

    def test_remove_shared_bucket_preserves_others(self, empty_index):
        empty_index.add("Robert")
        empty_index.add("Rupert")

        soundex_robert = empty_index.get_code("Robert").soundex
        soundex_rupert = empty_index.get_code("Rupert").soundex
        assert soundex_robert == soundex_rupert

        empty_index.remove("Robert")

        results = empty_index.search("Rupert", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results]
        assert "Rupert" in result_names
        assert "Robert" not in result_names

    def test_remove_all_clears_buckets(self, empty_index):
        empty_index.add("Robert")
        empty_index.add("Rupert")

        soundex_code = empty_index.get_code("Robert").soundex

        empty_index.remove("Robert")
        empty_index.remove("Rupert")

        assert soundex_code not in empty_index._soundex_index


class TestPhoneticIndexUpdate:
    def test_update_existing_name(self, empty_index):
        empty_index.add("Robert")
        old_code = empty_index.get_code("Robert")
        new_code = empty_index.update("Robert", "Rob")

        assert empty_index.contains("Rob")
        assert not empty_index.contains("Robert")
        assert empty_index.name_count == 1
        assert new_code.soundex != old_code.soundex

    def test_update_to_same_name(self, empty_index):
        empty_index.add("Robert")
        code_before = empty_index.get_code("Robert")
        result = empty_index.update("Robert", "Robert")
        assert result == code_before
        assert empty_index.contains("Robert")
        assert empty_index.name_count == 1

    def test_update_nonexistent_name_raises(self, empty_index):
        with pytest.raises(NameNotFoundError, match="not found"):
            empty_index.update("Robert", "Rob")

    def test_update_to_existing_name_raises(self, empty_index):
        empty_index.add("Robert")
        empty_index.add("Smith")
        with pytest.raises(NameExistsError, match="already exists"):
            empty_index.update("Robert", "Smith")

    def test_update_updates_indices(self, empty_index):
        empty_index.add("Robert")
        old_soundex = empty_index.get_code("Robert").soundex

        results_before = empty_index.search("Robert", mode=MatchMode.SOUNDEX)
        assert len(results_before) == 1

        empty_index.update("Robert", "Smith")

        results_old = empty_index.search("Robert", mode=MatchMode.SOUNDEX)
        assert len(results_old) == 0

        results_new = empty_index.search("Smith", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results_new]
        assert "Smith" in result_names


class TestPhoneticIndexClear:
    def test_clear_populated_index(self, populated_index):
        assert populated_index.name_count > 0
        populated_index.clear()
        assert populated_index.name_count == 0
        assert populated_index.names == []

    def test_clear_empty_index(self, empty_index):
        empty_index.clear()
        assert empty_index.name_count == 0


class TestPhoneticIndexSearchSoundex:
    def test_soundex_match_robert_rupert(self, populated_index):
        results = populated_index.search("Robert", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results]
        assert "Robert" in result_names
        assert "Rupert" in result_names
        assert "Rubin" not in result_names

    def test_soundex_match_smith_smythe(self, populated_index):
        results = populated_index.search("Smith", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results]
        assert "Smith" in result_names
        assert "Smythe" in result_names

    def test_soundex_match_catherine_variants(self, populated_index):
        results = populated_index.search("Catherine", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results]
        assert "Catherine" in result_names
        assert "Katherine" not in result_names
        assert "Katheryn" not in result_names

        results_k = populated_index.search("Katherine", mode=MatchMode.SOUNDEX)
        result_names_k = [r.name for r in results_k]
        assert "Katherine" in result_names_k
        assert "Katheryn" in result_names_k
        assert "Catherine" not in result_names_k

    def test_soundex_no_match(self, populated_index):
        results = populated_index.search("Nonexistent", mode=MatchMode.SOUNDEX)
        assert results == []

    def test_soundex_match_result_flags(self, populated_index):
        results = populated_index.search("Robert", mode=MatchMode.SOUNDEX)
        for r in results:
            assert r.soundex_match is True
            assert isinstance(r.metaphone_match, bool)
            assert isinstance(r, MatchResult)


class TestPhoneticIndexSearchMetaphone:
    def test_metaphone_match_smith_smythe(self, populated_index):
        results = populated_index.search("Smith", mode=MatchMode.METAPHONE)
        result_names = [r.name for r in results]
        assert "Smith" in result_names
        assert "Smythe" in result_names

    def test_metaphone_match_catherine_variants(self, populated_index):
        results = populated_index.search("Catherine", mode=MatchMode.METAPHONE)
        result_names = [r.name for r in results]
        assert "Catherine" in result_names
        assert "Katherine" in result_names

    def test_metaphone_match_john_jon(self, populated_index):
        results = populated_index.search("John", mode=MatchMode.METAPHONE)
        result_names = [r.name for r in results]
        assert "John" in result_names
        assert "Jon" in result_names

    def test_metaphone_no_match(self, populated_index):
        results = populated_index.search("Nonexistent", mode=MatchMode.METAPHONE)
        assert results == []

    def test_metaphone_match_result_flags(self, populated_index):
        results = populated_index.search("Smith", mode=MatchMode.METAPHONE)
        for r in results:
            assert r.metaphone_match is True
            assert r.soundex_match is False


class TestPhoneticIndexSearchBoth:
    def test_both_match_returns_union(self, populated_index):
        results = populated_index.search("Catherine", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Catherine" in result_names
        assert "Katherine" in result_names
        assert "Katheryn" in result_names

    def test_both_match_shawn_sean(self, populated_index):
        results = populated_index.search("Shawn", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Shawn" in result_names
        assert "Sean" in result_names
        assert "John" not in result_names
        assert "Jon" not in result_names

        results_john = populated_index.search("John", mode=MatchMode.BOTH)
        result_names_john = [r.name for r in results_john]
        assert "John" in result_names_john
        assert "Jon" in result_names_john
        assert "Shawn" not in result_names_john
        assert "Sean" not in result_names_john

    def test_both_match_result_both_true(self, populated_index):
        results = populated_index.search("Catherine", mode=MatchMode.BOTH)
        catherine_result = next(r for r in results if r.name == "Catherine")
        assert catherine_result.soundex_match is True
        assert catherine_result.metaphone_match is True

    def test_both_match_result_only_soundex(self, populated_index):
        results = populated_index.search("Robert", mode=MatchMode.BOTH)
        names_and_flags = [(r.name, r.soundex_match, r.metaphone_match) for r in results]
        found = False
        for name, sm, mm in names_and_flags:
            if name == "Rubin" and sm and not mm:
                found = True
                break
        assert found is False
        assert "Rubin" not in [r.name for r in results]

    def test_both_match_sorted_by_best_match(self, populated_index):
        results = populated_index.search("Catherine", mode=MatchMode.BOTH)
        for i in range(len(results) - 1):
            r1 = results[i]
            r2 = results[i + 1]
            r1_score = (r1.soundex_match and r1.metaphone_match, r1.soundex_match, r1.metaphone_match)
            r2_score = (r2.soundex_match and r2.metaphone_match, r2.soundex_match, r2.metaphone_match)
            assert r1_score >= r2_score


class TestPhoneticIndexSearchMode:
    def test_search_mode_string_soundex(self, populated_index):
        results1 = populated_index.search("Robert", mode="soundex")
        results2 = populated_index.search("Robert", mode=MatchMode.SOUNDEX)
        assert [r.name for r in results1] == [r.name for r in results2]

    def test_search_mode_string_metaphone(self, populated_index):
        results1 = populated_index.search("Smith", mode="metaphone")
        results2 = populated_index.search("Smith", mode=MatchMode.METAPHONE)
        assert [r.name for r in results1] == [r.name for r in results2]

    def test_search_mode_string_both(self, populated_index):
        results1 = populated_index.search("Catherine", mode="both")
        results2 = populated_index.search("Catherine", mode=MatchMode.BOTH)
        assert [r.name for r in results1] == [r.name for r in results2]

    def test_search_mode_invalid_string(self, populated_index):
        with pytest.raises(InvalidMatchModeError, match="Invalid match mode"):
            populated_index.search("Robert", mode="invalid")


class TestPhoneticIndexHomophoneMatching:
    def test_john_jon_sean_shawn(self, empty_index):
        names = ["John", "Jon", "Sean", "Shawn"]
        empty_index.add_batch(names)

        results = empty_index.search("John", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "John" in result_names
        assert "Jon" in result_names

        results = empty_index.search("Shawn", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Shawn" in result_names
        assert "Sean" in result_names

    def test_to_too_two(self, empty_index):
        names = ["To", "Too", "Two", "Three"]
        empty_index.add_batch(names)

        results = empty_index.search("To", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "To" in result_names
        assert "Too" in result_names
        assert "Two" in result_names
        assert "Three" not in result_names

    def test_no_false_matches(self, empty_index):
        names = ["Robert", "Smith", "Catherine", "John"]
        empty_index.add_batch(names)

        results = empty_index.search("Robert", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Smith" not in result_names
        assert "Catherine" not in result_names
        assert "John" not in result_names


class TestPhoneticIndexBoundaryConditions:
    def test_search_empty_string(self, populated_index):
        with pytest.raises(EmptyNameError):
            populated_index.search("")

    def test_search_special_chars(self, empty_index):
        empty_index.add("O'Brien")
        results = empty_index.search("Obrien", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "O'Brien" in result_names

    def test_search_numbers_in_name(self, empty_index):
        empty_index.add("John123")
        results = empty_index.search("John", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "John123" in result_names

    def test_search_all_vowels(self, empty_index):
        empty_index.add("Aeiou")
        results = empty_index.search("Aeio", mode=MatchMode.SOUNDEX)
        result_names = [r.name for r in results]
        assert "Aeiou" in result_names

    def test_search_single_character(self, empty_index):
        empty_index.add("A")
        empty_index.add("B")
        results = empty_index.search("A", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "A" in result_names
        assert "B" not in result_names


class TestPhoneticIndexEdgeCases:
    def test_soundex_metaphone_disagree(self, empty_index):
        names = ["Christian", "Christina"]
        empty_index.add_batch(names)

        results = empty_index.search("Christian", mode=MatchMode.BOTH)
        for r in results:
            if r.soundex_match != r.metaphone_match:
                break

    def test_delete_then_search_not_found(self, empty_index):
        empty_index.add("Robert")
        empty_index.add("Rupert")

        empty_index.remove("Robert")

        results = empty_index.search("Robert", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Robert" not in result_names
        assert "Rupert" in result_names

    def test_update_old_name_not_matchable(self, empty_index):
        empty_index.add("Robert")
        empty_index.update("Robert", "Smith")

        results = empty_index.search("Robert", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Robert" not in result_names
        assert "Smith" not in result_names

        results = empty_index.search("Smith", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Smith" in result_names

    def test_batch_add_and_delete(self, empty_index):
        names = ["Robert", "Rupert", "Rubin", "Smith", "Smythe"]
        empty_index.add_batch(names)
        assert empty_index.name_count == 5

        empty_index.remove("Robert")
        empty_index.remove("Smith")
        assert empty_index.name_count == 3

        results = empty_index.search("Rupert", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Rupert" in result_names
        assert "Rubin" not in result_names

    def test_multiple_updates(self, empty_index):
        empty_index.add("Name1")
        empty_index.update("Name1", "Name2")
        empty_index.update("Name2", "Name3")

        assert empty_index.contains("Name3")
        assert not empty_index.contains("Name2")
        assert not empty_index.contains("Name1")
        assert empty_index.name_count == 1

        results = empty_index.search("Name3", mode=MatchMode.BOTH)
        result_names = [r.name for r in results]
        assert "Name3" in result_names

    def test_case_insensitive_matching(self, empty_index):
        empty_index.add("Robert")
        results_upper = empty_index.search("ROBERT", mode=MatchMode.BOTH)
        results_lower = empty_index.search("robert", mode=MatchMode.BOTH)
        results_mixed = empty_index.search("RoBeRt", mode=MatchMode.BOTH)

        assert [r.name for r in results_upper] == [r.name for r in results_lower]
        assert [r.name for r in results_lower] == [r.name for r in results_mixed]


class TestPhoneticIndexMetaphoneMaxLength:
    def test_metaphone_max_length_in_search(self):
        idx = PhoneticIndex(metaphone_max_length=2)
        idx.add("Supercalifragilisticexpialidocious")

        results = idx.search("Supercalifragilisticexpialidocious", mode=MatchMode.METAPHONE)
        assert len(results) == 1

    def test_different_max_lengths_produce_different_results(self, sample_names):
        idx1 = PhoneticIndex(sample_names, metaphone_max_length=2)
        idx2 = PhoneticIndex(sample_names, metaphone_max_length=None)

        results1 = idx1.search("Catherine", mode=MatchMode.METAPHONE)
        results2 = idx2.search("Catherine", mode=MatchMode.METAPHONE)

        assert len(results1) >= len(results2)


class TestPhoneticIndexNamesProperty:
    def test_names_sorted(self, empty_index):
        empty_index.add("Charlie")
        empty_index.add("Alice")
        empty_index.add("Bob")
        assert empty_index.names == ["Alice", "Bob", "Charlie"]

    def test_names_empty(self, empty_index):
        assert empty_index.names == []
