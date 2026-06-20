from __future__ import annotations

from datetime import date, datetime, time

import pytest

from solocoder_py.config_parser import parse_toml


class TestEmptyDocuments:
    def test_empty_string(self):
        config = parse_toml("")
        assert len(config.to_dict()) == 0

    def test_only_whitespace(self):
        config = parse_toml("   \n  \t  \n  ")
        assert len(config.to_dict()) == 0

    def test_only_newlines(self):
        config = parse_toml("\n\n\n")
        assert len(config.to_dict()) == 0


class TestCommentOnlyDocuments:
    def test_only_comments(self):
        text = '''# This is comment 1
# This is comment 2
; Semicolon comment
'''
        config = parse_toml(text)
        assert len(config.to_dict()) == 0

    def test_comments_and_blank_lines(self):
        text = '''# Comment 1

# Comment 2

; Comment 3
'''
        config = parse_toml(text)
        assert len(config.to_dict()) == 0


class TestDeepNestedTables:
    def test_deep_nesting(self):
        text = '''
[a.b.c.d.e.f.g.h.i.j]
deep_key = "found"
'''
        config = parse_toml(text)
        assert config.get("a.b.c.d.e.f.g.h.i.j.deep_key") == "found"

    def test_deep_nested_access(self):
        text = '''
[l1.l2.l3.l4.l5]
value = 42
'''
        config = parse_toml(text)
        levels = ["l1", "l2", "l3", "l4", "l5"]
        current = config
        for level in levels:
            current = current.get_table(level)
        assert current["value"] == 42


class TestEmptyArrays:
    def test_empty_array(self):
        config = parse_toml("arr = []")
        assert config.get_array("arr") == []

    def test_empty_array_of_tables(self):
        text = '''
[[items]]
'''
        config = parse_toml(text)
        items = config.get_array_table("items")
        assert len(items) == 1
        assert len(items[0].to_dict()) == 0

    def test_multiple_empty_array_tables(self):
        text = '''
[[empty]]
[[empty]]
[[empty]]
'''
        config = parse_toml(text)
        assert len(config.get_array_table("empty")) == 3


class TestLargeIntegers:
    def test_large_positive_integer(self):
        config = parse_toml("big = 999999999999999999999")
        assert config["big"] == 999999999999999999999

    def test_large_negative_integer(self):
        config = parse_toml("neg = -999999999999999999999")
        assert config["neg"] == -999999999999999999999

    def test_max_int64_like_value(self):
        config = parse_toml("max = 9223372036854775807")
        assert config["max"] == 9223372036854775807

    def test_large_integer_with_underscores(self):
        config = parse_toml("big = 1_000_000_000_000_000")
        assert config["big"] == 1000000000000000


class TestSpecialStrings:
    def test_empty_string(self):
        config = parse_toml('s = ""')
        assert config["s"] == ""

    def test_string_with_only_spaces(self):
        config = parse_toml('s = "   "')
        assert config["s"] == "   "

    def test_empty_literal_string(self):
        config = parse_toml("s = ''")
        assert config["s"] == ""

    def test_string_with_all_escape_sequences(self):
        config = parse_toml(r's = "a\tb\nc\rd\\e\"f"')
        assert config["s"] == "a\tb\nc\rd\\e\"f"

    def test_multiline_string_empty(self):
        text = 's = """\n"""'
        config = parse_toml(text)
        assert config["s"] == ""


class TestTableEdgeCases:
    def test_table_names_with_underscores_and_dashes(self):
        text = '''
[my-table_name]
key = 1
'''
        config = parse_toml(text)
        assert config["my-table_name"]["key"] == 1

    def test_keys_with_underscores_and_dashes(self):
        config = parse_toml("my-key_name = 42")
        assert config["my-key_name"] == 42

    def test_bare_keys_digits(self):
        config = parse_toml("key123 = 1")
        assert config["key123"] == 1

    def test_numeric_keys_quoted(self):
        config = parse_toml('"123" = 456')
        assert config["123"] == 456


class TestArrayEdgeCases:
    def test_single_element_array(self):
        config = parse_toml("arr = [1]")
        assert config["arr"] == [1]

    def test_array_with_trailing_comma(self):
        config = parse_toml("arr = [1, 2, 3,]")
        assert config["arr"] == [1, 2, 3]

    def test_nested_empty_arrays(self):
        config = parse_toml("arr = [[], [[]]]")
        assert config["arr"] == [[], [[]]]

    def test_array_of_inline_tables(self):
        text = 'points = [{x = 1, y = 2}, {x = 3, y = 4}]'
        config = parse_toml(text)
        assert len(config["points"]) == 2
        assert config["points"][0]["x"] == 1
        assert config["points"][1]["y"] == 4


class TestDateTimeEdgeCases:
    def test_date_end_of_year(self):
        config = parse_toml("d = 2023-12-31")
        assert config["d"] == date(2023, 12, 31)

    def test_date_leap_day(self):
        config = parse_toml("d = 2024-02-29")
        assert config["d"] == date(2024, 2, 29)

    def test_time_midnight(self):
        config = parse_toml("t = 00:00:00")
        assert config["t"] == time(0, 0, 0)

    def test_time_end_of_day(self):
        config = parse_toml("t = 23:59:59")
        assert config["t"] == time(23, 59, 59)

    def test_datetime_midnight(self):
        config = parse_toml("dt = 2023-01-01T00:00:00")
        assert config["dt"] == datetime(2023, 1, 1, 0, 0, 0)

    def test_datetime_with_negative_offset(self):
        from datetime import timezone, timedelta
        config = parse_toml("dt = 2023-01-01T00:00:00-05:00")
        tz = timezone(timedelta(hours=-5))
        assert config["dt"] == datetime(2023, 1, 1, 0, 0, 0, tzinfo=tz)


class TestBooleanEdgeCases:
    def test_lowercase_true_false(self):
        config = parse_toml("a = true\nb = false")
        assert config["a"] is True
        assert config["b"] is False


class TestWhitespaceHandling:
    def test_extra_spaces_around_equals(self):
        config = parse_toml('key   =   "value"')
        assert config["key"] == "value"

    def test_tabs_around_equals(self):
        config = parse_toml("key\t=\t42")
        assert config["key"] == 42

    def test_mixed_whitespace_lines(self):
        text = '''
   [section]   
      key   =   "value"   
'''
        config = parse_toml(text)
        assert config["section"]["key"] == "value"

    def test_trailing_comment_with_space(self):
        config = parse_toml('key = "value"  # this is a comment')
        assert config["key"] == "value"

    def test_trailing_comment_no_space(self):
        config = parse_toml('key = "value"#comment')
        assert config["key"] == "value"


class TestTypeConversionEdgeCases:
    def test_get_bool_from_string_1_0(self):
        from solocoder_py.config_parser import Config
        config = Config()
        config.root["a"] = "1"
        config.root["b"] = "0"
        assert config.get_bool("a") is True
        assert config.get_bool("b") is False

    def test_get_int_from_negative_string(self):
        from solocoder_py.config_parser import Config
        config = Config()
        config.root["n"] = "-100"
        assert config.get_int("n") == -100

    def test_get_float_from_negative_string(self):
        from solocoder_py.config_parser import Config
        config = Config()
        config.root["f"] = "-3.14"
        assert config.get_float("f") == pytest.approx(-3.14)

    def test_get_array_with_strings_as_ints(self):
        from solocoder_py.config_parser import Config
        config = Config()
        config.root["arr"] = ["10", "20", "30"]
        assert config.get_array("arr", element_type="int") == [10, 20, 30]
