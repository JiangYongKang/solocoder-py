from __future__ import annotations

from .models import ScriptType


CJK_RANGES: list[tuple[int, int]] = [
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x30000, 0x3134F),
    (0xF900, 0xFAFF),
    (0x2F800, 0x2FA1F),
]


LATIN_RANGES: list[tuple[int, int]] = [
    (0x0041, 0x005A),
    (0x0061, 0x007A),
    (0x00C0, 0x00FF),
    (0x0100, 0x017F),
    (0x0180, 0x024F),
    (0x0250, 0x02AF),
    (0x1E00, 0x1EFF),
    (0x2C60, 0x2C7F),
    (0xA720, 0xA7FF),
    (0xAB30, 0xAB6F),
    (0xFB00, 0xFB06),
    (0xFF21, 0xFF3A),
    (0xFF41, 0xFF5A),
]


CYRILLIC_RANGES: list[tuple[int, int]] = [
    (0x0400, 0x04FF),
    (0x0500, 0x052F),
    (0x2DE0, 0x2DFF),
    (0xA640, 0xA69F),
    (0x1C80, 0x1C8F),
]


ARABIC_RANGES: list[tuple[int, int]] = [
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
    (0x10E60, 0x10E7F),
]


THAI_RANGES: list[tuple[int, int]] = [
    (0x0E00, 0x0E7F),
]


DEVANAGARI_RANGES: list[tuple[int, int]] = [
    (0x0900, 0x097F),
    (0xA8E0, 0xA8FF),
    (0x11B00, 0x11B5F),
]


GREEK_RANGES: list[tuple[int, int]] = [
    (0x0370, 0x03FF),
    (0x1F00, 0x1FFF),
]


HEBREW_RANGES: list[tuple[int, int]] = [
    (0x0590, 0x05FF),
    (0xFB1D, 0xFB4F),
]


KATAKANA_RANGES: list[tuple[int, int]] = [
    (0x30A0, 0x30FF),
    (0x31F0, 0x31FF),
    (0xFF66, 0xFF9F),
    (0x1B000, 0x1B0FF),
]


HIRAGANA_RANGES: list[tuple[int, int]] = [
    (0x3040, 0x309F),
    (0x1B100, 0x1B12F),
]


HANGUL_RANGES: list[tuple[int, int]] = [
    (0xAC00, 0xD7AF),
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xFFA0, 0xFFDC),
    (0xD7B0, 0xD7FF),
]


PUNCTUATION_RANGES: list[tuple[int, int]] = [
    (0x0021, 0x002F),
    (0x003A, 0x0040),
    (0x005B, 0x0060),
    (0x007B, 0x007E),
    (0x2000, 0x206F),
    (0x20A0, 0x20CF),
    (0x2E00, 0x2E7F),
    (0x3000, 0x303F),
    (0xFF01, 0xFF0F),
    (0xFF1A, 0xFF20),
    (0xFF3B, 0xFF40),
    (0xFF5B, 0xFF65),
    (0xFE50, 0xFE6F),
    (0x00A1, 0x00BF),
]


NUMBER_RANGES: list[tuple[int, int]] = [
    (0x0030, 0x0039),
    (0x0660, 0x0669),
    (0x06F0, 0x06F9),
    (0x0966, 0x096F),
    (0x09E6, 0x09EF),
    (0x0A66, 0x0A6F),
    (0x0AE6, 0x0AEF),
    (0x0B66, 0x0B6F),
    (0x0BE6, 0x0BEF),
    (0x0C66, 0x0C6F),
    (0x0CE6, 0x0CEF),
    (0x0D66, 0x0D6F),
    (0x0E50, 0x0E59),
    (0x0ED0, 0x0ED9),
    (0x0F20, 0x0F29),
    (0x1040, 0x1049),
    (0x1090, 0x1099),
    (0x17E0, 0x17E9),
    (0x1810, 0x1819),
    (0x1946, 0x194F),
    (0x19D0, 0x19D9),
    (0x1A80, 0x1A89),
    (0x1A90, 0x1A99),
    (0x1B50, 0x1B59),
    (0x1BB0, 0x1BB9),
    (0x1C40, 0x1C49),
    (0x1C50, 0x1C59),
    (0xA620, 0xA629),
    (0xA8D0, 0xA8D9),
    (0xA900, 0xA909),
    (0xA9D0, 0xA9D9),
    (0xA9F0, 0xA9F9),
    (0xAA50, 0xAA59),
    (0xABF0, 0xABF9),
    (0xFF10, 0xFF19),
]


