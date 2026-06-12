from __future__ import annotations

import pytest

from solocoder_py.basecodec import (
    Base16Decoder,
    Base16Encoder,
    Base32Decoder,
    Base32Encoder,
    Base64Decoder,
    Base64Encoder,
    InvalidCharacterError,
    InvalidLengthError,
    InvalidPaddingError,
    TruncatedInputError,
    b16decode,
    b16encode,
    b32decode,
    b32encode,
    b64decode,
    b64encode,
)


class TestBase64NormalFlow:
    def test_encode_decode_consistency(self):
        data = b"Hello, World!"
        encoded = b64encode(data)
        decoded = b64decode(encoded)
        assert decoded == data

    def test_encode_known_value(self):
        assert b64encode(b"") == ""
        assert b64encode(b"f") == "Zg=="
        assert b64encode(b"fo") == "Zm8="
        assert b64encode(b"foo") == "Zm9v"
        assert b64encode(b"foob") == "Zm9vYg=="
        assert b64encode(b"fooba") == "Zm9vYmE="
        assert b64encode(b"foobar") == "Zm9vYmFy"

    def test_decode_known_value(self):
        assert b64decode("") == b""
        assert b64decode("Zg==") == b"f"
        assert b64decode("Zm8=") == b"fo"
        assert b64decode("Zm9v") == b"foo"
        assert b64decode("Zm9vYg==") == b"foob"
        assert b64decode("Zm9vYmE=") == b"fooba"
        assert b64decode("Zm9vYmFy") == b"foobar"

    def test_streaming_encode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoder = Base64Encoder()
        chunks = [data[i : i + 5] for i in range(0, len(data), 5)]
        for chunk in chunks:
            encoder.update(chunk)
        result = encoder.finalize()
        assert result == b64encode(data)

    def test_streaming_decode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoded = b64encode(data)
        decoder = Base64Decoder()
        chunks = [encoded[i : i + 7] for i in range(0, len(encoded), 7)]
        for chunk in chunks:
            decoder.update(chunk)
        result = decoder.finalize()
        assert result == data

    def test_binary_data(self):
        data = bytes(range(256))
        encoded = b64encode(data)
        decoded = b64decode(encoded)
        assert decoded == data

    def test_large_data(self):
        data = b"x" * 10000
        encoded = b64encode(data)
        decoded = b64decode(encoded)
        assert decoded == data


class TestBase32NormalFlow:
    def test_encode_decode_consistency(self):
        data = b"Hello, World!"
        encoded = b32encode(data)
        decoded = b32decode(encoded)
        assert decoded == data

    def test_encode_known_value(self):
        assert b32encode(b"") == ""
        assert b32encode(b"f") == "MY======"
        assert b32encode(b"fo") == "MZXQ===="
        assert b32encode(b"foo") == "MZXW6==="
        assert b32encode(b"foob") == "MZXW6YQ="
        assert b32encode(b"fooba") == "MZXW6YTB"
        assert b32encode(b"foobar") == "MZXW6YTBOI======"

    def test_decode_known_value(self):
        assert b32decode("") == b""
        assert b32decode("MY======") == b"f"
        assert b32decode("MZXQ====") == b"fo"
        assert b32decode("MZXW6===") == b"foo"
        assert b32decode("MZXW6YQ=") == b"foob"
        assert b32decode("MZXW6YTB") == b"fooba"
        assert b32decode("MZXW6YTBOI======") == b"foobar"

    def test_streaming_encode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoder = Base32Encoder()
        chunks = [data[i : i + 3] for i in range(0, len(data), 3)]
        for chunk in chunks:
            encoder.update(chunk)
        result = encoder.finalize()
        assert result == b32encode(data)

    def test_streaming_decode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoded = b32encode(data)
        decoder = Base32Decoder()
        chunks = [encoded[i : i + 5] for i in range(0, len(encoded), 5)]
        for chunk in chunks:
            decoder.update(chunk)
        result = decoder.finalize()
        assert result == data

    def test_binary_data(self):
        data = bytes(range(256))
        encoded = b32encode(data)
        decoded = b32decode(encoded)
        assert decoded == data


