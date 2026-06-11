import pytest

from solocoder_py.framecodec import FrameConfig, FrameEncoder, Frame
from solocoder_py.framecodec.exceptions import FrameTooLargeError


class TestFrameEncoder:
    def test_encode_simple_payload(self, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        assert isinstance(encoded, bytes)
        assert len(encoded) == encoder.config.overhead_size + len(small_payload)

    def test_encode_uses_default_version(self, encoder):
        encoded = encoder.encode(b"test")
        version = int.from_bytes(
            encoded[: encoder.config.version_size],
            byteorder=encoder.config.byte_order,
            signed=False,
        )
        assert version == encoder.config.version

    def test_encode_with_specific_version(self, encoder):
        encoded = encoder.encode(b"test", version=2)
        version = int.from_bytes(
            encoded[: encoder.config.version_size],
            byteorder=encoder.config.byte_order,
            signed=False,
        )
        assert version == 2

    def test_encode_length_prefix(self, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        length_offset = encoder.config.version_size
        length_size = encoder.config.length_prefix_size
        payload_length = int.from_bytes(
            encoded[length_offset : length_offset + length_size],
            byteorder=encoder.config.byte_order,
            signed=False,
        )
        assert payload_length == len(small_payload)

    def test_encode_contains_payload(self, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        header_size = encoder.config.header_size
        payload = encoded[header_size : header_size + len(small_payload)]
        assert payload == small_payload

    def test_encode_empty_payload(self, encoder, empty_payload):
        encoded = encoder.encode(empty_payload)
        assert len(encoded) == encoder.config.overhead_size

        header_size = encoder.config.header_size
        length_offset = encoder.config.version_size
        length_size = encoder.config.length_prefix_size
        payload_length = int.from_bytes(
            encoded[length_offset : length_offset + length_size],
            byteorder=encoder.config.byte_order,
            signed=False,
        )
        assert payload_length == 0

    def test_encode_large_payload(self, encoder, large_payload):
        encoded = encoder.encode(large_payload)
        assert len(encoded) == encoder.config.overhead_size + len(large_payload)

    def test_encode_payload_too_large_raises(self, encoder):
        large_data = b"x" * (encoder.config.max_payload_size + 1)
        with pytest.raises(FrameTooLargeError, match="exceeds maximum"):
            encoder.encode(large_data)

    def test_encode_max_size_payload(self, encoder):
        max_data = b"x" * encoder.config.max_payload_size
        encoded = encoder.encode(max_data)
        assert len(encoded) == encoder.config.max_frame_size()

    def test_encode_frame(self, encoder, small_payload):
        frame = Frame(version=2, payload=small_payload)
        encoded = encoder.encode_frame(frame)
        assert isinstance(encoded, bytes)

        version = int.from_bytes(
            encoded[: encoder.config.version_size],
            byteorder=encoder.config.byte_order,
            signed=False,
        )
        assert version == 2

    def test_calculate_frame_size(self, encoder):
        size = encoder.calculate_frame_size(100)
        assert size == encoder.config.overhead_size + 100

    def test_calculate_frame_size_zero(self, encoder):
        size = encoder.calculate_frame_size(0)
        assert size == encoder.config.overhead_size

    def test_encode_with_custom_config(self):
        config = FrameConfig(
            version=3,
            min_supported_version=1,
            max_supported_version=3,
            length_prefix_size=4,
            crc_size=4,
            version_size=1,
        )
        encoder = FrameEncoder(config)
        payload = b"custom config test"
        encoded = encoder.encode(payload)

        assert len(encoded) == config.overhead_size + len(payload)

        version = int.from_bytes(
            encoded[: config.version_size],
            byteorder=config.byte_order,
            signed=False,
        )
        assert version == 3

        length_offset = config.version_size
        length = int.from_bytes(
            encoded[length_offset : length_offset + config.length_prefix_size],
            byteorder=config.byte_order,
            signed=False,
        )
        assert length == len(payload)
