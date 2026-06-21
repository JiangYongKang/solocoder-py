from __future__ import annotations

from datetime import date, datetime, time, timezone, timedelta

import pytest

from solocoder_py.config_parser import (
    Config,
    ConfigParser,
    parse_toml,
    parse_ini,
)


class TestBasicKeyValueParsing:
    def test_parse_simple_string(self):
        config = parse_toml('name = "Alice"')
        assert config["name"] == "Alice"

    def test_parse_literal_string(self):
        config = parse_toml("path = 'C:\\Users\\test'")
        assert config["path"] == "C:\\Users\\test"

    def test_parse_integer(self):
        config = parse_toml("count = 42")
        assert config["count"] == 42
        assert isinstance(config["count"], int)

    def test_parse_negative_integer(self):
        config = parse_toml("temp = -10")
        assert config["temp"] == -10

    def test_parse_hex_integer(self):
        config = parse_toml("hex_val = 0xFF")
        assert config["hex_val"] == 255

    def test_parse_octal_integer(self):
        config = parse_toml("oct_val = 0o777")
        assert config["oct_val"] == 511

    def test_parse_binary_integer(self):
        config = parse_toml("bin_val = 0b1010")
        assert config["bin_val"] == 10

    def test_parse_float(self):
        config = parse_toml("pi = 3.14159")
        assert config["pi"] == pytest.approx(3.14159)
        assert isinstance(config["pi"], float)

    def test_parse_scientific_float(self):
        config = parse_toml("sci = 1.5e3")
        assert config["sci"] == 1500.0

    def test_parse_boolean_true(self):
        config = parse_toml("active = true")
        assert config["active"] is True

    def test_parse_boolean_false(self):
        config = parse_toml("active = false")
        assert config["active"] is False

    def test_parse_integer_with_underscores(self):
        config = parse_toml("big = 1_000_000")
        assert config["big"] == 1000000

    def test_parse_float_with_underscores(self):
        config = parse_toml("flt = 3_141.59_26")
        assert config["flt"] == pytest.approx(3141.5926)

    def test_parse_positive_number(self):
        config = parse_toml("num = +5")
        assert config["num"] == 5

    def test_parse_date(self):
        config = parse_toml("dob = 1979-05-27")
        assert config["dob"] == date(1979, 5, 27)

    def test_parse_local_datetime(self):
        config = parse_toml("ts = 1979-05-27T07:32:00")
        assert config["ts"] == datetime(1979, 5, 27, 7, 32, 0)

    def test_parse_local_datetime_with_space(self):
        config = parse_toml("ts = 1979-05-27 07:32:00")
        assert config["ts"] == datetime(1979, 5, 27, 7, 32, 0)

    def test_parse_local_datetime_with_microseconds(self):
        config = parse_toml("ts = 1979-05-27T07:32:00.123456")
        assert config["ts"] == datetime(1979, 5, 27, 7, 32, 0, 123456)

    def test_parse_datetime_with_utc_offset(self):
        config = parse_toml("ts = 1979-05-27T07:32:00Z")
        expected = datetime(1979, 5, 27, 7, 32, 0, tzinfo=timezone.utc)
        assert config["ts"] == expected

    def test_parse_datetime_with_positive_offset(self):
        config = parse_toml("ts = 1979-05-27T07:32:00+08:00")
        tz = timezone(timedelta(hours=8))
        expected = datetime(1979, 5, 27, 7, 32, 0, tzinfo=tz)
        assert config["ts"] == expected

    def test_parse_local_time(self):
        config = parse_toml("t = 07:32:00")
        assert config["t"] == time(7, 32, 0)

    def test_parse_local_time_with_microseconds(self):
        config = parse_toml("t = 07:32:00.999999")
        assert config["t"] == time(7, 32, 0, 999999)

    def test_parse_string_with_escape_sequences(self):
        config = parse_toml(r'str = "hello\t\nworld\\"')
        assert config["str"] == "hello\t\nworld\\"

    def test_parse_string_with_unicode_escape(self):
        config = parse_toml('heart = "\\u00B7"')
        assert config["heart"] == "\u00B7"

    def test_parse_simple_array(self):
        config = parse_toml("arr = [1, 2, 3]")
        assert config["arr"] == [1, 2, 3]

    def test_parse_string_array(self):
        config = parse_toml('colors = ["red", "green", "blue"]')
        assert config["colors"] == ["red", "green", "blue"]

    def test_parse_nested_array(self):
        config = parse_toml("nested = [[1, 2], [3, 4]]")
        assert config["nested"] == [[1, 2], [3, 4]]

    def test_parse_mixed_type_array(self):
        config = parse_toml('mixed = [1, "two", 3.0]')
        assert config["mixed"] == [1, "two", 3.0]

    def test_parse_empty_array(self):
        config = parse_toml("empty = []")
        assert config["empty"] == []

    def test_parse_inline_table(self):
        config = parse_toml('point = { x = 1, y = 2 }')
        assert config["point"]["x"] == 1
        assert config["point"]["y"] == 2

    def test_parse_empty_inline_table(self):
        config = parse_toml("empty = {}")
        assert len(config["empty"]) == 0

    def test_parse_multiline_basic_string(self):
        text = '''desc = """
line1
line2
"""'''
        config = parse_toml(text)
        assert config["desc"] == "line1\nline2"

    def test_parse_multiline_literal_string(self):
        text = "regexp = '''\n\\d+\n'''"
        config = parse_toml(text)
        assert config["regexp"] == "\\d+"


