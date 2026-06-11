import pytest

from solocoder_py.framecodec import FrameConfig, FrameCodec, FrameDecoder, FrameEncoder


@pytest.fixture
def default_config():
    return FrameConfig()


@pytest.fixture
def v2_config():
    return FrameConfig(
        version=2,
        min_supported_version=1,
        max_supported_version=2,
    )


@pytest.fixture
def encoder(default_config):
    return FrameEncoder(default_config)


@pytest.fixture
def decoder(default_config):
    return FrameDecoder(default_config)


@pytest.fixture
def codec(default_config):
    return FrameCodec(default_config)


@pytest.fixture
def v2_codec(v2_config):
    return FrameCodec(v2_config)


@pytest.fixture
def small_payload():
    return b"Hello, FrameCodec!"


@pytest.fixture
def large_payload():
    return b"A" * 1024


@pytest.fixture
def empty_payload():
    return b""
