from __future__ import annotations

import pytest

from solocoder_py.summarizer import TextSummarizer, SummarizerConfig


@pytest.fixture
def default_summarizer() -> TextSummarizer:
    return TextSummarizer()


@pytest.fixture
def config() -> SummarizerConfig:
    return SummarizerConfig()