class TestNestedTableParsing:
    def test_parse_simple_table(self):
        config = parse_toml('[server]\nhost = "localhost"\nport = 8080')
        assert config["server"]["host"] == "localhost"
        assert config["server"]["port"] == 8080

    def test_parse_nested_table(self):
        text = '''
[a.b.c]
key = "value"
'''
        config = parse_toml(text)
        assert config["a.b.c.key"] == "value"
        assert config["a"]["b"]["c"]["key"] == "value"

    def test_parse_multiple_tables(self):
        text = '''
[server]
host = "localhost"

[client]
timeout = 30
'''
        config = parse_toml(text)
        assert config["server"]["host"] == "localhost"
        assert config["client"]["timeout"] == 30

    def test_parse_implicit_tables(self):
        text = '''
[level1.level2.level3]
data = true
'''
        config = parse_toml(text)
        assert "level1" in config
        assert "level2" in config["level1"]
        assert "level3" in config["level1"]["level2"]
        assert config["level1.level2.level3.data"] is True

    def test_quoted_table_name(self):
        text = '''
["my.table"]
key = 123
'''
        config = parse_toml(text)
        assert config["my.table"]["key"] == 123

    def test_quoted_key(self):
        config = parse_toml('"my key" = 42')
        assert config["my key"] == 42

    def test_dotted_key(self):
        config = parse_toml("a.b.c = 1")
        assert config["a"]["b"]["c"] == 1

    def test_traversal_with_dot_notation(self):
        text = '''
[app]
version = "1.0"

[app.server]
port = 9000
'''
        config = parse_toml(text)
        assert config.get("app.version") == "1.0"
        assert config.get("app.server.port") == 9000


class TestArrayTableParsing:
    def test_parse_array_table(self):
        text = '''
[[product]]
name = "Hammer"
price = 10

[[product]]
name = "Nail"
price = 2
'''
        config = parse_toml(text)
        products = config.get_array_table("product")
        assert len(products) == 2
        assert products[0]["name"] == "Hammer"
        assert products[1]["name"] == "Nail"
        assert products[1]["price"] == 2

    def test_array_table_with_nested_tables(self):
        text = '''
[[database]]
name = "main"

[[database.config]]
timeout = 30

[[database]]
name = "backup"

[[database.config]]
timeout = 60
'''
        config = parse_toml(text)
        databases = config.get_array_table("database")
        assert len(databases) == 2
        cfgs0 = databases[0].get_array_table("config")
        cfgs1 = databases[1].get_array_table("config")
        assert cfgs0[0]["timeout"] == 30
        assert cfgs1[0]["timeout"] == 60

    def test_single_element_array_table(self):
        text = '''
[[items]]
value = 1
'''
        config = parse_toml(text)
        items = config.get_array_table("items")
        assert len(items) == 1
        assert items[0]["value"] == 1


