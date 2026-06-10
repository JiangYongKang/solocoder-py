from __future__ import annotations

import pytest

from solocoder_py.csv_parser import (
    CSVParser,
    CSVParserError,
    UnclosedQuoteError,
    UnexpectedQuoteError,
)


class TestExceptionsHierarchy:
    def test_all_exceptions_inherit_from_base(self):
        assert issubclass(UnclosedQuoteError, CSVParserError)
        assert issubclass(UnexpectedQuoteError, CSVParserError)


class TestEmptyInput:
    def test_empty_string(self, parser: CSVParser):
        result = parser.parse("")
        assert result.header is None
        assert result.rows == []
        assert result.data == []
        assert result.field_mismatch_lines == []

    def test_only_newlines(self, parser: CSVParser):
        result = parser.parse("\n\n\n")
        assert result.header == [""]
        assert len(result.rows) == 2
        assert all(r.fields == [""] for r in result.rows)


class TestBasicParsing:
    def test_single_row_without_header(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b,c")
        assert result.header is None
        assert result.data == [["a", "b", "c"]]

    def test_single_row_with_header(self, parser: CSVParser):
        result = parser.parse("name,age,city")
        assert result.header == ["name", "age", "city"]
        assert result.data == []

    def test_multiple_rows(self, parser: CSVParser):
        text = "name,age\nAlice,30\nBob,25"
        result = parser.parse(text)
        assert result.header == ["name", "age"]
        assert result.data == [["Alice", "30"], ["Bob", "25"]]

    def test_single_field_single_row(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("hello")
        assert result.data == [["hello"]]

    def test_single_field_multiple_rows(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a\nb\nc")
        assert result.data == [["a"], ["b"], ["c"]]

    def test_empty_fields(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,,c\n,d,")
        assert result.data == [["a", "", "c"], ["", "d", ""]]

    def test_all_empty_fields(self, parser_no_header: CSVParser):
        result = parser_no_header.parse(",,,")
        assert result.data == [["", "", "", ""]]

    def test_custom_delimiter(self):
        parser = CSVParser(delimiter=";", has_header=False)
        result = parser.parse("a;b;c\n1;2;3")
        assert result.data == [["a", "b", "c"], ["1", "2", "3"]]

    def test_tab_delimiter(self):
        parser = CSVParser(delimiter="\t", has_header=False)
        result = parser.parse("a\tb\tc")
        assert result.data == [["a", "b", "c"]]

    def test_windows_line_endings(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\r\nc,d\r\ne,f")
        assert result.data == [["a", "b"], ["c", "d"], ["e", "f"]]

    def test_mixed_line_endings(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\nc,d\r\ne,f")
        assert result.data == [["a", "b"], ["c", "d"], ["e", "f"]]


class TestQuotedFields:
    def test_simple_quoted_field(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"hello",world')
        assert result.data == [["hello", "world"]]

    def test_quoted_field_with_delimiter(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"a,b",c')
        assert result.data == [["a,b", "c"]]

    def test_quoted_field_with_double_quotes_escape(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"he said ""hello""",world')
        assert result.data == [['he said "hello"', "world"]]

    def test_all_quoted_fields(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"a","b","c"')
        assert result.data == [["a", "b", "c"]]

    def test_quoted_field_empty(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"","b"')
        assert result.data == [["", "b"]]

    def test_quoted_field_with_spaces(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('" hello world ",foo')
        assert result.data == [[" hello world ", "foo"]]

    def test_quoted_field_only_double_quotes(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"""""",b')
        assert result.data == [['""', "b"]]

    def test_multiple_quoted_fields(self, parser_no_header: CSVParser):
        text = '"field1","field2","field3"\n"a,b","c""d","e\nf"'
        result = parser_no_header.parse(text)
        assert result.data[0] == ["field1", "field2", "field3"]
        assert result.data[1][0] == "a,b"
        assert result.data[1][1] == 'c"d'
        assert result.data[1][2] == "e\nf"


class TestEmbeddedNewlines:
    def test_single_newline_in_quoted_field(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"line1\nline2",b')
        assert result.data == [["line1\nline2", "b"]]

    def test_multiple_newlines_in_quoted_field(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"a\n\nb\nc",d')
        assert result.data == [["a\n\nb\nc", "d"]]

    def test_embedded_newline_correct_line_numbering(self, parser: CSVParser):
        text = 'name,desc\n"Alice","line1\nline2"\n"Bob","simple"'
        result = parser.parse(text)
        assert len(result.rows) == 2
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 4
        assert result.rows[0].fields[1] == "line1\nline2"
        assert result.rows[1].fields[1] == "simple"

    def test_embedded_newline_with_crlf(self, parser: CSVParser):
        text = 'name,desc\n"Alice","line1\r\nline2"\n"Bob","simple"'
        result = parser.parse(text)
        assert len(result.rows) == 2
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 4
        assert result.rows[0].fields[1] == "line1\r\nline2"
        assert result.rows[1].fields[1] == "simple"

    def test_embedded_cr_in_quoted_field_line_number(self, parser: CSVParser):
        text = 'name,desc\n"Alice","line1\rline2"\n"Bob","simple"'
        result = parser.parse(text)
        assert len(result.rows) == 2
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 4
        assert result.rows[0].fields[1] == "line1\rline2"
        assert result.rows[1].fields[1] == "simple"

    def test_embedded_crlf_in_quoted_field_line_number(self, parser: CSVParser):
        text = 'name,desc\n"Alice","line1\r\nline2"\n"Bob","simple"'
        result = parser.parse(text)
        assert len(result.rows) == 2
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 4
        assert result.rows[0].fields[1] == "line1\r\nline2"
        assert result.rows[1].fields[1] == "simple"

    def test_multiple_cr_in_quoted_field(self, parser: CSVParser):
        text = 'name,desc\n"Alice","a\rb\rc\rd"\n"Bob","next"'
        result = parser.parse(text)
        assert len(result.rows) == 2
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 6
        assert result.rows[0].fields[1] == "a\rb\rc\rd"

    def test_cr_outside_quotes_as_line_separator(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\rc,d\re,f")
        assert result.data == [["a", "b"], ["c", "d"], ["e", "f"]]
        assert result.rows[0].line_number == 1
        assert result.rows[1].line_number == 2
        assert result.rows[2].line_number == 3

    def test_mixed_cr_and_lf_line_endings(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\nc,d\re,f\r\ng,h")
        assert result.data == [["a", "b"], ["c", "d"], ["e", "f"], ["g", "h"]]
        assert result.rows[0].line_number == 1
        assert result.rows[1].line_number == 2
        assert result.rows[2].line_number == 3
        assert result.rows[3].line_number == 4


class TestChineseAndSpecialCharacters:
    def test_chinese_characters(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("姓名,年龄\n张三,30\n李四,25")
        assert result.data == [["姓名", "年龄"], ["张三", "30"], ["李四", "25"]]

    def test_chinese_in_quoted_fields(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"你好,世界","测试"')
        assert result.data == [["你好,世界", "测试"]]

    def test_mixed_chinese_and_english(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("name,中文名\nAlice,爱丽丝\nBob,鲍勃")
        assert result.data == [
            ["name", "中文名"],
            ["Alice", "爱丽丝"],
            ["Bob", "鲍勃"],
        ]

    def test_emoji_characters(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,🎉,c\n🔥,b,💻")
        assert result.data == [["a", "🎉", "c"], ["🔥", "b", "💻"]]

    def test_unicode_characters(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("café,naïve,résumé")
        assert result.data == [["café", "naïve", "résumé"]]

    def test_special_punctuation(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"!@#$%^&*()","<>,./?;:\'[]{}"')
        assert result.data == [["!@#$%^&*()", "<>,./?;:'[]{}"]]


class TestFieldMismatch:
    def test_fewer_fields_detected(self, parser: CSVParser):
        text = "a,b,c\n1,2\n4,5,6"
        result = parser.parse(text)
        assert result.field_mismatch_lines == [2]
        assert result.data == [["1", "2"], ["4", "5", "6"]]

    def test_more_fields_detected(self, parser: CSVParser):
        text = "a,b,c\n1,2,3,4\n4,5,6"
        result = parser.parse(text)
        assert result.field_mismatch_lines == [2]
        assert result.data == [["1", "2", "3", "4"], ["4", "5", "6"]]

    def test_multiple_mismatch_lines(self, parser: CSVParser):
        text = "a,b\n1\n2,3,4\n5,6"
        result = parser.parse(text)
        assert result.field_mismatch_lines == [2, 3]

    def test_align_fields_pad_missing(self, parser_align: CSVParser):
        text = "a,b,c\n1,2\n4,5,6"
        result = parser_align.parse(text)
        assert result.data == [["1", "2", ""], ["4", "5", "6"]]

    def test_align_fields_truncate_extra(self, parser_align: CSVParser):
        text = "a,b,c\n1,2,3,4,5\n4,5,6"
        result = parser_align.parse(text)
        assert result.data == [["1", "2", "3"], ["4", "5", "6"]]

    def test_align_fields_both_pad_and_truncate(self, parser_align: CSVParser):
        text = "a,b,c\n1\n2,3,4,5\n6,7,8"
        result = parser_align.parse(text)
        assert result.field_mismatch_lines == [2, 3]
        assert result.data == [["1", "", ""], ["2", "3", "4"], ["6", "7", "8"]]

    def test_no_header_no_mismatch(self, parser_no_header: CSVParser):
        text = "a,b\n1,2,3\n4"
        result = parser_no_header.parse(text)
        assert result.field_mismatch_lines == []
        assert result.data == [["a", "b"], ["1", "2", "3"], ["4"]]


class TestErrorCases:
    def test_unclosed_quote_simple(self, parser_no_header: CSVParser):
        with pytest.raises(UnclosedQuoteError) as exc_info:
            parser_no_header.parse('"hello,world')
        assert exc_info.value.position > 0

    def test_unclosed_quote_at_end(self, parser_no_header: CSVParser):
        with pytest.raises(UnclosedQuoteError):
            parser_no_header.parse('a,"b')

    def test_unclosed_quote_with_newline(self, parser_no_header: CSVParser):
        with pytest.raises(UnclosedQuoteError):
            parser_no_header.parse('"line1\nline2,rest')

    def test_unexpected_quote_after_quoted_field(self, parser_no_header: CSVParser):
        with pytest.raises(UnexpectedQuoteError):
            parser_no_header.parse('"abc"def,g')

    def test_unexpected_quote_after_quoted_field_mid_row(self, parser_no_header: CSVParser):
        with pytest.raises(UnexpectedQuoteError):
            parser_no_header.parse('a,"b"extra,c')

    def test_unclosed_quote_in_multiline(self, parser_no_header: CSVParser):
        with pytest.raises(UnclosedQuoteError):
            parser_no_header.parse('a,b\n"this quote never closes\nc,d')


class TestEdgeCases:
    def test_trailing_newline(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\nc,d\n")
        assert result.data == [["a", "b"], ["c", "d"]]

    def test_quote_followed_by_delimiter(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"a",b')
        assert result.data == [["a", "b"]]

    def test_delimiter_followed_by_quote(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('a,"b"')
        assert result.data == [["a", "b"]]

    def test_consecutive_quoted_fields(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('"a""b","c""d"')
        assert result.data == [['a"b', 'c"d']]

    def test_nested_quotes_extreme(self, parser_no_header: CSVParser):
        result = parser_no_header.parse('""""""')
        assert result.data == [['""']]

    def test_quoted_field_after_empty(self, parser_no_header: CSVParser):
        result = parser_no_header.parse(',"quoted",')
        assert result.data == [["", "quoted", ""]]

    def test_whitespace_outside_quotes_preserved(self, parser_no_header: CSVParser):
        result = parser_no_header.parse(' a , "b" , c ')
        assert result.data == [[" a ", ' "b" ', " c "]]

    def test_only_carriage_return(self, parser_no_header: CSVParser):
        result = parser_no_header.parse("a,b\rc,d")
        assert result.data == [["a", "b"], ["c", "d"]]

    def test_complex_real_world_scenario(self, parser: CSVParser):
        text = (
            'id,name,description,value\n'
            '1,Alice,"Alice is a ""good"" developer\nwith 5 years exp",100\n'
            '2,Bob,Bob likes coffee,200\n'
            '3,"Charlie, Jr.","Charlie ""The Man"" Junior\nloves coding",300\n'
        )
        result = parser.parse(text)
        assert result.header == ["id", "name", "description", "value"]
        assert len(result.rows) == 3
        assert result.rows[0].fields == [
            "1",
            "Alice",
            'Alice is a "good" developer\nwith 5 years exp',
            "100",
        ]
        assert result.rows[1].fields == ["2", "Bob", "Bob likes coffee", "200"]
        assert result.rows[2].fields == [
            "3",
            "Charlie, Jr.",
            'Charlie "The Man" Junior\nloves coding',
            "300",
        ]


class TestParseResult:
    def test_parse_result_data_property(self, parser: CSVParser):
        text = "a,b\n1,2\n3,4"
        result = parser.parse(text)
        assert result.data == [["1", "2"], ["3", "4"]]

    def test_parse_result_rows_have_line_numbers(self, parser: CSVParser):
        text = "a,b\n1,2\n3,4"
        result = parser.parse(text)
        assert result.rows[0].line_number == 2
        assert result.rows[1].line_number == 3

    def test_parse_result_empty_rows(self, parser: CSVParser):
        result = parser.parse("a,b,c")
        assert result.data == []
        assert result.field_mismatch_lines == []