EMOJI_RANGES: list[tuple[int, int]] = [
    (0x1F300, 0x1F5FF),
    (0x1F600, 0x1F64F),
    (0x1F680, 0x1F6FF),
    (0x1F700, 0x1F77F),
    (0x1F780, 0x1F7FF),
    (0x1F800, 0x1F8FF),
    (0x1F900, 0x1F9FF),
    (0x1FA00, 0x1FA6F),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
    (0x2B00, 0x2BFF),
    (0x2300, 0x23FF),
    (0x1F000, 0x1F02F),
    (0x1F0A0, 0x1F0FF),
]


WHITESPACE_RANGES: list[tuple[int, int]] = [
    (0x0009, 0x000D),
    (0x0020, 0x0020),
    (0x0085, 0x0085),
    (0x00A0, 0x00A0),
    (0x1680, 0x1680),
    (0x2000, 0x200A),
    (0x2028, 0x2029),
    (0x202F, 0x202F),
    (0x205F, 0x205F),
    (0x3000, 0x3000),
]


SURROGATE_RANGES: list[tuple[int, int]] = [
    (0xD800, 0xDFFF),
]


VARIATION_SELECTOR_RANGES: list[tuple[int, int]] = [
    (0xFE00, 0xFE0F),
    (0xE0100, 0xE01EF),
]


def _in_ranges(codepoint: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _is_surrogate(codepoint: int) -> bool:
    return _in_ranges(codepoint, SURROGATE_RANGES)


def _is_variation_selector(codepoint: int) -> bool:
    return _in_ranges(codepoint, VARIATION_SELECTOR_RANGES)


def is_variation_selector(char: str) -> bool:
    if len(char) == 0:
        return False
    return _is_variation_selector(ord(char))


def detect_script(char: str) -> ScriptType:
    if len(char) == 0:
        return ScriptType.UNKNOWN

    codepoint = ord(char)

    if _is_surrogate(codepoint):
        return ScriptType.UNKNOWN

    if _is_variation_selector(codepoint):
        return ScriptType.UNKNOWN

    if _in_ranges(codepoint, WHITESPACE_RANGES):
        return ScriptType.WHITESPACE

    if _in_ranges(codepoint, PUNCTUATION_RANGES):
        return ScriptType.PUNCTUATION

    if _in_ranges(codepoint, NUMBER_RANGES):
        return ScriptType.NUMBER

    if _in_ranges(codepoint, EMOJI_RANGES):
        return ScriptType.EMOJI

    if _in_ranges(codepoint, CJK_RANGES):
        return ScriptType.CJK

    if _in_ranges(codepoint, KATAKANA_RANGES):
        return ScriptType.KATAKANA

    if _in_ranges(codepoint, HIRAGANA_RANGES):
        return ScriptType.HIRAGANA

    if _in_ranges(codepoint, HANGUL_RANGES):
        return ScriptType.HANGUL

    if _in_ranges(codepoint, LATIN_RANGES):
        return ScriptType.LATIN

    if _in_ranges(codepoint, CYRILLIC_RANGES):
        return ScriptType.CYRILLIC

    if _in_ranges(codepoint, ARABIC_RANGES):
        return ScriptType.ARABIC

    if _in_ranges(codepoint, THAI_RANGES):
        return ScriptType.THAI

    if _in_ranges(codepoint, DEVANAGARI_RANGES):
        return ScriptType.DEVANAGARI

    if _in_ranges(codepoint, GREEK_RANGES):
        return ScriptType.GREEK

    if _in_ranges(codepoint, HEBREW_RANGES):
        return ScriptType.HEBREW

    return ScriptType.UNKNOWN


def is_cjk(char: str) -> bool:
    if len(char) == 0:
        return False
    codepoint = ord(char)
    if _is_surrogate(codepoint):
        return False
    return _in_ranges(codepoint, CJK_RANGES)


def is_punctuation(char: str) -> bool:
    if len(char) == 0:
        return False
    codepoint = ord(char)
    if _is_surrogate(codepoint):
        return False
    return _in_ranges(codepoint, PUNCTUATION_RANGES)


def is_whitespace(char: str) -> bool:
    if len(char) == 0:
        return False
    codepoint = ord(char)
    if _is_surrogate(codepoint):
        return False
    return _in_ranges(codepoint, WHITESPACE_RANGES)


def is_number(char: str) -> bool:
    if len(char) == 0:
        return False
    codepoint = ord(char)
    if _is_surrogate(codepoint):
        return False
    return _in_ranges(codepoint, NUMBER_RANGES)


def is_emoji(char: str) -> bool:
    if len(char) == 0:
        return False
    codepoint = ord(char)
    if _is_surrogate(codepoint):
        return False
    return _in_ranges(codepoint, EMOJI_RANGES)


def is_surrogate(char: str) -> bool:
    if len(char) == 0:
        return False
    return _is_surrogate(ord(char))


def get_script_name(script: ScriptType) -> str:
    return script.value


def get_all_script_types() -> list[ScriptType]:
    return list(ScriptType)