class TestBase16NormalFlow:
    def test_encode_decode_consistency(self):
        data = b"Hello, World!"
        encoded = b16encode(data)
        decoded = b16decode(encoded)
        assert decoded == data

    def test_encode_known_value(self):
        assert b16encode(b"") == ""
        assert b16encode(b"f") == "66"
        assert b16encode(b"fo") == "666F"
        assert b16encode(b"foo") == "666F6F"
        assert b16encode(b"\x00\x01\x02\xFE\xFF") == "000102FEFF"

    def test_decode_known_value(self):
        assert b16decode("") == b""
        assert b16decode("66") == b"f"
        assert b16decode("666F") == b"fo"
        assert b16decode("666F6F") == b"foo"
        assert b16decode("000102FEFF") == b"\x00\x01\x02\xFE\xFF"

    def test_streaming_encode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoder = Base16Encoder()
        chunks = [data[i : i + 1] for i in range(len(data))]
        for chunk in chunks:
            encoder.update(chunk)
        result = encoder.finalize()
        assert result == b16encode(data)

    def test_streaming_decode(self):
        data = b"The quick brown fox jumps over the lazy dog"
        encoded = b16encode(data)
        decoder = Base16Decoder()
        chunks = [encoded[i : i + 2] for i in range(0, len(encoded), 2)]
        for chunk in chunks:
            decoder.update(chunk)
        result = decoder.finalize()
        assert result == data

    def test_binary_data(self):
        data = bytes(range(256))
        encoded = b16encode(data)
        decoded = b16decode(encoded)
        assert decoded == data


class TestNoPaddingMode:
    def test_base64_no_padding(self):
        assert b64encode(b"f", pad=False) == "Zg"
        assert b64encode(b"fo", pad=False) == "Zm8"
        assert b64encode(b"foo", pad=False) == "Zm9v"
        assert b64decode("Zg", pad=False) == b"f"
        assert b64decode("Zm8", pad=False) == b"fo"
        assert b64decode("Zm9v", pad=False) == b"foo"

    def test_base64_no_padding_consistency(self):
        data = b"Test data with various lengths"
        encoded = b64encode(data, pad=False)
        decoded = b64decode(encoded, pad=False)
        assert decoded == data
        assert "=" not in encoded

    def test_base32_no_padding(self):
        assert b32encode(b"f", pad=False) == "MY"
        assert b32encode(b"fo", pad=False) == "MZXQ"
        assert b32encode(b"foo", pad=False) == "MZXW6"
        assert b32encode(b"fooba", pad=False) == "MZXW6YTB"
        assert b32decode("MY", pad=False) == b"f"
        assert b32decode("MZXQ", pad=False) == b"fo"
        assert b32decode("MZXW6", pad=False) == b"foo"
        assert b32decode("MZXW6YTB", pad=False) == b"fooba"

    def test_base32_no_padding_consistency(self):
        data = b"Test data with various lengths"
        encoded = b32encode(data, pad=False)
        decoded = b32decode(encoded, pad=False)
        assert decoded == data
        assert "=" not in encoded

    def test_base16_no_padding(self):
        data = b"Test data"
        encoded = b16encode(data, pad=False)
        decoded = b16decode(encoded, pad=False)
        assert decoded == data
        assert "=" not in encoded

    def test_streaming_no_padding(self):
        data = b"Streaming test with no padding mode"
        encoder = Base64Encoder(pad=False)
        for i in range(0, len(data), 2):
            encoder.update(data[i : i + 2])
        encoded = encoder.finalize()
        decoder = Base64Decoder(pad=False)
        for i in range(0, len(encoded), 3):
            decoder.update(encoded[i : i + 3])
        decoded = decoder.finalize()
        assert decoded == data
        assert "=" not in encoded


