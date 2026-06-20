from __future__ import annotations

import pytest

from solocoder_py.config_parser import (
    Config,
    DuplicateKeyError,
    InvalidDateTimeError,
    InvalidNumberError,
    InvalidTableNameError,
    InvalidValueTypeError,
    KeyNotFoundError,
    ParseError,
    TypeConversionError,
    UnclosedStringError,
    parse_toml,
)


class TestSyntaxErrors:
    def test_invalid_line(self):
        with pytest.raises(ParseError):
            parse_toml("this is not valid toml")

    def test_missing_equals(self):
        with pytest.raises(ParseError):
            parse_toml("key value")

    def test_empty_key(self):
        with pytest.raises(ParseError):
            parse_toml(' = "value"')

    def test_unclosed_bracket_table(self):
        with pytest.raises(ParseError):
            parse_toml("[section\nkey = 1")

    def test_unclosed_double_bracket_array_table(self):
        with pytest.raises(ParseError):
            parse_toml("[[section\nkey = 1")

    def test_invalid_value(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("key = 0xZZ")

    def test_toml_strict_rejects_bare_string(self):
        with pytest.raises(InvalidValueTypeError):
            parse_toml("key = bare_string")

    def test_toml_strict_rejects_unquoted_value_with_special_chars(self):
        with pytest.raises(InvalidValueTypeError):
            parse_toml("key = hello world")


class TestDuplicateKeyAndTable:
    def test_duplicate_key_in_root(self):
        with pytest.raises(DuplicateKeyError) as exc:
            parse_toml('a = 1\na = 2')
        assert exc.value.key == "a"
        assert exc.value.line == 2

    def test_duplicate_key_in_table(self):
        with pytest.raises(DuplicateKeyError):
            parse_toml('[s]\nk = 1\nk = 2')

    def test_key_already_defined_as_table(self):
        with pytest.raises(DuplicateKeyError):
            parse_toml('a = {}\na = 2')

    def test_duplicate_inline_table_key(self):
        with pytest.raises(DuplicateKeyError):
            parse_toml('t = { a = 1, a = 2 }')


class TestInvalidTableNames:
    def test_empty_table_name(self):
        with pytest.raises(InvalidTableNameError):
            parse_toml("[]\nk = 1")

    def test_empty_array_table_name(self):
        with pytest.raises(InvalidTableNameError):
            parse_toml("[[]]\nk = 1")

    def test_empty_segment_in_table_name(self):
        with pytest.raises(InvalidTableNameError):
            parse_toml("[a..b]\nk = 1")

    def test_table_name_with_special_chars(self):
        with pytest.raises(InvalidTableNameError):
            parse_toml("[bad name]\nk = 1")


class TestUnclosedStrings:
    def test_unclosed_basic_string(self):
        with pytest.raises(UnclosedStringError):
            parse_toml('s = "unterminated')

    def test_unclosed_literal_string(self):
        with pytest.raises(UnclosedStringError):
            parse_toml("s = 'unterminated")

    def test_unclosed_multiline_string(self):
        text = '''s = """
line1
line2
'''
        with pytest.raises(UnclosedStringError):
            parse_toml(text)

    def test_invalid_escape_sequence(self):
        with pytest.raises(ParseError):
            parse_toml(r's = "hello\xworld"')


class TestInvalidNumbers:
    def test_invalid_hex_number(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("n = 0xGGG")

    def test_invalid_octal_number(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("n = 0o888")

    def test_invalid_binary_number(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("n = 0b222")

    def test_malformed_float(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("n = 1.2.3")

    def test_just_sign_as_number(self):
        with pytest.raises(InvalidNumberError):
            parse_toml("n = -123abc")


class TestInvalidDateTime:
    def test_invalid_month(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("d = 2023-13-01")

    def test_invalid_day(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("d = 2023-01-32")

    def test_invalid_hour(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("t = 25:00:00")

    def test_invalid_minute(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("t = 00:60:00")

    def test_invalid_second(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("t = 00:00:60")

    def test_invalid_datetime_format(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("dt = 2023-01-01-00:00:00")

    def test_non_leap_year_feb_29(self):
        with pytest.raises(InvalidDateTimeError):
            parse_toml("d = 2023-02-29")


class TestTypeConversionErrors:
    def test_get_bool_invalid_string(self):
        config = Config()
        config.root["flag"] = "not_a_bool"
        with pytest.raises(TypeConversionError) as exc:
            config.get_bool("flag")
        assert exc.value.target_type == "bool"
        assert exc.value.key == "flag"

    def test_get_bool_from_invalid_number(self):
        config = Config()
        config.root["flag"] = 2
        with pytest.raises(TypeConversionError):
            config.get_bool("flag")

    def test_get_int_from_invalid_string(self):
        config = Config()
        config.root["n"] = "not_a_number"
        with pytest.raises(TypeConversionError) as exc:
            config.get_int("n")
        assert exc.value.target_type == "int"

    def test_get_int_from_non_integer_float(self):
        config = Config()
        config.root["n"] = 3.14
        with pytest.raises(TypeConversionError):
            config.get_int("n")

    def test_get_float_from_invalid_string(self):
        config = Config()
        config.root["f"] = "not_a_float"
        with pytest.raises(TypeConversionError):
            config.get_float("f")

    def test_get_array_non_array_value(self):
        config = parse_toml("s = 'hello'")
        with pytest.raises(TypeConversionError) as exc:
            config.get_array("s")
        assert exc.value.target_type == "array"

    def test_get_array_invalid_element_type(self):
        config = parse_toml("arr = [1, 2, 3]")
        with pytest.raises(TypeConversionError):
            config.get_array("arr", element_type="invalid_type")

    def test_get_array_element_type_mismatch(self):
        config = parse_toml('arr = [1, "not_int", 3]')
        with pytest.raises(TypeConversionError):
            config.get_array("arr", element_type="int")

    def test_get_table_non_table_value(self):
        config = parse_toml("s = 'hello'")
        with pytest.raises(TypeConversionError) as exc:
            config.get_table("s")
        assert exc.value.target_type == "table"

    def test_get_array_table_from_regular_table(self):
        text = '''
[items]
a = 1
'''
        config = parse_toml(text)
        with pytest.raises(TypeConversionError):
            config.get_array_table("items")


class TestKeyNotFound:
    def test_get_missing_key(self):
        config = parse_toml('existing = "yes"')
        with pytest.raises(KeyNotFoundError) as exc:
            config.get_str("missing")
        assert exc.value.key == "missing"

    def test_get_bool_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_bool("nonexistent")

    def test_get_int_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_int("nonexistent")

    def test_get_float_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_float("nonexistent")

    def test_get_str_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_str("nonexistent")

    def test_get_array_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_array("nonexistent")

    def test_get_table_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_table("nonexistent")

    def test_get_array_table_missing_key(self):
        config = Config()
        with pytest.raises(KeyNotFoundError):
            config.get_array_table("nonexistent")

    def test_nested_key_not_found(self):
        config = parse_toml("[a]\nb = 1")
        with pytest.raises(KeyNotFoundError):
            config.get_str("a.c")


class TestExceptionMessages:
    def test_parse_error_includes_line(self):
        try:
            parse_toml("invalid line here")
        except ParseError as e:
            assert "line" in str(e).lower()
            assert str(e.line) in str(e)

    def test_duplicate_key_error_includes_key_name(self):
        try:
            parse_toml("a = 1\na = 2")
        except DuplicateKeyError as e:
            assert "a" in str(e)

    def test_type_conversion_error_includes_key(self):
        config = Config()
        config.root["test_key"] = "bad"
        try:
            config.get_int("test_key")
        except TypeConversionError as e:
            assert "test_key" in str(e)
            assert "int" in str(e)
