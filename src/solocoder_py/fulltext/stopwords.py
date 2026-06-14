from __future__ import annotations

import re


_EN_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "of", "as", "so", "than", "too", "very", "s", "t", "just", "don",
    "should", "now", "will", "would", "could", "should", "may", "might",
    "can", "shall", "must", "need", "dare", "ought", "used",
    "there", "here", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "also", "because", "until",
    "while", "although", "though", "whether", "either", "neither",
})


_CN_STOPWORDS = frozenset({
    "的", "了", "和", "是", "在", "我", "有", "他", "也", "不",
    "就", "都", "而", "及", "与", "着", "或", "一个", "没有", "我们",
    "你们", "他们", "她们", "它们", "自己", "这", "那", "这个", "那个",
    "这些", "那些", "什么", "怎么", "为什么", "如何", "哪里", "哪个",
    "谁", "多少", "几", "些", "每", "各", "某", "该", "此", "其",
    "之", "于", "以", "及", "为", "因", "由", "从", "到", "向",
    "对", "给", "把", "被", "让", "使", "将", "把", "比", "跟",
    "同", "和", "与", "及", "并", "且", "或", "而", "但", "却",
    "只", "仅", "才", "就", "便", "又", "再", "还", "也", "都",
    "全", "总", "共", "已", "曾", "正", "在", "将", "要", "会",
    "能", "可以", "应该", "必须", "得", "地", "过", "来", "去",
    "上", "下", "左", "右", "前", "后", "里", "外", "中", "间",
    "内", "旁", "边", "面", "头", "尾", "第", "啊", "呀", "呢",
    "吧", "吗", "哦", "嗯", "哈", "唉", "咦", "喔", "呗", "嘛",
})


def _is_all_ascii(word: str) -> bool:
    return all(ord(c) < 128 for c in word)


def _is_any_cjk(word: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in word)


class StopWords:
    def __init__(self, extra_stopwords: set[str] | None = None) -> None:
        self._stopwords: set[str] = set(_EN_STOPWORDS) | set(_CN_STOPWORDS)
        if extra_stopwords:
            self._stopwords.update(extra_stopwords)
        self._rebuild_multi_char_pattern()

    def _rebuild_multi_char_pattern(self) -> None:
        multi_char = sorted(
            [w for w in self._stopwords if len(w) > 1],
            key=len,
            reverse=True,
        )
        if not multi_char:
            self._ascii_pattern = None
            self._cjk_pattern = None
            return

        ascii_words = [w for w in multi_char if _is_all_ascii(w)]
        cjk_words = [w for w in multi_char if _is_any_cjk(w)]

        if ascii_words:
            escaped_ascii = [re.escape(w) for w in ascii_words]
            ascii_alt = "|".join(escaped_ascii)
            self._ascii_pattern = re.compile(
                r"(?i)(?<![A-Za-z0-9'])(?:" + ascii_alt + r")(?![A-Za-z0-9'])"
            )
        else:
            self._ascii_pattern = None

        if cjk_words:
            escaped_cjk = [re.escape(w) for w in cjk_words]
            self._cjk_pattern = re.compile("|".join(escaped_cjk))
        else:
            self._cjk_pattern = None

    def preprocess_text(self, text: str) -> str:
        if not text:
            return text
        result = text
        if self._cjk_pattern is not None:
            result = self._cjk_pattern.sub(
                lambda m: " " * len(m.group(0)),
                result,
            )
        if self._ascii_pattern is not None:
            result = self._ascii_pattern.sub(
                lambda m: " " * len(m.group(0)),
                result,
            )
        return result

    def is_stopword(self, term: str) -> bool:
        return term.lower() in self._stopwords

    def add(self, term: str) -> None:
        self._stopwords.add(term.lower())
        self._rebuild_multi_char_pattern()

    def remove(self, term: str) -> None:
        lowered = term.lower()
        if lowered in self._stopwords:
            self._stopwords.remove(lowered)
            self._rebuild_multi_char_pattern()

    def filter(self, terms: list[str]) -> list[str]:
        return [t for t in terms if not self.is_stopword(t)]

    def filter_tokens(
        self, tokens: list[tuple[str, int]]
    ) -> list[tuple[str, int]]:
        return [(t, pos) for t, pos in tokens if not self.is_stopword(t)]

    @property
    def stopwords(self) -> frozenset[str]:
        return frozenset(self._stopwords)
