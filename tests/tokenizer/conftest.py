import pytest

from solocoder_py.tokenizer import UnicodeTokenizer


@pytest.fixture
def tokenizer() -> UnicodeTokenizer:
    return UnicodeTokenizer()


@pytest.fixture
def tokenizer_no_punctuation() -> UnicodeTokenizer:
    return UnicodeTokenizer(include_punctuation=False)


@pytest.fixture
def tokenizer_with_whitespace() -> UnicodeTokenizer:
    return UnicodeTokenizer(include_whitespace=True)


@pytest.fixture
def sample_chinese_text() -> str:
    return "我爱北京天安门"


@pytest.fixture
def sample_english_text() -> str:
    return "Hello World from Unicode Tokenizer"


@pytest.fixture
def sample_mixed_text() -> str:
    return "你好，世界！Hello, World! 这是一个测试。"


@pytest.fixture
def sample_punctuation_text() -> str:
    return "，。！？、；：""''（）【】《》"


@pytest.fixture
def long_cjk_text() -> str:
    return "中" * 1000
