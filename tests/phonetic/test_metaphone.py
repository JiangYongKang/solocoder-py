import pytest

from solocoder_py.phonetic import EmptyNameError, metaphone


class TestMetaphoneBasicEncoding:
    def test_smith(self):
        assert metaphone("Smith") == "SM0"

    def test_smythe(self):
        assert metaphone("Smythe") == "SM0"

    def test_schmidt(self):
        assert metaphone("Schmidt") == "XMT"

    def test_robert(self):
        assert metaphone("Robert") == "RBRT"

    def test_rupert(self):
        assert metaphone("Rupert") == "RPRT"

    def test_catherine(self):
        assert metaphone("Catherine") == "K0RN"

    def test_katherine(self):
        assert metaphone("Katherine") == "K0RN"

    def test_john(self):
        assert metaphone("John") == "JN"

    def test_jon(self):
        assert metaphone("Jon") == "JN"

    def test_sean(self):
        assert metaphone("Sean") == "SN"

    def test_shawn(self):
        assert metaphone("Shawn") == "XN"


class TestMetaphoneSpecialCases:
    def test_ph_maps_to_f(self):
        assert metaphone("Phone") == "FN"
        assert metaphone("Stephen") == "STFN"

    def test_gn_kn_pn_wr_prefix(self):
        assert metaphone("Knight") == "NT"
        assert metaphone("Gnome") == "NM"
        assert metaphone("Pneumonia") == "NMN"
        assert metaphone("Write") == "RT"

    def test_wh_prefix(self):
        assert metaphone("Whale") == "WL"
        assert metaphone("What") == "WT"

    def test_x_prefix(self):
        assert metaphone("Xavier") == "SFR"

    def test_cia_sia_tia_patterns(self):
        assert metaphone("Special") == "SPXL"
        assert metaphone("Patient") == "PXNT"

    def test_th_sounds(self):
        assert metaphone("Think") == "0NK"
        assert metaphone("This") == "0S"
        assert metaphone("The") == "0"

    def test_dge_dgi_dgy(self):
        assert metaphone("Judge") == "JJ"
        assert metaphone("Edge") == "EJ"

    def test_gned_ending(self):
        assert metaphone("Signed") == "SNT"
        assert metaphone("Design") == "TSN"

    def test_mb_ending(self):
        assert metaphone("Bomb") == "BM"
        assert metaphone("Limb") == "LM"

    def test_sch_pattern(self):
        assert metaphone("School") == "SKL"
        assert metaphone("Scheme") == "XM"


class TestMetaphoneCaseInsensitivity:
    def test_lowercase(self):
        assert metaphone("robert") == "RBRT"

    def test_uppercase(self):
        assert metaphone("ROBERT") == "RBRT"

    def test_mixed_case(self):
        assert metaphone("RoBeRt") == "RBRT"


class TestMetaphoneBoundaryConditions:
    def test_empty_string_raises(self):
        with pytest.raises(EmptyNameError, match="Name cannot be empty"):
            metaphone("")

    def test_all_non_alphabetic(self):
        assert metaphone("12345") == ""

    def test_all_special_chars(self):
        assert metaphone("!@#$%^") == ""

    def test_name_with_spaces(self):
        assert metaphone("Robert Smith") == "RBRTSM0"

    def test_name_with_hyphens(self):
        assert metaphone("Smith-Jones") == "SM0JNS"

    def test_name_with_numbers(self):
        assert metaphone("John123") == "JN"

    def test_name_with_special_chars(self):
        assert metaphone("O'Brien") == "OBRN"

    def test_single_vowel(self):
        assert metaphone("A") == "A"
        assert metaphone("E") == "E"

    def test_single_consonant(self):
        assert metaphone("B") == "B"
        assert metaphone("S") == "S"

    def test_all_vowels(self):
        assert metaphone("AEIOU") == "A"

    def test_very_long_name(self):
        long_name = "Supercalifragilisticexpialidocious"
        result = metaphone(long_name)
        assert len(result) > 0
        assert all(c in "0ABCDEFHJKLMNPRSTWXY" for c in result)

    def test_vowels_after_initial_dropped(self):
        assert metaphone("BAEIOU") == "B"


class TestMetaphoneMaxLength:
    def test_max_length_truncates(self):
        result = metaphone("Supercalifragilisticexpialidocious", max_length=5)
        assert len(result) == 5

    def test_max_length_1(self):
        result = metaphone("Robert", max_length=1)
        assert len(result) == 1
        assert result == "R"

    def test_max_length_0(self):
        result = metaphone("Robert", max_length=0)
        assert result == ""

    def test_max_length_none_no_truncation(self):
        result = metaphone("Supercalifragilisticexpialidocious", max_length=None)
        assert len(result) > 5

    def test_max_length_greater_than_output(self):
        result = metaphone("John", max_length=10)
        assert result == "JN"