class TestIniParsing:
    def test_parse_ini_section(self, sample_ini_text):
        config = parse_ini(sample_ini_text)
        assert config["section1"]["key1"] == "value1"
        assert config["section1"]["key2"] == 42
        assert config["section1"]["key3"] is True

    def test_parse_ini_semicolon_comment(self):
        text = '''; this is a comment
[sec]
; another comment
key = 1
'''
        config = parse_ini(text)
        assert config["sec"]["key"] == 1

    def test_parse_ini_hash_comment(self):
        text = '''# this is a comment
[sec]
key = 2
'''
        config = parse_ini(text)
        assert config["sec"]["key"] == 2

    def test_parse_ini_key_overwrite(self):
        text = '''
[section]
key = first
key = second
'''
        config = parse_ini(text)
        assert config["section"]["key"] == "second"

    def test_parse_ini_global_keys(self):
        text = '''global_key = "global_value"
[section]
section_key = "section_value"
'''
        config = parse_ini(text)
        assert config["global_key"] == "global_value"
        assert config["section"]["section_key"] == "section_value"

    def test_parse_ini_bare_strings_allowed(self):
        text = '''
[section]
key1 = hello
key2 = world peace
'''
        config = parse_ini(text)
        assert config["section"]["key1"] == "hello"
        assert config["section"]["key2"] == "world peace"

    def test_parse_ini_duplicate_key_overwrite_multiple_times(self):
        text = '''
[section]
key = first
key = second
key = third
'''
        config = parse_ini(text)
        assert config["section"]["key"] == "third"

    def test_parse_ini_duplicate_key_in_root_overwrite(self):
        text = '''
global = a
global = b
'''
        config = parse_ini(text)
        assert config["global"] == "b"

    def test_parse_ini_inline_table_duplicate_key_overwrite(self):
        text = '''
section_key = { a = 1, a = 2 }
'''
        config = parse_ini(text)
        assert config["section_key"]["a"] == 2

    def test_parse_ini_inline_table_duplicate_key_multiple_overwrite(self):
        text = '''
point = { x = 0, y = 0, x = 10, y = 20, x = 5 }
'''
        config = parse_ini(text)
        assert config["point"]["x"] == 5
        assert config["point"]["y"] == 20

    def test_parse_ini_inline_table_duplicate_key_different_types(self):
        text = '''
val = { k = "first", k = 42 }
'''
        config = parse_ini(text)
        assert config["val"]["k"] == 42

    def test_parse_ini_inline_table_duplicate_key_bool_value(self):
        text = '''
flags = { enabled = true, enabled = false, active = false, active = true }
'''
        config = parse_ini(text)
        assert config["flags"]["enabled"] is False
        assert config["flags"]["active"] is True

    def test_parse_ini_inline_table_duplicate_key_array_value(self):
        text = '''
data = { items = [1, 2], items = [3, 4, 5] }
'''
        config = parse_ini(text)
        assert config["data"]["items"] == [3, 4, 5]

    def test_parse_ini_inline_table_duplicate_key_nested_inner(self):
        text = '''
outer = { inner = { a = 1, a = 2 } }
'''
        config = parse_ini(text)
        assert config["outer"]["inner"]["a"] == 2

    def test_parse_ini_inline_table_duplicate_key_nested_multiple_levels(self):
        text = '''
root = {
    x = 0,
    mid = { y = 1, y = 10, deep = { z = 2, z = 20 } },
    x = 5
}
'''
        config = parse_ini(text)
        assert config["root"]["x"] == 5
        assert config["root"]["mid"]["y"] == 10
        assert config["root"]["mid"]["deep"]["z"] == 20

    def test_parse_ini_inline_table_duplicate_key_nested_and_flat_mixed(self):
        text = '''
cfg = { a = "old", inner = { b = 1, b = 2, c = 0 }, a = "new" }
'''
        config = parse_ini(text)
        assert config["cfg"]["a"] == "new"
        assert config["cfg"]["inner"]["b"] == 2
        assert config["cfg"]["inner"]["c"] == 0

    def test_parse_ini_inline_table_duplicate_key_inner_is_replaced(self):
        text = '''
cfg = { inner = { b = 1 }, inner = { c = 2 } }
'''
        config = parse_ini(text)
        assert "b" not in config["cfg"]["inner"]
        assert config["cfg"]["inner"]["c"] == 2

    def test_parse_ini_inline_table_duplicate_key_with_array_of_inline_tables(self):
        text = '''
data = { points = [{x = 1, x = 100}, {y = 2, y = 200}] }
'''
        config = parse_ini(text)
        assert config["data"]["points"][0]["x"] == 100
        assert config["data"]["points"][1]["y"] == 200

    def test_parse_ini_inline_table_duplicate_key_float_and_date_values(self):
        text = '''
mixed = { pi = 3.0, pi = 3.14159, start = 2023-01-01, start = 2024-06-20 }
'''
        config = parse_ini(text)
        assert config["mixed"]["pi"] == 3.14159
        from datetime import date
        assert config["mixed"]["start"] == date(2024, 6, 20)