class TestLineWidthControl:
    def test_base64_line_width_76(self):
        data = b"x" * 100
        encoded = b64encode(data, line_width=76)
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        assert len(lines[-1]) <= 76
        decoded = b64decode(encoded)
        assert decoded == data

    def test_base64_line_width_exact_multiple(self):
        data = b"x" * 57
        encoded = b64encode(data, line_width=76)
        lines = encoded.split("\n")
        assert len(lines) == 2
        assert len(lines[0]) == 76
        assert len(lines[1]) == 0 or len(lines[1]) <= 76

    def test_base64_decode_with_newlines(self):
        encoded = "SGVsbG8s\nIFdvcmxk\nIQ=="
        decoded = b64decode(encoded)
        assert decoded == b"Hello, World!"

    def test_base64_decode_with_whitespace(self):
        encoded = "SGVs bG8s \t IFdv \r\n cmxkIQ=="
        decoded = b64decode(encoded)
        assert decoded == b"Hello, World!"

    def test_line_width_zero_no_wrap(self):
        data = b"x" * 100
        encoded = b64encode(data, line_width=0)
        assert "\n" not in encoded
        decoded = b64decode(encoded)
        assert decoded == data

    def test_custom_newline(self):
        data = b"x" * 100
        encoded = b64encode(data, line_width=76, newline="\r\n")
        assert "\r\n" in encoded
        assert "\n" not in encoded.replace("\r\n", "")
        decoded = b64decode(encoded)
        assert decoded == data

    def test_streaming_encode_with_line_width(self):
        data = b"x" * 200
        encoder = Base64Encoder(line_width=76)
        chunks = [data[i : i + 10] for i in range(0, len(data), 10)]
        for chunk in chunks:
            encoder.update(chunk)
        encoded = encoder.finalize()
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        decoded = b64decode(encoded)
        assert decoded == data

    def test_base32_line_width_76(self):
        data = b"x" * 100
        encoded = b32encode(data, line_width=76)
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        assert len(lines[-1]) <= 76
        decoded = b32decode(encoded)
        assert decoded == data

    def test_base32_line_width_exact_multiple(self):
        data = b"x" * 95
        encoded = b32encode(data, line_width=76)
        lines = encoded.split("\n")
        assert len(lines) >= 2
        assert len(lines[0]) == 76
        decoded = b32decode(encoded)
        assert decoded == data

    def test_base32_decode_with_newlines(self):
        data = b"Hello, World!"
        encoded = b32encode(data, line_width=8)
        assert "\n" in encoded
        decoded = b32decode(encoded)
        assert decoded == data

    def test_base32_line_width_zero_no_wrap(self):
        data = b"x" * 100
        encoded = b32encode(data, line_width=0)
        assert "\n" not in encoded
        decoded = b32decode(encoded)
        assert decoded == data

    def test_base32_streaming_encode_with_line_width(self):
        data = b"x" * 200
        encoder = Base32Encoder(line_width=76)
        chunks = [data[i : i + 10] for i in range(0, len(data), 10)]
        for chunk in chunks:
            encoder.update(chunk)
        encoded = encoder.finalize()
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        decoded = b32decode(encoded)
        assert decoded == data

    def test_base16_line_width_76(self):
        data = b"x" * 100
        encoded = b16encode(data, line_width=76)
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        assert len(lines[-1]) <= 76
        decoded = b16decode(encoded)
        assert decoded == data

    def test_base16_line_width_exact_multiple(self):
        data = b"x" * 152
        encoded = b16encode(data, line_width=76)
        lines = encoded.split("\n")
        assert len(lines) >= 2
        for line in lines[:-1]:
            assert len(line) == 76
        assert len(lines[-1]) <= 76
        decoded = b16decode(encoded)
        assert decoded == data

    def test_base16_decode_with_newlines(self):
        data = b"Hello, World!"
        encoded = b16encode(data, line_width=8)
        assert "\n" in encoded
        decoded = b16decode(encoded)
        assert decoded == data

    def test_base16_line_width_zero_no_wrap(self):
        data = b"x" * 100
        encoded = b16encode(data, line_width=0)
        assert "\n" not in encoded
        decoded = b16decode(encoded)
        assert decoded == data

    def test_base16_streaming_encode_with_line_width(self):
        data = b"x" * 200
        encoder = Base16Encoder(line_width=76)
        chunks = [data[i : i + 10] for i in range(0, len(data), 10)]
        for chunk in chunks:
            encoder.update(chunk)
        encoded = encoder.finalize()
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 76
        decoded = b16decode(encoded)
        assert decoded == data

    def test_base64_no_padding_with_line_width(self):
        data = b"Base64 block is 3 bytes -> 4 chars, so use 3*N length!"
        assert len(data) % 3 == 0 or (len(data) % 3) != 0
        encoded = b64encode(data, pad=False, line_width=24)
        assert "\n" in encoded
        assert "=" not in encoded
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 24
        decoded = b64decode(encoded, pad=False)
        assert decoded == data

    def test_base32_no_padding_with_line_width(self):
        data = b"Base32 block=5bytes->8chars, padding needed often here!"
        assert len(data) % 5 == 0 or (len(data) % 5) != 0
        encoded = b32encode(data, pad=False, line_width=32)
        assert "\n" in encoded
        assert "=" not in encoded
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 32
        decoded = b32decode(encoded, pad=False)
        assert decoded == data

    def test_base16_no_padding_with_line_width(self):
        data = b"Base16 encodes each byte as two hex digits, 1:2 ratio always works cleanly."
        assert len(data) % 1 == 0
        encoded = b16encode(data, pad=False, line_width=30)
        assert "\n" in encoded
        assert "=" not in encoded
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 30
        decoded = b16decode(encoded, pad=False)
        assert decoded == data

    def test_streaming_no_padding_with_line_width(self):
        data = b"x" * 300
        encoder = Base64Encoder(pad=False, line_width=40)
        chunks = [data[i : i + 17] for i in range(0, len(data), 17)]
        for chunk in chunks:
            encoder.update(chunk)
        encoded = encoder.finalize()
        assert "\n" in encoded
        assert "=" not in encoded
        lines = encoded.split("\n")
        for line in lines[:-1]:
            assert len(line) == 40
        for split_len in [1, 2, 3, 4, 5, 39, 40, 41, 53, 79, 80, 81]:
            decoder = Base64Decoder(pad=False)
            encoded_chunks = [
                encoded[i : i + split_len]
                for i in range(0, len(encoded), split_len)
            ]
            for chunk in encoded_chunks:
                decoder.update(chunk)
            decoded = decoder.finalize()
            assert decoded == data, f"Failed for split_len={split_len}"


