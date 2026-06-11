import pytest

from solocoder_py.framecodec import (
    CrcCheckError,
    Frame,
    FrameCodec,
    FrameConfig,
    VersionIncompatibleError,
)
from solocoder_py.framecodec.exceptions import FrameTooLargeError


class TestFrameCodecIntegration:
    def test_encode_decode_roundtrip(self, codec, small_payload):
        encoded = codec.encode(small_payload)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == small_payload
        assert result.frame.version == codec.config.version

    def test_encode_decode_multiple_frames(self, codec):
        payloads = [b"alpha", b"beta", b"gamma", b"delta"]
        all_data = b""
        for p in payloads:
            all_data += codec.encode(p)

        codec.feed(all_data)
        frames = codec.decode_all()
        assert len(frames) == len(payloads)
        for i, frame in enumerate(frames):
            assert frame.payload == payloads[i]

    def test_encode_frame_roundtrip(self, codec, small_payload):
        frame = Frame(version=1, payload=small_payload)
        encoded = codec.encode_frame(frame)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == frame.payload
        assert result.frame.version == frame.version

    def test_clear_buffer(self, codec, small_payload):
        encoded = codec.encode(small_payload)
        codec.feed(encoded)
        assert codec.buffer_size == len(encoded)
        codec.clear_buffer()
        assert codec.buffer_size == 0

    def test_encoder_property(self, codec):
        assert codec.encoder is not None
        assert codec.encoder.config is codec.config

    def test_decoder_property(self, codec):
        assert codec.decoder is not None
        assert codec.decoder.config is codec.config

    def test_config_property(self, codec):
        assert isinstance(codec.config, FrameConfig)


class TestBoundaryConditions:
    def test_zero_length_payload(self, codec):
        encoded = codec.encode(b"")
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == b""
        assert result.frame.payload_size == 0

    def test_max_length_payload(self, codec):
        max_payload = b"x" * codec.config.max_payload_size
        encoded = codec.encode(max_payload)
        assert len(encoded) == codec.config.max_frame_size()
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == max_payload

    def test_single_byte_payload(self, codec):
        payload = b"\x42"
        encoded = codec.encode(payload)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == payload

    def test_single_byte_length_prefix_boundary_1byte(self):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
            length_prefix_size=1,
            max_payload_size=255,
        )
        codec = FrameCodec(config)

        payload_255 = b"x" * 255
        encoded = codec.encode(payload_255)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == payload_255

    def test_single_byte_length_prefix_boundary_overflow(self):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
            length_prefix_size=1,
            max_payload_size=255,
        )
        codec = FrameCodec(config)

        with pytest.raises(FrameTooLargeError):
            codec.encode(b"x" * 256)

    def test_two_byte_length_prefix_boundary(self, codec):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
            length_prefix_size=2,
            max_payload_size=65535,
        )
        codec = FrameCodec(config)

        payload_65535 = b"x" * 65535
        encoded = codec.encode(payload_65535)
        assert len(encoded) == 1 + 2 + 65535 + 2
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == payload_65535

    def test_version_boundary_min(self):
        config = FrameConfig(
            version=2,
            min_supported_version=1,
            max_supported_version=3,
        )
        codec = FrameCodec(config)

        v1_config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=3,
        )
        v1_encoder = FrameCodec(v1_config)
        encoded = v1_encoder.encode(b"min version test", version=1)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.version == 1

    def test_version_boundary_max(self):
        config = FrameConfig(
            version=2,
            min_supported_version=1,
            max_supported_version=3,
        )
        codec = FrameCodec(config)

        v3_config = FrameConfig(
            version=3,
            min_supported_version=1,
            max_supported_version=3,
        )
        v3_encoder = FrameCodec(v3_config)
        encoded = v3_encoder.encode(b"max version test", version=3)
        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.version == 3


