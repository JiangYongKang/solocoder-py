from __future__ import annotations

import pytest

from src.solocoder_py.masking import TokenizationConfig, TokenizationStrategy


class TestTokenizationStrategy:
    def test_same_value_generates_same_token(self):
        tokenizer = TokenizationStrategy()
        token1 = tokenizer.tokenize("张三")
        token2 = tokenizer.tokenize("张三")
        assert token1 == token2

    def test_different_values_generate_different_tokens(self):
        tokenizer = TokenizationStrategy()
        token1 = tokenizer.tokenize("张三")
        token2 = tokenizer.tokenize("李四")
        assert token1 != token2

    def test_token_has_prefix(self):
        config = TokenizationConfig(token_prefix="USER_", token_length=12)
        tokenizer = TokenizationStrategy(config)
        token = tokenizer.tokenize("张三")
        assert token.startswith("USER_")
        assert len(token) == len("USER_") + 12

    def test_token_length(self):
        config = TokenizationConfig(token_prefix="TKN_", token_length=16)
        tokenizer = TokenizationStrategy(config)
        token = tokenizer.tokenize("test_value")
        assert len(token) == len("TKN_") + 16

    def test_none_value_tokenization(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize(None)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_empty_string_tokenization(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize("")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_numeric_value_tokenization(self):
        tokenizer = TokenizationStrategy()
        token1 = tokenizer.tokenize(12345)
        token2 = tokenizer.tokenize("12345")
        assert token1 == token2

    def test_repeated_calls_consistency(self):
        tokenizer = TokenizationStrategy()
        value = "test@example.com"
        tokens = []
        for _ in range(10):
            tokens.append(tokenizer.tokenize(value))
        assert all(t == tokens[0] for t in tokens)

    def test_detokenize_returns_original_value(self):
        tokenizer = TokenizationStrategy()
        original = "张三"
        token = tokenizer.tokenize(original)
        detokenized = tokenizer.detokenize(token)
        assert detokenized == original

    def test_detokenize_none_value(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize(None)
        detokenized = tokenizer.detokenize(token)
        assert detokenized is None

    def test_detokenize_empty_string(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize("")
        detokenized = tokenizer.detokenize(token)
        assert detokenized == ""

    def test_detokenize_unknown_token(self):
        tokenizer = TokenizationStrategy()
        tokenizer.tokenize("known")
        result = tokenizer.detokenize("unknown_token")
        assert result is None

    def test_is_token(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize("test")
        assert tokenizer.is_token(token)
        assert not tokenizer.is_token("not_a_token")
        assert not tokenizer.is_token(123)

    def test_contains_operator(self):
        tokenizer = TokenizationStrategy()
        tokenizer.tokenize("test_value")
        assert "test_value" in tokenizer
        assert "not_in_tokenizer" not in tokenizer

    def test_clear_cache(self):
        tokenizer = TokenizationStrategy()
        tokenizer.tokenize("value1")
        tokenizer.tokenize("value2")
        assert tokenizer.get_token_count() == 2

        tokenizer.clear()
        assert tokenizer.get_token_count() == 0

        token1 = tokenizer.tokenize("value1")
        token2 = tokenizer.tokenize("value1")
        assert token1 == token2

    def test_get_token_count(self):
        tokenizer = TokenizationStrategy()
        assert tokenizer.get_token_count() == 0

        tokenizer.tokenize("value1")
        assert tokenizer.get_token_count() == 1

        tokenizer.tokenize("value1")
        assert tokenizer.get_token_count() == 1

        tokenizer.tokenize("value2")
        assert tokenizer.get_token_count() == 2

    def test_callable_interface(self):
        tokenizer = TokenizationStrategy()
        token1 = tokenizer("test")
        token2 = tokenizer.tokenize("test")
        assert token1 == token2

    def test_different_secrets_generate_different_tokens(self):
        secret1 = b"secret_key_1"
        secret2 = b"secret_key_2"

        tokenizer1 = TokenizationStrategy(secret_key=secret1)
        tokenizer2 = TokenizationStrategy(secret_key=secret2)

        value = "same_value"
        token1 = tokenizer1.tokenize(value)
        token2 = tokenizer2.tokenize(value)

        assert token1 != token2

    def test_same_secret_generates_same_tokens(self):
        secret = b"same_secret_key"
        tokenizer1 = TokenizationStrategy(secret_key=secret)
        tokenizer2 = TokenizationStrategy(secret_key=secret)

        value = "test_value"
        token1 = tokenizer1.tokenize(value)
        token2 = tokenizer2.tokenize(value)

        assert token1 == token2

    def test_random_token_mode(self):
        config = TokenizationConfig(use_hash=False)
        tokenizer = TokenizationStrategy(config)

        token1 = tokenizer.tokenize("value1")
        token2 = tokenizer.tokenize("value1")
        assert token1 == token2

        token3 = tokenizer.tokenize("value2")
        assert token1 != token3

    def test_token_not_reversible(self):
        tokenizer = TokenizationStrategy()
        token = tokenizer.tokenize("sensitive_data")

        assert token != "sensitive_data"
        assert "sensitive" not in token.lower()
        assert "data" not in token.lower()

    def test_large_number_of_unique_tokens(self):
        tokenizer = TokenizationStrategy()
        tokens = set()
        for i in range(1000):
            token = tokenizer.tokenize(f"user_{i}")
            tokens.add(token)

        assert len(tokens) == 1000

    def test_unicode_characters(self):
        tokenizer = TokenizationStrategy()
        unicode_values = ["张三", "🎉🎊", "日本語", "العربية", "🚀"]

        for value in unicode_values:
            token = tokenizer.tokenize(value)
            assert token is not None
            assert tokenizer.detokenize(token) == value

    def test_special_characters(self):
        tokenizer = TokenizationStrategy()
        special_values = [
            "test@example.com",
            "user+tag@domain.co.uk",
            "pass!@#$%^&*()",
            "path/to/file.txt",
            "value with spaces",
        ]

        for value in special_values:
            token1 = tokenizer.tokenize(value)
            token2 = tokenizer.tokenize(value)
            assert token1 == token2
            assert tokenizer.detokenize(token1) == value

    def test_tokenization_config_validation(self):
        with pytest.raises(ValueError, match="token_length must be at least 8"):
            TokenizationConfig(token_length=5)