class TestBoundaryConditions:
    def test_empty_byte_stream(self):
        assert b64encode(b"") == ""
        assert b64decode("") == b""
        assert b32encode(b"") == ""
        assert b32decode("") == b""
        assert b16encode(b"") == ""
        assert b16decode("") == b""

    def test_single_byte_input(self):
        for b in range(256):
            data = bytes([b])
            assert b64decode(b64encode(data)) == data
            assert b32decode(b32encode(data)) == data
            assert b16decode(b16encode(data)) == data

    def test_base64_exact_3_bytes_no_padding(self):
        data = b"abc"
        encoded = b64encode(data)
        assert "=" not in encoded
        assert len(encoded) == 4
        assert b64decode(encoded) == data

    def test_base32_exact_5_bytes_no_padding(self):
        data = b"abcde"
        encoded = b32encode(data)
        assert "=" not in encoded
        assert len(encoded) == 8
        assert b32decode(encoded) == data

    def test_base16_always_no_padding_needed(self):
        for length in range(10):
            data = b"x" * length
            encoded = b16encode(data)
            assert "=" not in encoded
            assert b16decode(encoded) == data

    def test_decode_with_newlines_and_spaces(self):
        data = b"Test data with whitespace in encoding"
        encoded = b64encode(data, line_width=10)
        decoded = b64decode(encoded)
        assert decoded == data

    def test_line_width_exact_divisor(self):
        data = b"A" * 57
        encoded = b64encode(data, line_width=76)
        lines = encoded.split("\n")
        assert len(lines) == 2
        assert len(lines[0]) == 76
        assert lines[1] == ""
        decoded = b64decode(encoded)
        assert decoded == data

    def test_all_possible_base64_chars(self):
        data = bytes([0, 0, 0, 255, 255, 255])
        encoded = b64encode(data)
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in encoded)
        decoded = b64decode(encoded)
        assert decoded == data

    def test_all_possible_base32_chars(self):
        data = bytes([0, 0, 0, 0, 0, 255, 255, 255, 255, 255])
        encoded = b32encode(data)
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in encoded)
        decoded = b32decode(encoded)
        assert decoded == data


