from __future__ import annotations

from typing import List, Optional

from .exceptions import UnclosedQuoteError, UnexpectedQuoteError
from .models import CSVRow, ParseResult


class CSVParser:
    def __init__(
        self,
        delimiter: str = ",",
        has_header: bool = True,
        align_fields: bool = False,
    ) -> None:
        self.delimiter = delimiter
        self.has_header = has_header
        self.align_fields = align_fields

    def parse(self, text: str) -> ParseResult:
        if not text:
            return ParseResult(header=None, rows=[])

        rows_data = self._parse_rows(text)

        if not rows_data:
            return ParseResult(header=None, rows=[])

        header: Optional[List[str]] = None
        data_rows: List[CSVRow] = []
        field_mismatch_lines: List[int] = []

        expected_field_count: Optional[int] = None

        start_idx = 0

        if self.has_header:
            header = rows_data[0].fields
            expected_field_count = len(header)
            start_idx = 1

        for row_data in rows_data[start_idx:]:
            if expected_field_count is not None and len(row_data.fields) != expected_field_count:
                field_mismatch_lines.append(row_data.line_number)
                if self.align_fields:
                    row_data = self._align_row(row_data, expected_field_count)
            data_rows.append(row_data)

        return ParseResult(
            header=header,
            rows=data_rows,
            field_mismatch_lines=field_mismatch_lines,
        )

    def _parse_rows(self, text: str) -> List[CSVRow]:
        rows: List[CSVRow] = []
        line_number = 1
        row_start_line = 1
        current_row_fields: List[str] = []
        current_field_chars: List[str] = []
        in_quotes = False
        i = 0
        n = len(text)

        while i < n:
            ch = text[i]

            if in_quotes:
                if ch == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        current_field_chars.append('"')
                        i += 2
                        continue
                    else:
                        in_quotes = False
                        i += 1
                        if i < n:
                            next_ch = text[i]
                            if next_ch not in (self.delimiter, "\r", "\n"):
                                raise UnexpectedQuoteError(i)
                        continue
                else:
                    current_field_chars.append(ch)
                    if ch == "\n":
                        line_number += 1
                    i += 1
                    continue
            else:
                if ch == '"':
                    if not current_field_chars:
                        in_quotes = True
                        i += 1
                        continue
                    else:
                        current_field_chars.append(ch)
                        i += 1
                        continue
                elif ch == self.delimiter:
                    current_row_fields.append("".join(current_field_chars))
                    current_field_chars = []
                    i += 1
                    continue
                elif ch == "\r":
                    if i + 1 < n and text[i + 1] == "\n":
                        current_row_fields.append("".join(current_field_chars))
                        rows.append(CSVRow(fields=current_row_fields, line_number=row_start_line))
                        current_row_fields = []
                        current_field_chars = []
                        line_number += 1
                        row_start_line = line_number
                        i += 2
                        continue
                    else:
                        current_row_fields.append("".join(current_field_chars))
                        rows.append(CSVRow(fields=current_row_fields, line_number=row_start_line))
                        current_row_fields = []
                        current_field_chars = []
                        line_number += 1
                        row_start_line = line_number
                        i += 1
                        continue
                elif ch == "\n":
                    current_row_fields.append("".join(current_field_chars))
                    rows.append(CSVRow(fields=current_row_fields, line_number=row_start_line))
                    current_row_fields = []
                    current_field_chars = []
                    line_number += 1
                    row_start_line = line_number
                    i += 1
                    continue
                else:
                    current_field_chars.append(ch)
                    i += 1
                    continue

        if in_quotes:
            raise UnclosedQuoteError(i)

        if current_field_chars or current_row_fields:
            current_row_fields.append("".join(current_field_chars))
            rows.append(CSVRow(fields=current_row_fields, line_number=row_start_line))

        return rows

    def _align_row(self, row: CSVRow, expected_count: int) -> CSVRow:
        fields = row.fields
        if len(fields) < expected_count:
            fields = fields + [""] * (expected_count - len(fields))
        elif len(fields) > expected_count:
            fields = fields[:expected_count]
        return CSVRow(fields=fields, line_number=row.line_number)
