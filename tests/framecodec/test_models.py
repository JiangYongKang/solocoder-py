import pytest

from solocoder_py.framecodec import FrameConfig, Frame


class TestFrameConfig:
    def test_default_config(self):
        config = FrameConfig()
        assert config.version == 1
        assert config.min_supported_version == 1
        assert config.max_supported_version == 2
        assert config.length_prefix_size == 2
        assert config.crc_size == 2
        assert config.version_size == 1
        assert config.max_payload_size == 65535
        assert config.byte_order == "big"

    def test_header_size(self):
        config = FrameConfig()
        assert config.header_size == config.version_size + config.length_prefix_size

    def test_overhead_size(self):
        config = FrameConfig()
        assert config.overhead_size == config.header_size + config.crc_size

    def test_max_frame_size(self):
        config = FrameConfig()
        assert config.max_frame_size() == config.overhead_size + config.max_payload_size

    def test_invalid_version_size_raises(self):
        with pytest.raises(ValueError, match="version_size must be at least 1"):
            FrameConfig(version_size=0)

    def test_invalid_length_prefix_size_raises(self):
        with pytest.raises(ValueError, match="length_prefix_size must be at least 1"):
            FrameConfig(length_prefix_size=0)

    def test_invalid_crc_size_raises(self):
        with pytest.raises(ValueError, match="crc_size must be at least 1"):
            FrameConfig(crc_size=0)

    def test_version_below_min_raises(self):
        with pytest.raises(ValueError, match="version must be >= min_supported_version"):
            FrameConfig(version=0, min_supported_version=1)

    def test_version_above_max_raises(self):
        with pytest.raises(ValueError, match="version must be <= max_supported_version"):
            FrameConfig(version=3, max_supported_version=2)

    def test_min_gt_max_version_raises(self):
        with pytest.raises(ValueError, match="min_supported_version must be <= max_supported_version"):
            FrameConfig(min_supported_version=3, max_supported_version=2)

    def test_negative_max_payload_raises(self):
        with pytest.raises(ValueError, match="max_payload_size must be non-negative"):
            FrameConfig(max_payload_size=-1)


class TestFrameModel:
    def test_frame_creation(self):
        payload = b"test"
        frame = Frame(version=1, payload=payload, crc=0x1234)
        assert frame.version == 1
        assert frame.payload == payload
        assert frame.crc == 0x1234

    def test_frame_payload_size(self):
        frame = Frame(version=1, payload=b"hello world")
        assert frame.payload_size == 11

    def test_frame_empty_payload(self):
        frame = Frame(version=1, payload=b"")
        assert frame.payload_size == 0