class TestExceptionCases:
    def test_base64_invalid_character(self):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            b64decode("Invalid!Chars")

    def test_base32_invalid_character(self):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            b32decode("01!Invalid")

    def test_base16_invalid_character(self):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            b16decode("GG")

    def test_base32_invalid_chars_0189(self):
        for invalid_char in ["0", "1", "8", "9"]:
            with pytest.raises(InvalidCharacterError, match="Invalid character"):
                b32decode(invalid_char * 8)

    def test_base16_invalid_chars_G_Z(self):
        for invalid_char in ["G", "H", "Z", "g", "z"]:
            with pytest.raises(InvalidCharacterError, match="Invalid character"):
                b16decode(invalid_char * 2)

    def test_truncated_base64_input(self):
        with pytest.raises(InvalidLengthError, match="Invalid input length"):
            b64decode("ABC")

    def test_truncated_base32_input(self):
        with pytest.raises(InvalidLengthError, match="Invalid input length"):
            b32decode("ABCDE")

    def test_invalid_padding_too_many(self):
        with pytest.raises(InvalidPaddingError, match="Invalid padding"):
            b64decode("=====")

    def test_invalid_padding_wrong_position(self):
        with pytest.raises(InvalidCharacterError, match="Invalid character"):
            b64decode("=ABCDEFG")

    def test_invalid_padding_length(self):
        with pytest.raises(InvalidPaddingError, match="Invalid input length with padding"):
            b64decode("ABC=")

    def test_no_padding_invalid_length(self):
        with pytest.raises(TruncatedInputError, match="Truncated input"):
            b64decode("AB", pad=False)

    def test_no_padding_base32_invalid_length(self):
        with pytest.raises(TruncatedInputError, match="Truncated input"):
            b32decode("ABCDEFG", pad=False)

    def test_no_padding_base16_invalid_length(self):
        with pytest.raises(TruncatedInputError, match="Truncated input"):
            b16decode("A", pad=False)

    def test_invalid_line_width_negative(self):
        with pytest.raises(ValueError, match="line_width must be non-negative"):
            Base64Encoder(line_width=-1)

    def test_encoder_double_finalize(self):
        encoder = Base64Encoder()
        encoder.update(b"test")
        encoder.finalize()
        with pytest.raises(RuntimeError, match="Encoder has already been finalized"):
            encoder.finalize()

    def test_decoder_double_finalize(self):
        decoder = Base64Decoder()
        decoder.update("dGVzdA==")
        decoder.finalize()
        with pytest.raises(RuntimeError, match="Decoder has already been finalized"):
            decoder.finalize()

    def test_encoder_update_after_finalize(self):
        encoder = Base64Encoder()
        encoder.finalize()
        with pytest.raises(RuntimeError, match="Encoder has already been finalized"):
            encoder.update(b"test")

    def test_decoder_update_after_finalize(self):
        decoder = Base64Decoder()
        decoder.finalize()
        with pytest.raises(RuntimeError, match="Decoder has already been finalized"):
            decoder.update("test")

    def test_encoder_wrong_input_type(self):
        encoder = Base64Encoder()
        with pytest.raises(TypeError, match="data must be bytes-like"):
            encoder.update("not bytes")

    def test_decoder_wrong_input_type(self):
        decoder = Base64Decoder()
        with pytest.raises(TypeError, match="data must be a string"):
            decoder.update(b"not string")