class TestTypeConversion:
    def test_get_bool_from_bool(self):
        config = parse_toml("active = true")
        assert config.get_bool("active") is True

    def test_get_bool_from_string_true(self):
        config = Config()
        config.root["flag"] = "True"
        assert config.get_bool("flag") is True
        config.root["flag"] = "true"
        assert config.get_bool("flag") is True
        config.root["flag"] = "TRUE"
        assert config.get_bool("flag") is True

    def test_get_bool_from_string_false(self):
        config = Config()
        config.root["flag"] = "False"
        assert config.get_bool("flag") is False
        config.root["flag"] = "false"
        assert config.get_bool("flag") is False
        config.root["flag"] = "FALSE"
        assert config.get_bool("flag") is False

    def test_get_bool_from_string_yes_no(self):
        config = Config()
        config.root["a"] = "yes"
        config.root["b"] = "on"
        config.root["c"] = "no"
        config.root["d"] = "off"
        assert config.get_bool("a") is True
        assert config.get_bool("b") is True
        assert config.get_bool("c") is False
        assert config.get_bool("d") is False

    def test_get_bool_from_int(self):
        config = Config()
        config.root["a"] = 1
        config.root["b"] = 0
        assert config.get_bool("a") is True
        assert config.get_bool("b") is False

    def test_get_int_from_int(self):
        config = parse_toml("num = 42")
        assert config.get_int("num") == 42

    def test_get_int_from_string(self):
        config = Config()
        config.root["num"] = "123"
        assert config.get_int("num") == 123

    def test_get_int_from_bool(self):
        config = Config()
        config.root["a"] = True
        config.root["b"] = False
        assert config.get_int("a") == 1
        assert config.get_int("b") == 0

    def test_get_int_from_float(self):
        config = Config()
        config.root["num"] = 5.0
        assert config.get_int("num") == 5

    def test_get_float_from_int(self):
        config = parse_toml("n = 5")
        assert config.get_float("n") == 5.0

    def test_get_float_from_string(self):
        config = Config()
        config.root["f"] = "3.14"
        assert config.get_float("f") == pytest.approx(3.14)

    def test_get_str_from_string(self):
        config = parse_toml('s = "hello"')
        assert config.get_str("s") == "hello"

    def test_get_str_from_int(self):
        config = parse_toml("n = 42")
        assert config.get_str("n") == "42"

    def test_get_array(self):
        config = parse_toml("arr = [1, 2, 3]")
        assert config.get_array("arr") == [1, 2, 3]

    def test_get_array_with_int_type(self):
        config = parse_toml('arr = ["1", "2", "3"]')
        assert config.get_array("arr", element_type="int") == [1, 2, 3]

    def test_get_array_with_bool_type(self):
        config = parse_toml('arr = ["true", "false", "1"]')
        assert config.get_array("arr", element_type="bool") == [True, False, True]

    def test_get_array_with_float_type(self):
        config = parse_toml('arr = ["1.5", "2.5", "3"]')
        assert config.get_array("arr", element_type="float") == [1.5, 2.5, 3.0]

    def test_get_array_with_str_type(self):
        config = parse_toml("arr = [1, 2, 3]")
        assert config.get_array("arr", element_type="str") == ["1", "2", "3"]

    def test_get_table(self):
        text = '''
[server]
host = "localhost"
'''
        config = parse_toml(text)
        server = config.get_table("server")
        assert isinstance(server, Config)
        assert server["host"] == "localhost"


class TestCommentExtraction:
    def test_single_comment_before_key(self):
        text = '''# This is a comment
key = "value"
'''
        config = parse_toml(text)
        assert config.get_comment("key") == "This is a comment"

    def test_multiline_comment_before_key(self):
        text = '''# Line 1
# Line 2
key = "value"
'''
        config = parse_toml(text)
        assert config.get_comment("key") == "Line 1\nLine 2"

    def test_comment_in_table(self):
        text = '''
[section]
# Section key comment
section_key = 100
'''
        config = parse_toml(text)
        assert config.get_comment("section.section_key") == "Section key comment"

    def test_no_comment(self):
        config = parse_toml('key = "value"')
        assert config.get_comment("key") is None

    def test_comment_resets_after_key(self):
        text = '''# Comment for key1
key1 = "a"
key2 = "b"
'''
        config = parse_toml(text)
        assert config.get_comment("key1") == "Comment for key1"
        assert config.get_comment("key2") is None


class TestFullDocumentParsing:
    def test_full_toml_document(self, sample_toml_text):
        config = parse_toml(sample_toml_text)
        assert config["title"] == "Example Config"
        assert config["server"]["host"] == "localhost"
        assert config["server"]["port"] == 8080
        assert config["server"]["enabled"] is True
        assert config["server"]["tls"]["cert_file"] == "/etc/ssl/cert.pem"
        databases = config.get_array_table("database")
        assert len(databases) == 2
        assert databases[0]["name"] == "primary"
        assert databases[1]["name"] == "secondary"

    def test_to_dict(self, sample_toml_text):
        config = parse_toml(sample_toml_text)
        d = config.to_dict()
        assert d["title"] == "Example Config"
        assert d["server"]["host"] == "localhost"
        assert len(d["database"]) == 2
        assert d["database"][0]["name"] == "primary"

    def test_config_contains(self):
        config = parse_toml('[a.b]\nc = 1')
        assert "a" in config
        assert "a.b" in config
        assert "a.b.c" in config
        assert "nonexistent" not in config

    def test_config_get_with_default(self):
        config = parse_toml('existing = "yes"')
        assert config.get("existing") == "yes"
        assert config.get("missing", "default") == "default"
        assert config.get("missing") is None
