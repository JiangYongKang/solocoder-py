from __future__ import annotations

import pytest

from src.solocoder_py.masking import MaskingConfig, MaskingStrategy


class TestMaskingStrategy:
    def test_default_masking_phone(self):
        masker = MaskingStrategy()
        result = masker.mask("13812345678")
        assert result == "138****5678"
        assert len(result) == 11

    def test_custom_masking_config(self):
        config = MaskingConfig(keep_prefix=2, keep_suffix=2, mask_char="#")
        masker = MaskingStrategy(config)
        result = masker.mask("1234567890")
        assert result == "12######90"
        assert len(result) == 10

    def test_mask_phone_method(self):
        masker = MaskingStrategy()
        result = masker.mask_phone("13812345678")
        assert result == "138****5678"

    def test_mask_id_card_method(self):
        masker = MaskingStrategy()
        result = masker.mask_id_card("110101199001011234")
        assert result == "1****************4"
        assert len(result) == 18
        assert result[0] == "1"
        assert result[-1] == "4"

    def test_mask_email_method(self):
        masker = MaskingStrategy()
        result = masker.mask_email("zhangsan@example.com")
        assert "@" in result
        username, domain = result.split("@")
        assert username[0] == "z"
        assert username[-1] == "n"
        assert "*" in username
        assert domain == "example.com"

    def test_short_phone_masking(self):
        masker = MaskingStrategy()
        result = masker.mask_phone("12345")
        assert result == "*****"

    def test_short_id_card_masking(self):
        masker = MaskingStrategy()
        result = masker.mask_id_card("12")
        assert result == "12"
        result2 = masker.mask_id_card("1")
        assert result2 == "*"

    def test_full_mask_when_keep_exceeds_length(self):
        config = MaskingConfig(keep_prefix=5, keep_suffix=5)
        masker = MaskingStrategy(config)
        result = masker.mask("12345")
        assert result == "*****"

    def test_empty_string_masking(self):
        masker = MaskingStrategy()
        result = masker.mask("")
        assert result == ""

    def test_none_value_masking(self):
        masker = MaskingStrategy()
        result = masker.mask(None)
        assert result == ""

    def test_numeric_value_masking(self):
        masker = MaskingStrategy()
        result = masker.mask(13812345678)
        assert result == "138****5678"

    def test_zero_keep_prefix(self):
        config = MaskingConfig(keep_prefix=0, keep_suffix=4)
        masker = MaskingStrategy(config)
        result = masker.mask("13812345678")
        assert result == "*******5678"
        assert not result[0].isdigit()

    def test_zero_keep_suffix(self):
        config = MaskingConfig(keep_prefix=3, keep_suffix=0)
        masker = MaskingStrategy(config)
        result = masker.mask("13812345678")
        assert result == "138********"

    def test_both_zero_keep(self):
        config = MaskingConfig(keep_prefix=0, keep_suffix=0)
        masker = MaskingStrategy(config)
        result = masker.mask("13812345678")
        assert result == "***********"

    def test_custom_mask_character(self):
        config = MaskingConfig(keep_prefix=3, keep_suffix=4, mask_char="x")
        masker = MaskingStrategy(config)
        result = masker.mask("13812345678")
        assert result == "138xxxx5678"

    def test_callable_interface(self):
        masker = MaskingStrategy()
        result = masker("13812345678")
        assert result == "138****5678"

    def test_short_email_masking(self):
        masker = MaskingStrategy()
        result = masker.mask_email("ab@example.com")
        assert result == "**@example.com"

    def test_email_without_at_symbol(self):
        masker = MaskingStrategy()
        result = masker.mask_email("invalidemail")
        assert result == "************"

    def test_empty_email(self):
        masker = MaskingStrategy()
        result = masker.mask_email("")
        assert result == ""

    def test_empty_phone(self):
        masker = MaskingStrategy()
        result = masker.mask_phone("")
        assert result == "***"

    def test_empty_id_card(self):
        masker = MaskingStrategy()
        result = masker.mask_id_card("")
        assert result == "***"

    def test_whitespace_phone(self):
        masker = MaskingStrategy()
        result = masker.mask_phone("  13812345678  ")
        assert result == "138****5678"

    def test_mask_preserves_length(self):
        masker = MaskingStrategy()
        test_cases = ["1", "12", "123", "1234", "12345", "123456", "1234567"]
        for test_case in test_cases:
            result = masker.mask(test_case)
            assert len(result) == len(test_case)

    def test_masking_config_validation(self):
        with pytest.raises(ValueError, match="keep_prefix must be non-negative"):
            MaskingConfig(keep_prefix=-1)

        with pytest.raises(ValueError, match="keep_suffix must be non-negative"):
            MaskingConfig(keep_suffix=-1)

        with pytest.raises(ValueError, match="mask_char must be exactly one character"):
            MaskingConfig(mask_char="**")
