import pytest

from solocoder_py.phonetic import EmptyNameError, soundex


class TestSoundexBasicEncoding:
    def test_robert(self):
        assert soundex("Robert") == "R163"

    def test_rupert(self):
        assert soundex("Rupert") == "R163"

    def test_rubin(self):
        assert soundex("Rubin") == "R150"

    def test_smith(self):
        assert soundex("Smith") == "S530"

    def test_smythe(self):
        assert soundex("Smythe") == "S530"

    def test_ashcroft(self):
        assert soundex("Ashcraft") == "A261"

    def test_ashcroft_variant(self):
        assert soundex("Ashcroft") == "A261"

    def test_tymczak(self):
        assert soundex("Tymczak") == "T522"

    def test_pfister(self):
        assert soundex("Pfister") == "P236"

    def test_jackson(self):
        assert soundex("Jackson") == "J250"


class TestSoundexCaseInsensitivity:
    def test_lowercase(self):
        assert soundex("robert") == "R163"

    def test_uppercase(self):
        assert soundex("ROBERT") == "R163"

    def test_mixed_case(self):
        assert soundex("RoBeRt") == "R163"

    def test_all_caps_smith(self):
        assert soundex("SMITH") == "S530"


class TestSoundexSingleCharacter:
    def test_single_a(self):
        assert soundex("A") == "A000"

    def test_single_b(self):
        assert soundex("B") == "B000"

    def test_single_z(self):
        assert soundex("Z") == "Z000"

    def test_single_consonant_s(self):
        assert soundex("S") == "S000"


class TestSoundexBoundaryConditions:
    def test_empty_string_raises(self):
        with pytest.raises(EmptyNameError, match="Name cannot be empty"):
            soundex("")

    def test_all_non_alphabetic(self):
        assert soundex("12345") == "0000"

    def test_all_special_chars(self):
        assert soundex("!@#$%^") == "0000"

    def test_name_with_spaces(self):
        assert soundex("Robert Smith") == "R163"

    def test_name_with_hyphens(self):
        assert soundex("Smith-Jones") == "S532"

    def test_name_with_numbers(self):
        assert soundex("John123") == "J500"

    def test_name_with_special_chars(self):
        assert soundex("O'Brien") == "O165"

    def test_all_vowels(self):
        assert soundex("AEIOU") == "A000"

    def test_all_vowels_with_y(self):
        assert soundex("AEIOUY") == "A000"

    def test_very_long_name(self):
        long_name = "Supercalifragilisticexpialidocious"
        result = soundex(long_name)
        assert len(result) == 4
        assert result[0] == "S"
        assert result[1:].isdigit()


class TestSoundexDuplicateConsonants:
    def test_adjacent_duplicates_merged(self):
        assert soundex("Bell") == "B400"

    def test_adjacent_same_group(self):
        assert soundex("BFPV") == "B000"

    def test_vowel_separated_duplicates(self):
        assert soundex("Bob") == "B100"

    def test_h_w_separated_duplicates_dropped(self):
        assert soundex("Bhwl") == "B400"

    def test_repeated_letters(self):
        assert soundex("Lll") == "L000"


class TestSoundexVowelHandling:
    def test_vowels_removed(self):
        assert soundex("BAEIOU") == "B000"

    def test_vowels_separate_same_group(self):
        result1 = soundex("Tt")
        result2 = soundex("TaT")
        assert result1 != result2
        assert result1 == "T000"
        assert result2 == "T300"

    def test_initial_vowel_preserved(self):
        result = soundex("Euler")
        assert result[0] == "E"


class TestSoundexConventionalNames:
    def test_williams(self):
        assert soundex("Williams") == "W452"

    def test_brown(self):
        assert soundex("Brown") == "B650"

    def test_jones(self):
        assert soundex("Jones") == "J520"

    def test_miller(self):
        assert soundex("Miller") == "M460"

    def test_davis(self):
        assert soundex("Davis") == "D120"

    def test_garcia(self):
        assert soundex("Garcia") == "G620"

    def test_rodriguez(self):
        assert soundex("Rodriguez") == "R362"

    def test_wilson(self):
        assert soundex("Wilson") == "W425"

    def test_martinez(self):
        assert soundex("Martinez") == "M635"

    def test_anderson(self):
        assert soundex("Anderson") == "A536"


class TestSoundexConsonantGroups:
    def test_group1_bfpv(self):
        assert soundex("B") == "B000"
        assert soundex("F") == "F000"
        assert soundex("P") == "P000"
        assert soundex("V") == "V000"
        assert soundex("BF") == "B000"
        assert soundex("FPV") == "F000"

    def test_group2_cgjkqsxz(self):
        assert soundex("C") == "C000"
        assert soundex("G") == "G000"
        assert soundex("CG") == "C000"

    def test_group3_dt(self):
        assert soundex("D") == "D000"
        assert soundex("T") == "T000"
        assert soundex("DT") == "D000"

    def test_group4_l(self):
        assert soundex("L") == "L000"
        assert soundex("LL") == "L000"

    def test_group5_mn(self):
        assert soundex("M") == "M000"
        assert soundex("N") == "N000"
        assert soundex("MN") == "M000"

    def test_group6_r(self):
        assert soundex("R") == "R000"
        assert soundex("RR") == "R000"


class TestSoundexPadding:
    def test_short_name_padded(self):
        result = soundex("Lee")
        assert len(result) == 4
        assert result.endswith("00")

    def test_single_char_padded(self):
        result = soundex("A")
        assert len(result) == 4
        assert result[1:] == "000"

    def test_two_chars_padded(self):
        result = soundex("Al")
        assert len(result) == 4
        assert result.endswith("0")


class TestSoundexHWSeparator:
    def test_h_separates_duplicate_codes(self):
        assert soundex("Ashcraft") == soundex("Ashcroft")

    def test_w_separates_duplicate_codes(self):
        assert soundex("Bwl") == "B400"

    def test_yt_and_gne_ending(self):
        pass