class TestMetaphoneDuplicateLetters:
    def test_adjacent_duplicates_dropped(self):
        assert metaphone("Bell") == "BL"
        assert metaphone("Lll") == "L"

    def test_c_duplicates_not_dropped(self):
        assert metaphone("Access") == "AKSS"


class TestMetaphoneConventionalNames:
    def test_williams(self):
        assert metaphone("Williams") == "WLMS"

    def test_brown(self):
        assert metaphone("Brown") == "BRN"

    def test_jones(self):
        assert metaphone("Jones") == "JNS"

    def test_miller(self):
        assert metaphone("Miller") == "MLR"

    def test_davis(self):
        assert metaphone("Davis") == "TFS"

    def test_garcia(self):
        assert metaphone("Garcia") == "KRX"

    def test_rodriguez(self):
        assert metaphone("Rodriguez") == "RTRKS"

    def test_wilson(self):
        assert metaphone("Wilson") == "WLSN"

    def test_martinez(self):
        assert metaphone("Martinez") == "MRTNS"

    def test_anderson(self):
        assert metaphone("Anderson") == "ANTRSN"


class TestMetaphoneHomophones:
    def test_to_too_two(self):
        assert metaphone("To") == metaphone("Too") == metaphone("Two") == "T"

    def test_there_their(self):
        assert metaphone("There") == metaphone("Their") == "0R"

    def test_here_hear(self):
        assert metaphone("Here") == metaphone("Hear") == "HR"

    def test_right_write(self):
        assert metaphone("Right") == metaphone("Write") == "RT"

    def test_knew_new(self):
        assert metaphone("Knew") == metaphone("New") == "N"


class TestMetaphoneVowelHandling:
    def test_initial_vowel_preserved(self):
        assert metaphone("Apple") == "APL"
        assert metaphone("Eagle") == "EKL"
        assert metaphone("Idea") == "IT"
        assert metaphone("Orange") == "ORNJ"
        assert metaphone("Umbrella") == "UMBRL"

    def test_middle_vowels_dropped(self):
        assert metaphone("Banana") == "BNN"
        assert metaphone("Computer") == "KMPTR"


class TestMetaphoneLetterC:
    def test_soft_c(self):
        assert metaphone("Cent") == "SNT"
        assert metaphone("City") == "ST"
        assert metaphone("Cycle") == "SKL"

    def test_hard_c(self):
        assert metaphone("Cat") == "KT"
        assert metaphone("Corn") == "KRN"
        assert metaphone("Cut") == "KT"

    def test_ch_sounds(self):
        assert metaphone("Church") == "XRX"
        assert metaphone("Character") == "XRKTR"
        assert metaphone("Chaos") == "XS"


class TestMetaphoneCKCombination:
    def test_ck_jackson(self):
        assert metaphone("Jackson") == "JKSN"

    def test_ck_back(self):
        assert metaphone("Back") == "BK"

    def test_ck_mack(self):
        assert metaphone("Mack") == "MK"

    def test_ck_jack(self):
        assert metaphone("Jack") == "JK"

    def test_ck_sack(self):
        assert metaphone("Sack") == "SK"

    def test_ck_pack(self):
        assert metaphone("Pack") == "PK"

    def test_ck_rack(self):
        assert metaphone("Rack") == "RK"

    def test_ck_check(self):
        assert metaphone("Check") == "XK"

    def test_ck_truck(self):
        assert metaphone("Truck") == "TRK"

    def test_ck_in_middle(self):
        assert metaphone("Lucky") == "LK"
        assert metaphone("Bucket") == "BKT"


class TestMetaphoneLetterG:
    def test_soft_g(self):
        assert metaphone("Gent") == "JNT"
        assert metaphone("Giant") == "JNT"
        assert metaphone("Gym") == "JM"

    def test_hard_g(self):
        assert metaphone("Goat") == "KT"
        assert metaphone("Good") == "KT"
        assert metaphone("Gut") == "KT"

    def test_gh_patterns(self):
        assert metaphone("Ghost") == "KST"
        assert metaphone("Night") == "NT"
        assert metaphone("Through") == "0R"


class TestMetaphoneLetterS:
    def test_sh_sound(self):
        assert metaphone("Ship") == "XP"
        assert metaphone("Shore") == "XR"

    def test_sio_sia_patterns(self):
        assert metaphone("Vision") == "FXN"
        assert metaphone("Asia") == "AX"


class TestMetaphoneLetterT:
    def test_tio_tia_patterns(self):
        assert metaphone("Nation") == "NXN"
        assert metaphone("Ratio") == "RX"

    def test_tch_pattern(self):
        assert metaphone("Watch") == "WX"
        assert metaphone("Match") == "MX"
