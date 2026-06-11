import pytest

from solocoder_py.framecodec import (
    CrcCheckError,
    FrameConfig,
    FrameDecoder,
    FrameEncoder,
    VersionIncompatibleError,
)
from solocoder_py.framecodec.exceptions import IncompleteFrameError


class TestFrameDecoderBasic:
    def test_decode_one_frame(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == small_payload
        assert result.frame.version == encoder.config.version
        assert result.consumed == len(encoded)
        assert result.waiting_for_more is False

    def test_decode_empty_payload(self, decoder, encoder, empty_payload):
        encoded = encoder.encode(empty_payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == b""
        assert result.frame.payload_size == 0

    def test_decode_large_payload(self, decoder, encoder, large_payload):
        encoded = encoder.encode(large_payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == large_payload
        assert len(result.frame.payload) == len(large_payload)

    def test_decode_all_multiple_frames(self, decoder, encoder):
        payloads = [b"frame1", b"frame2", b"frame3"]
        all_data = b""
        for p in payloads:
            all_data += encoder.encode(p)

        decoder.feed(all_data)
        frames = decoder.decode_all()
        assert len(frames) == 3
        for i, frame in enumerate(frames):
            assert frame.payload == payloads[i]

    def test_decode_multiple_frames_one_by_one(self, decoder, encoder):
        payload1 = b"first"
        payload2 = b"second"
        data1 = encoder.encode(payload1)
        data2 = encoder.encode(payload2)

        decoder.feed(data1 + data2)

        result1 = decoder.decode_one()
        assert result1.frame is not None
        assert result1.frame.payload == payload1

        result2 = decoder.decode_one()
        assert result2.frame is not None
        assert result2.frame.payload == payload2

    def test_clear_buffer(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        decoder.feed(encoded)
        assert decoder.buffer_size > 0
        decoder.clear()
        assert decoder.buffer_size == 0


class TestIncompleteFrames:
    def test_incomplete_header(self, decoder):
        decoder.feed(b"\x01")
        result = decoder.decode_one()
        assert result.frame is None
        assert result.waiting_for_more is True
        assert decoder.buffer_size == 1

    def test_incomplete_payload(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        half = len(encoded) // 2
        decoder.feed(encoded[:half])
        result = decoder.decode_one()
        assert result.frame is None
        assert result.waiting_for_more is True

    def test_incomplete_then_complete(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        mid = len(encoded) // 2

        decoder.feed(encoded[:mid])
        result1 = decoder.decode_one()
        assert result1.waiting_for_more is True

        decoder.feed(encoded[mid:])
        result2 = decoder.decode_one()
        assert result2.frame is not None
        assert result2.frame.payload == small_payload

    def test_incomplete_then_multiple_frames(self, decoder, encoder):
        p1 = b"first"
        p2 = b"second"
        d1 = encoder.encode(p1)
        d2 = encoder.encode(p2)

        decoder.feed(d1[:3])
        result = decoder.decode_one()
        assert result.waiting_for_more is True

        decoder.feed(d1[3:] + d2)
        frames = decoder.decode_all()
        assert len(frames) == 2
        assert frames[0].payload == p1
        assert frames[1].payload == p2

    def test_single_byte_stream(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        for byte in encoded:
            decoder.feed(bytes([byte]))
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == small_payload


class TestCrcVerification:
    def test_crc_corrupted_payload_raises(self, decoder, encoder, small_payload):
        encoded = bytearray(encoder.encode(small_payload))
        header_size = encoder.config.header_size
        encoded[header_size] ^= 0xFF
        decoder.feed(bytes(encoded))
        with pytest.raises(CrcCheckError, match="CRC mismatch"):
            decoder.decode_one()

    def test_crc_corrupted_header_raises(self, decoder, encoder, small_payload):
        encoded = bytearray(encoder.encode(small_payload))
        encoded[0] ^= 0xFF
        decoder.feed(bytes(encoded))
        try:
            decoder.decode_one()
        except CrcCheckError:
            pass
        except VersionIncompatibleError:
            pass
        else:
            pytest.fail("Expected CrcCheckError or VersionIncompatibleError")

    def test_crc_corrupted_crc_field_raises(self, decoder, encoder, small_payload):
        encoded = bytearray(encoder.encode(small_payload))
        encoded[-1] ^= 0xFF
        decoder.feed(bytes(encoded))
        with pytest.raises(CrcCheckError, match="CRC mismatch"):
            decoder.decode_one()

    def test_valid_crc_passes(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.crc != 0

    def test_crc_error_consumes_frame(self, decoder, encoder, small_payload):
        bad_frame = bytearray(encoder.encode(small_payload))
        bad_frame[-1] ^= 0xFF
        good_frame = encoder.encode(b"good")

        decoder.feed(bytes(bad_frame) + good_frame)
        with pytest.raises(CrcCheckError):
            decoder.decode_one()

        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == b"good"


class TestVersionNegotiation:
    def test_decode_same_version(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload, version=1)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.version == 1

    def test_decode_higher_supported_version(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload, version=2)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.version == 2

    def test_decode_version_below_min_raises(self):
        config = FrameConfig(
            version=2,
            min_supported_version=2,
            max_supported_version=3,
        )
        encoder = FrameEncoder(config)
        decoder = FrameDecoder(config)

        low_config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=3,
        )
        low_encoder = FrameEncoder(low_config)
        encoded = low_encoder.encode(b"test", version=1)
        decoder.feed(encoded)
        with pytest.raises(VersionIncompatibleError, match="not supported"):
            decoder.decode_one()

    def test_decode_version_above_max_raises(self, decoder):
        high_version_payload = b"\x03\x00\x04test"
        from solocoder_py.framecodec import CrcCalculator

        config = decoder.config
        crc = CrcCalculator.calculate(high_version_payload, config.crc_size)
        crc_bytes = crc.to_bytes(config.crc_size, byteorder=config.byte_order, signed=False)
        full_frame = high_version_payload + crc_bytes
        decoder.feed(full_frame)
        with pytest.raises(VersionIncompatibleError, match="not supported"):
            decoder.decode_one()

    def test_version_incompatible_consumes_frame(self, decoder):
        config = decoder.config
        bad_version = config.max_supported_version + 1
        from solocoder_py.framecodec import CrcCalculator

        header = (
            bad_version.to_bytes(config.version_size, byteorder=config.byte_order, signed=False)
            + (4).to_bytes(config.length_prefix_size, byteorder=config.byte_order, signed=False)
        )
        payload = b"test"
        crc = CrcCalculator.calculate(header + payload, config.crc_size)
        crc_bytes = crc.to_bytes(config.crc_size, byteorder=config.byte_order, signed=False)
        bad_frame = header + payload + crc_bytes

        good_frame = FrameEncoder(config).encode(b"good")

        decoder.feed(bad_frame + good_frame)
        with pytest.raises(VersionIncompatibleError):
            decoder.decode_one()

        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == b"good"

    def test_adjacent_version_support(self):
        config = FrameConfig(
            version=2,
            min_supported_version=1,
            max_supported_version=2,
        )
        decoder = FrameDecoder(config)
        encoder_v1 = FrameEncoder(FrameConfig(version=1, min_supported_version=1, max_supported_version=2))
        encoder_v2 = FrameEncoder(config)

        decoder.feed(encoder_v1.encode(b"v1_data"))
        result1 = decoder.decode_one()
        assert result1.frame is not None
        assert result1.frame.version == 1
        assert result1.frame.payload == b"v1_data"

        decoder.feed(encoder_v2.encode(b"v2_data"))
        result2 = decoder.decode_one()
        assert result2.frame is not None
        assert result2.frame.version == 2
        assert result2.frame.payload == b"v2_data"


class TestDecoderEdgeCases:
    def test_empty_buffer(self, decoder):
        result = decoder.decode_one()
        assert result.frame is None
        assert result.waiting_for_more is True

    def test_decode_all_empty(self, decoder):
        frames = decoder.decode_all()
        assert frames == []

    def test_exactly_one_frame(self, decoder, encoder, small_payload):
        encoded = encoder.encode(small_payload)
        decoder.feed(encoded)
        frames = decoder.decode_all()
        assert len(frames) == 1
        assert frames[0].payload == small_payload

    def test_one_and_half_frames(self, decoder, encoder, small_payload):
        f1 = encoder.encode(small_payload)
        f2 = encoder.encode(b"second")
        decoder.feed(f1 + f2[: len(f2) // 2])
        frames = decoder.decode_all()
        assert len(frames) == 1
        assert frames[0].payload == small_payload
        assert decoder.buffer_size > 0

    def test_zero_length_frame(self, decoder, encoder, empty_payload):
        encoded = encoder.encode(empty_payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload_size == 0
        assert result.consumed == encoder.config.overhead_size

    def test_custom_config_decoding(self):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
            length_prefix_size=4,
            crc_size=4,
            version_size=2,
        )
        encoder = FrameEncoder(config)
        decoder = FrameDecoder(config)

        payload = b"custom config test payload"
        encoded = encoder.encode(payload)
        decoder.feed(encoded)
        result = decoder.decode_one()
        assert result.frame is not None
        assert result.frame.payload == payload
        assert result.frame.version == 1
