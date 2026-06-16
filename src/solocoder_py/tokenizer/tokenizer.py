from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .exceptions import EmptyInputError, InvalidTextError
from .models import ScriptType, Token, TokenizationResult
from .scripts import (
    detect_script,
    is_cjk,
    is_emoji,
    is_number,
    is_punctuation,
    is_surrogate,
    is_variation_selector,
    is_whitespace,
)


TokenizationRule = Callable[[str, int], Optional[tuple[str, ScriptType, int]]]


@dataclass
class ScriptRuleSet:
    script: ScriptType
    split_by_single_char: bool = False
    split_on_whitespace: bool = True
    split_on_punctuation: bool = True
    merge_consecutive_same_script: bool = True
    custom_rule: Optional[TokenizationRule] = None


DEFAULT_RULE_SETS: dict[ScriptType, ScriptRuleSet] = {
    ScriptType.CJK: ScriptRuleSet(
        script=ScriptType.CJK,
        split_by_single_char=True,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=False,
    ),
    ScriptType.LATIN: ScriptRuleSet(
        script=ScriptType.LATIN,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.CYRILLIC: ScriptRuleSet(
        script=ScriptType.CYRILLIC,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.ARABIC: ScriptRuleSet(
        script=ScriptType.ARABIC,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.THAI: ScriptRuleSet(
        script=ScriptType.THAI,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.DEVANAGARI: ScriptRuleSet(
        script=ScriptType.DEVANAGARI,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.GREEK: ScriptRuleSet(
        script=ScriptType.GREEK,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.HEBREW: ScriptRuleSet(
        script=ScriptType.HEBREW,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.KATAKANA: ScriptRuleSet(
        script=ScriptType.KATAKANA,
        split_by_single_char=True,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=False,
    ),
    ScriptType.HIRAGANA: ScriptRuleSet(
        script=ScriptType.HIRAGANA,
        split_by_single_char=True,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=False,
    ),
    ScriptType.HANGUL: ScriptRuleSet(
        script=ScriptType.HANGUL,
        split_by_single_char=True,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=False,
    ),
    ScriptType.NUMBER: ScriptRuleSet(
        script=ScriptType.NUMBER,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
    ScriptType.EMOJI: ScriptRuleSet(
        script=ScriptType.EMOJI,
        split_by_single_char=True,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=False,
    ),
    ScriptType.UNKNOWN: ScriptRuleSet(
        script=ScriptType.UNKNOWN,
        split_by_single_char=False,
        split_on_whitespace=True,
        split_on_punctuation=True,
        merge_consecutive_same_script=True,
    ),
}


@dataclass
class UnicodeTokenizer:
    rule_sets: dict[ScriptType, ScriptRuleSet] = field(default_factory=lambda: dict(DEFAULT_RULE_SETS))
    include_whitespace: bool = False
    include_punctuation: bool = True
    normalize_unicode: bool = True

    def get_rule_set(self, script: ScriptType) -> ScriptRuleSet:
        return self.rule_sets.get(script, DEFAULT_RULE_SETS[ScriptType.UNKNOWN])

    def add_rule_set(self, rule_set: ScriptRuleSet) -> None:
        self.rule_sets[rule_set.script] = rule_set

    def tokenize(self, text: str) -> TokenizationResult:
        start_time = time.perf_counter()

        if text is None:
            raise InvalidTextError("Input text cannot be None")

        if not isinstance(text, str):
            raise InvalidTextError(f"Input must be a string, got {type(text).__name__}")

        if len(text) == 0:
            return TokenizationResult(
                tokens=[],
                original_text="",
                detected_scripts=set(),
                duration_ms=0.0,
            )

        tokens: list[Token] = []
        detected_scripts: set[ScriptType] = set()
        i = 0
        n = len(text)

        def _is_boundary_script(script: ScriptType) -> bool:
            return script in (
                ScriptType.WHITESPACE,
                ScriptType.PUNCTUATION,
                ScriptType.NUMBER,
                ScriptType.EMOJI,
                ScriptType.CJK,
                ScriptType.KATAKANA,
                ScriptType.HIRAGANA,
                ScriptType.HANGUL,
                ScriptType.UNKNOWN,
            )

        def _should_break_on_script_change(
            current_script: ScriptType,
            next_script: ScriptType,
            rule_set: ScriptRuleSet,
        ) -> bool:
            if next_script == current_script:
                return False

            if _is_boundary_script(next_script):
                return True

            if _is_boundary_script(current_script):
                return True

            if not rule_set.merge_consecutive_same_script:
                return True

            return False

        while i < n:
            char = text[i]

            if is_surrogate(char):
                i += 1
                continue

            if is_variation_selector(char):
                i += 1
                continue

            script = detect_script(char)
            detected_scripts.add(script)

            if script == ScriptType.WHITESPACE:
                if self.include_whitespace:
                    tokens.append(Token(
                        text=char,
                        script=script,
                        start=i,
                        end=i + 1,
                    ))
                i += 1
                continue

            if script == ScriptType.PUNCTUATION:
                if self.include_punctuation:
                    tokens.append(Token(
                        text=char,
                        script=script,
                        start=i,
                        end=i + 1,
                    ))
                i += 1
                continue

            rule_set = self.get_rule_set(script)

            if rule_set.split_by_single_char:
                tokens.append(Token(
                    text=char,
                    script=script,
                    start=i,
                    end=i + 1,
                ))
                i += 1
                continue

            start = i
            current_script = script

            while i < n:
                next_char = text[i]

                if is_surrogate(next_char):
                    break

                if is_variation_selector(next_char):
                    i += 1
                    continue

                next_script = detect_script(next_char)

                if next_script == ScriptType.WHITESPACE:
                    break

                if next_script == ScriptType.PUNCTUATION:
                    break

                if next_script != current_script:
                    if _should_break_on_script_change(current_script, next_script, rule_set):
                        break
                    current_script = next_script
                    detected_scripts.add(next_script)

                i += 1

            token_text = text[start:i]
            if token_text:
                tokens.append(Token(
                    text=token_text,
                    script=script,
                    start=start,
                    end=i,
                    metadata={"merged_scripts": [script, current_script]} if script != current_script else {},
                ))

        duration_ms = (time.perf_counter() - start_time) * 1000

        return TokenizationResult(
            tokens=tokens,
            original_text=text,
            detected_scripts=detected_scripts,
            duration_ms=duration_ms,
        )

    def tokenize_to_strings(self, text: str) -> list[str]:
        result = self.tokenize(text)
        return result.to_strings()

    def detect_dominant_script(self, text: str) -> ScriptType:
        if not text:
            return ScriptType.UNKNOWN

        script_counts: dict[ScriptType, int] = {}

        for char in text:
            if is_surrogate(char) or is_whitespace(char):
                continue

            script = detect_script(char)
            if script in (ScriptType.PUNCTUATION, ScriptType.NUMBER, ScriptType.EMOJI):
                continue

            script_counts[script] = script_counts.get(script, 0) + 1

        if not script_counts:
            return ScriptType.UNKNOWN

        return max(script_counts.items(), key=lambda x: x[1])[0]


def tokenize(text: str) -> TokenizationResult:
    tokenizer = UnicodeTokenizer()
    return tokenizer.tokenize(text)


def tokenize_to_strings(text: str) -> list[str]:
    tokenizer = UnicodeTokenizer()
    return tokenizer.tokenize_to_strings(text)