class TestStreamingEdgeCases:
    def test_streaming_single_byte_chunks(self):
        data = bytes(range(100))
        encoder = Base64Encoder()
        for b in data:
            encoder.update(bytes([b]))
        encoded = encoder.finalize()
        decoder = Base64Decoder()
        for c in encoded:
            decoder.update(c)
        decoded = decoder.finalize()
        assert decoded == data

    def test_streaming_with_reset(self):
        encoder = Base64Encoder()
        encoder.update(b"first")
        encoder.finalize()
        encoder.reset()
        result = encoder.encode(b"second")
        assert result == b64encode(b"second")

    def test_streaming_partial_blocks(self):
        data = b"Partial block test data"
        encoder = Base64Encoder()
        encoder.update(data[:1])
        encoder.update(data[1:4])
        encoder.update(data[4:])
        encoded = encoder.finalize()
        assert encoded == b64encode(data)

    def test_streaming_decode_with_interleaved_whitespace(self):
        data = b"Test whitespace filtering"
        encoded = b64encode(data)
        mangled = ""
        for i, c in enumerate(encoded):
            mangled += c
            if i % 5 == 0:
                mangled += " "
            if i % 7 == 0:
                mangled += "\n"
        decoded = b64decode(mangled)
        assert decoded == data


class TestEncoderDecoderClasses:
    def test_base64_encoder_class(self):
        encoder = Base64Encoder(pad=True, line_width=0)
        assert encoder.encode(b"test") == "dGVzdA=="

    def test_base64_decoder_class(self):
        decoder = Base64Decoder(pad=True)
        assert decoder.decode("dGVzdA==") == b"test"

    def test_base32_encoder_class(self):
        encoder = Base32Encoder(pad=True)
        assert encoder.encode(b"test") == "ORSXG5A="

    def test_base32_decoder_class(self):
        decoder = Base32Decoder(pad=True)
        assert decoder.decode("ORSXG5A=") == b"test"

    def test_base16_encoder_class(self):
        encoder = Base16Encoder()
        assert encoder.encode(b"test") == "74657374"

    def test_base16_decoder_class(self):
        decoder = Base16Decoder()
        assert decoder.decode("74657374") == b"test"

    def test_encoder_reset(self):
        encoder = Base64Encoder()
        encoder.update(b"partial")
        encoder.reset()
        result = encoder.encode(b"complete")
        assert result == b64encode(b"complete")

    def test_decoder_reset(self):
        decoder = Base64Decoder()
        decoder.update("cGFydGlhbA==")
        decoder.reset()
        result = decoder.decode("Y29tcGxldGU=")
        assert result == b"complete"


class TestConvenienceFunctions:
    def test_b64encode_function(self):
        assert b64encode(b"hello") == "aGVsbG8="

    def test_b64decode_function(self):
        assert b64decode("aGVsbG8=") == b"hello"

    def test_b32encode_function(self):
        assert b32encode(b"hello") == "NBSWY3DP"

    def test_b32decode_function(self):
        assert b32decode("NBSWY3DP") == b"hello"

    def test_b16encode_function(self):
        assert b16encode(b"hello") == "68656C6C6F"

    def test_b16decode_function(self):
        assert b16decode("68656C6C6F") == b"hello"
