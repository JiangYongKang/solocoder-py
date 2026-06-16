from __future__ import annotations

import re
from html import escape
from typing import List, Optional, Tuple

from .exceptions import UnclosedCodeBlockError
from .highlighter import HighlightRegistry, get_default_registry
from .models import ConversionResult, TableData, TableRow
from .sanitizer import HtmlSanitizer


class MarkdownConverter:
    def __init__(
        self,
        highlight_registry: Optional[HighlightRegistry] = None,
        sanitize: bool = True,
    ) -> None:
        self.highlight_registry = highlight_registry or get_default_registry()
        self.sanitize = sanitize
        self._sanitizer = HtmlSanitizer()
        self.warnings: List[str] = []

    def convert(self, markdown: str) -> ConversionResult:
        self.warnings = []
        self._sanitizer.warnings = []

        if not markdown:
            return ConversionResult(html="", warnings=[])

        lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        blocks = self._parse_blocks(lines)
        html = "\n".join(blocks)

        if self.sanitize:
            html = self._sanitizer.sanitize(html)
            self.warnings.extend(self._sanitizer.warnings)

        return ConversionResult(html=html, warnings=self.warnings.copy())

    def _parse_blocks(self, lines: List[str]) -> List[str]:
        blocks: List[str] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            if not line.strip():
                i += 1
                continue

            if self._is_heading(line):
                block, i = self._parse_heading(lines, i)
                blocks.append(block)
                continue

            if self._is_horizontal_rule(line):
                blocks.append("<hr />")
                i += 1
                continue

            if self._is_code_block(line):
                block, i = self._parse_code_block(lines, i)
                blocks.append(block)
                continue

            if self._is_blockquote(line):
                block, i = self._parse_blockquote(lines, i)
                blocks.append(block)
                continue

            if self._is_unordered_list_item(line) or self._is_ordered_list_item(line):
                block, i = self._parse_list(lines, i)
                blocks.append(block)
                continue

            if self._is_table_possible(lines, i):
                block, i = self._parse_table(lines, i)
                if block is not None:
                    blocks.append(block)
                    continue

            block, i = self._parse_paragraph(lines, i)
            blocks.append(block)

        return blocks

    def _is_heading(self, line: str) -> bool:
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            return False
        count = 0
        for ch in stripped:
            if ch == "#":
                count += 1
            else:
                break
        if count < 1 or count > 6:
            return False
        return len(stripped) > count and stripped[count] == " "

    def _parse_heading(self, lines: List[str], i: int) -> Tuple[str, int]:
        line = lines[i].lstrip()
        level = 0
        while level < len(line) and line[level] == "#":
            level += 1
        text = line[level:].strip()
        text = text.rstrip("#").strip()
        inline_text = self._parse_inline(text)
        return f"<h{level}>{inline_text}</h{level}>", i + 1

    def _is_horizontal_rule(self, line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if stripped[0] not in ("-", "*", "_"):
            return False
        char = stripped[0]
        count = 0
        for ch in stripped:
            if ch == char:
                count += 1
            elif ch != " ":
                return False
        return count >= 3

    def _is_code_block(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith("```") or stripped.startswith("~~~")

    def _parse_code_block(self, lines: List[str], i: int) -> Tuple[str, int]:
        stripped = lines[i].lstrip()
        fence_char = stripped[0]
        fence_len = 0
        while fence_len < len(stripped) and stripped[fence_len] == fence_char:
            fence_len += 1
        language = stripped[fence_len:].strip()

        code_lines: List[str] = []
        j = i + 1
        n = len(lines)
        found_closing = False

        while j < n:
            line = lines[j]
            line_stripped = line.lstrip()
            if line_stripped.startswith(fence_char * fence_len):
                rest = line_stripped[fence_len:].strip()
                if not rest:
                    found_closing = True
                    j += 1
                    break
            code_lines.append(line)
            j += 1

        if not found_closing:
            self.warnings.append("Unclosed code block detected")
            raise UnclosedCodeBlockError()

        code = "\n".join(code_lines)
        code = self._highlight_code(code, language)
        return code, j

    def _highlight_code(self, code: str, language: str) -> str:
        return self.highlight_registry.highlight(code, language)

    def _is_blockquote(self, line: str) -> bool:
        stripped = line.lstrip()
        return stripped.startswith("> ") or stripped == ">"

    def _parse_blockquote(self, lines: List[str], i: int) -> Tuple[str, int]:
        quote_lines: List[str] = []
        j = i
        n = len(lines)

        while j < n:
            line = lines[j]
            if not line.strip():
                break
            stripped = line.lstrip()
            if not stripped.startswith(">"):
                break
            if stripped == ">":
                quote_lines.append("")
            else:
                quote_lines.append(stripped[1:].lstrip())
            j += 1

        content = "\n".join(quote_lines).strip()
        inner_blocks = self._parse_blocks(content.split("\n"))
        inner_html = "\n".join(inner_blocks)
        return f"<blockquote>\n{inner_html}\n</blockquote>", j

    def _is_unordered_list_item(self, line: str) -> bool:
        stripped = line.lstrip()
        if len(stripped) < 2:
            return False
        if stripped[0] in ("-", "*", "+") and stripped[1] == " ":
            return True
        return False

    def _is_ordered_list_item(self, line: str) -> bool:
        stripped = line.lstrip()
        match = re.match(r'^(\d+)\.\s', stripped)
        return match is not None

    def _parse_list(self, lines: List[str], i: int) -> Tuple[str, int]:
        is_ordered = self._is_ordered_list_item(lines[i])
        items: List[List[str]] = []
        current_item: List[str] = []
        j = i
        n = len(lines)
        list_indent = len(lines[j]) - len(lines[j].lstrip())

        while j < n:
            line = lines[j]
            stripped = line.lstrip()
            current_indent = len(line) - len(line.lstrip())

            if not line.strip():
                if j + 1 < n:
                    next_line = lines[j + 1]
                    next_stripped = next_line.lstrip()
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent >= list_indent + 2 and next_stripped and (
                        self._is_unordered_list_item(next_stripped)
                        or self._is_ordered_list_item(next_stripped)
                    ):
                        current_item.append("")
                        j += 1
                        continue
                if current_item:
                    items.append(current_item)
                    current_item = []
                j += 1
                continue

            if current_indent < list_indent:
                break

            if current_indent == list_indent:
                is_ul = self._is_unordered_list_item(stripped)
                is_ol = self._is_ordered_list_item(stripped)

                if is_ul or is_ol:
                    if current_item:
                        items.append(current_item)
                        current_item = []

                    if is_ordered and is_ul:
                        break
                    if not is_ordered and is_ol:
                        break

                    content = ""
                    if is_ul:
                        content = stripped[2:]
                    else:
                        match = re.match(r'^\d+\.\s(.*)', stripped)
                        if match:
                            content = match.group(1)

                    current_item = [content]
                    j += 1
                    continue

            if current_item and current_indent > list_indent:
                current_item.append(stripped)
                j += 1
                continue

            break

        if current_item:
            items.append(current_item)

        list_items_html: List[str] = []
        for item_lines in items:
            item_content = "\n".join(item_lines).strip()
            item_html = self._parse_list_item_content(item_content)
            list_items_html.append(f"<li>{item_html}</li>")

        tag = "ol" if is_ordered else "ul"
        items_html = "\n".join(list_items_html)
        return f"<{tag}>\n{items_html}\n</{tag}>", j

    def _parse_list_item_content(self, content: str) -> str:
        if not content:
            return ""
        if "\n" in content:
            inner_blocks = self._parse_blocks(content.split("\n"))
            return "\n".join(inner_blocks)
        return self._parse_inline(content)

    def _is_table_possible(self, lines: List[str], i: int) -> bool:
        if i + 1 >= len(lines):
            return False
        if not lines[i].strip():
            return False
        next_line = lines[i + 1].strip()
        if not next_line:
            return False
        return bool(re.match(r'^[\s\-:|]+$', next_line)) and "---" in next_line

    def _parse_table(self, lines: List[str], i: int) -> Tuple[Optional[str], int]:
        try:
            header_line = lines[i].strip()
            separator_line = lines[i + 1].strip()

            if not header_line or not separator_line:
                return None, i

            header_cells = self._split_table_row(header_line)
            separator_cells = self._split_table_row(separator_line)

            if not header_cells or not separator_cells:
                return None, i

            if len(separator_cells) != len(header_cells):
                if len(separator_cells) < len(header_cells):
                    separator_cells = separator_cells + ["---"] * (len(header_cells) - len(separator_cells))
                else:
                    separator_cells = separator_cells[:len(header_cells)]

            valid_sep = all(self._is_table_separator(cell) for cell in separator_cells)
            if not valid_sep:
                return None, i

            alignments = [self._get_alignment(cell) for cell in separator_cells]

            j = i + 2
            n = len(lines)
            data_rows: List[List[str]] = []

            while j < n:
                line = lines[j].strip()
                if not line:
                    break
                cells = self._split_table_row(line)
                if not cells:
                    break
                data_rows.append(cells)
                j += 1

            expected_cols = len(header_cells)
            for idx, row in enumerate(data_rows):
                if len(row) < expected_cols:
                    data_rows[idx] = row + [""] * (expected_cols - len(row))
                    self.warnings.append(
                        f"Table row {idx + 1} has fewer columns than header"
                    )
                elif len(row) > expected_cols:
                    data_rows[idx] = row[:expected_cols]
                    self.warnings.append(
                        f"Table row {idx + 1} has more columns than header"
                    )

            table_data = TableData(
                header=TableRow(cells=header_cells),
                rows=[TableRow(cells=row) for row in data_rows],
                alignments=alignments,
            )
            return self._render_table(table_data), j

        except Exception:
            return None, i

    def _split_table_row(self, line: str) -> List[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]

        cells: List[str] = []
        current: List[str] = []
        i = 0
        n = len(line)

        while i < n:
            ch = line[i]
            if ch == "\\" and i + 1 < n and line[i + 1] == "|":
                current.append("|")
                i += 2
                continue
            if ch == "|":
                cells.append("".join(current).strip())
                current = []
                i += 1
                continue
            current.append(ch)
            i += 1

        if current or line.endswith("|"):
            cells.append("".join(current).strip())

        return cells

    def _is_table_separator(self, cell: str) -> bool:
        cell = cell.strip()
        if not cell:
            return False
        if cell.startswith(":"):
            cell = cell[1:]
        if cell.endswith(":"):
            cell = cell[:-1]
        if not cell:
            return False
        return all(ch == "-" for ch in cell) and len(cell) >= 1

    def _get_alignment(self, cell: str) -> str:
        cell = cell.strip()
        left = cell.startswith(":")
        right = cell.endswith(":")
        if left and right:
            return "center"
        if right:
            return "right"
        return "left"

    def _render_table(self, table_data: TableData) -> str:
        header_cells = []
        for idx, cell in enumerate(table_data.header.cells):
            inline_cell = self._parse_inline(cell)
            align = ""
            if table_data.alignments and idx < len(table_data.alignments):
                align = f' align="{table_data.alignments[idx]}"'
            header_cells.append(f"<th{align}>{inline_cell}</th>")

        body_rows = []
        for row in table_data.rows:
            row_cells = []
            for idx, cell in enumerate(row.cells):
                inline_cell = self._parse_inline(cell)
                align = ""
                if table_data.alignments and idx < len(table_data.alignments):
                    align = f' align="{table_data.alignments[idx]}"'
                row_cells.append(f"<td{align}>{inline_cell}</td>")
            body_rows.append(f"<tr>{''.join(row_cells)}</tr>")

        thead = f"<thead><tr>{''.join(header_cells)}</tr></thead>"
        tbody = f"<tbody>{''.join(body_rows)}</tbody>" if body_rows else ""

        return f"<table>\n{thead}\n{tbody}\n</table>"

    def _parse_paragraph(self, lines: List[str], i: int) -> Tuple[str, int]:
        para_lines: List[str] = []
        j = i
        n = len(lines)

        while j < n:
            line = lines[j]
            if not line.strip():
                break
            if self._is_heading(line):
                break
            if self._is_horizontal_rule(line):
                break
            if self._is_code_block(line):
                break
            if self._is_blockquote(line):
                break
            if self._is_unordered_list_item(line) or self._is_ordered_list_item(line):
                break
            para_lines.append(line.strip())
            j += 1

        text = " ".join(para_lines)
        inline_text = self._parse_inline(text)
        return f"<p>{inline_text}</p>", j

    def _parse_inline(self, text: str) -> str:
        text = self._parse_images(text)
        text = self._parse_links(text)
        text = self._parse_inline_code(text)
        text = self._parse_bold(text)
        text = self._parse_italic(text)
        text = self._parse_line_breaks(text)
        return text

    def _parse_images(self, text: str) -> str:
        pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

        def replace(match: re.Match) -> str:
            alt_text = match.group(1)
            url = match.group(2)
            return f'<img src="{escape(url, quote=True)}" alt="{escape(alt_text, quote=True)}" />'

        return pattern.sub(replace, text)

    def _parse_links(self, text: str) -> str:
        pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

        def replace(match: re.Match) -> str:
            link_text = match.group(1)
            url = match.group(2)
            return f'<a href="{escape(url, quote=True)}">{link_text}</a>'

        return pattern.sub(replace, text)

    def _parse_inline_code(self, text: str) -> str:
        result: List[str] = []
        i = 0
        n = len(text)

        while i < n:
            if text[i] == "`":
                start = i
                i += 1
                while i < n and text[i] == "`":
                    i += 1
                fence_len = i - start

                code_start = i
                found_end = False
                while i < n:
                    if text[i] == "`":
                        end_fence_start = i
                        while i < n and text[i] == "`":
                            i += 1
                        if i - end_fence_start == fence_len:
                            found_end = True
                            break
                    else:
                        i += 1

                if found_end:
                    code = text[code_start:end_fence_start]
                    result.append(f"<code>{escape(code)}</code>")
                else:
                    result.append(text[start:i])
            else:
                result.append(text[i])
                i += 1

        return "".join(result)

    def _parse_bold(self, text: str) -> str:
        result: List[str] = []
        i = 0
        n = len(text)

        while i < n:
            if i + 1 < n and text[i:i+2] in ("**", "__"):
                marker = text[i:i+2]
                j = i + 2
                found = False
                while j < n - 1:
                    if text[j:j+2] == marker:
                        found = True
                        break
                    j += 1
                if found:
                    content = text[i+2:j]
                    result.append(f"<strong>{content}</strong>")
                    i = j + 2
                    continue
                result.append(text[i])
                i += 1
                continue

            result.append(text[i])
            i += 1

        return "".join(result)

    def _parse_italic(self, text: str) -> str:
        result: List[str] = []
        i = 0
        n = len(text)

        while i < n:
            ch = text[i]

            if ch in ("*", "_"):
                if i + 1 < n and text[i+1] == ch:
                    result.append(text[i:i+2])
                    i += 2
                    continue

                j = i + 1
                found = False
                while j < n:
                    if text[j] == ch:
                        if j + 1 < n and text[j+1] == ch:
                            j += 2
                            continue
                        found = True
                        break
                    j += 1

                if found and j > i + 1:
                    content = text[i+1:j]
                    result.append(f"<em>{content}</em>")
                    i = j + 1
                    continue

            result.append(ch)
            i += 1

        return "".join(result)

    def _parse_line_breaks(self, text: str) -> str:
        return text.replace("  \n", "<br />\n")