class TestErrorScenarios:
    def test_crc_mismatch_rejects_frame(self, codec):
        encoded = bytearray(codec.encode(b"test payload"))
        encoded[-1] ^= 0xAA
        codec.feed(bytes(encoded))
        with pytest.raises(CrcCheckError):
            codec.decode_one()

    def test_version_too_high_rejects(self):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=1,
        )
        codec = FrameCodec(config)

        v2_config = FrameConfig(
            version=2,
            min_supported_version=1,
            max_supported_version=2,
        )
        v2_encoder = FrameCodec(v2_config)
        encoded = v2_encoder.encode(b"high version", version=2)
        codec.feed(encoded)
        with pytest.raises(VersionIncompatibleError):
            codec.decode_one()

    def test_version_too_low_rejects(self):
        config = FrameConfig(
            version=2,
            min_supported_version=2,
            max_supported_version=2,
        )
        codec = FrameCodec(config)

        v1_config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
        )
        v1_encoder = FrameCodec(v1_config)
        encoded = v1_encoder.encode(b"low version", version=1)
        codec.feed(encoded)
        with pytest.raises(VersionIncompatibleError):
            codec.decode_one()

    def test_incomplete_frame_waits(self, codec, small_payload):
        encoded = codec.encode(small_payload)
        partial = encoded[: len(encoded) - 5]
        codec.feed(partial)
        result = codec.decode_one()
        assert result.waiting_for_more is True
        assert result.frame is None

    def test_incomplete_header_waits(self, codec):
        codec.feed(b"\x01\x00")
        result = codec.decode_one()
        assert result.waiting_for_more is True

    def test_payload_length_mismatch_shorter_than_expected(self, codec):
        config = codec.config
        header = (
            (1).to_bytes(config.version_size, byteorder=config.byte_order, signed=False)
            + (100).to_bytes(config.length_prefix_size, byteorder=config.byte_order, signed=False)
        )
        short_payload = b"short"

        from solocoder_py.framecodec import CrcCalculator

        fake_full = header + short_payload + b"\x00" * (100 - len(short_payload))
        crc = CrcCalculator.calculate(fake_full, config.crc_size)
        crc_bytes = crc.to_bytes(config.crc_size, byteorder=config.byte_order, signed=False)

        bad_frame = header + short_payload + crc_bytes
        codec.feed(bad_frame)
        result = codec.decode_one()
        assert result.waiting_for_more is True

    def test_multiple_bad_frames_mixed_with_good(self, codec):
        good1 = codec.encode(b"good1")
        bad = bytearray(codec.encode(b"bad payload"))
        bad[5] ^= 0xFF
        good2 = codec.encode(b"good2")

        codec.feed(good1 + bytes(bad) + good2)

        r1 = codec.decode_one()
        assert r1.frame is not None
        assert r1.frame.payload == b"good1"

        with pytest.raises(CrcCheckError):
            codec.decode_one()

        r2 = codec.decode_one()
        assert r2.frame is not None
        assert r2.frame.payload == b"good2"


class TestComplexScenarios:
    def test_streaming_decode_byte_by_byte(self, codec):
        payloads = [b"first", b"second", b"third"]
        all_data = b"".join(codec.encode(p) for p in payloads)

        frames = []
        for i in range(len(all_data)):
            codec.feed(bytes([all_data[i]]))
            while True:
                result = codec.decode_one()
                if result.frame is not None:
                    frames.append(result.frame)
                else:
                    break

        assert len(frames) == 3
        for i, frame in enumerate(frames):
            assert frame.payload == payloads[i]

    def test_chunked_decode(self, codec, large_payload):
        encoded = codec.encode(large_payload)
        chunk_size = 64

        pos = 0
        while pos < len(encoded):
            chunk = encoded[pos : pos + chunk_size]
            codec.feed(chunk)
            pos += len(chunk)

        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == large_payload

    def test_version_mixed_frames(self, v2_codec):
        config_v1 = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
        )
        encoder_v1 = FrameCodec(config_v1)

        v1_frame = encoder_v1.encode(b"v1 data", version=1)
        v2_frame = v2_codec.encode(b"v2 data", version=2)

        v2_codec.feed(v1_frame + v2_frame)
        frames = v2_codec.decode_all()
        assert len(frames) == 2
        assert frames[0].version == 1
        assert frames[0].payload == b"v1 data"
        assert frames[1].version == 2
        assert frames[1].payload == b"v2 data"

    def test_crc32_roundtrip(self):
        config = FrameConfig(
            version=1,
            min_supported_version=1,
            max_supported_version=2,
            crc_size=4,
        )
        codec = FrameCodec(config)

        payload = b"CRC32 test payload"
        encoded = codec.encode(payload)
        assert len(encoded) == config.overhead_size + len(payload)

        codec.feed(encoded)
        result = codec.decode_one()
        assert result.frame is not None
        assert result.frame.payload == payload
        assert result.frame.crc != 0

    def test_crc_collision_extremely_unlikely(self, codec):
        payload1 = b"Hello, World!"
        payload2 = b"Goodbye, World!"

        encoded1 = codec.encode(payload1)
        encoded2 = codec.encode(payload2)

        crc1_start = codec.config.header_size + len(payload1)
        crc2_start = codec.config.header_size + len(payload2)
        crc1 = int.from_bytes(
            encoded1[crc1_start : crc1_start + codec.config.crc_size],
            byteorder=codec.config.byte_order,
            signed=False,
        )
        crc2 = int.from_bytes(
            encoded2[crc2_start : crc2_start + codec.config.crc_size],
            byteorder=codec.config.byte_order,
            signed=False,
        )

        assert crc1 != crc2
