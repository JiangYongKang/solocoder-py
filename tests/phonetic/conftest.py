import pytest

from solocoder_py.phonetic import PhoneticIndex


@pytest.fixture
def empty_index():
    return PhoneticIndex()


@pytest.fixture
def sample_names():
    return [
        "Robert",
        "Rupert",
        "Rubin",
        "Smith",
        "Smythe",
        "Schmidt",
        "Catherine",
        "Katherine",
        "Katheryn",
        "John",
        "Jon",
        "Shawn",
        "Sean",
    ]


@pytest.fixture
def populated_index(sample_names):
    return PhoneticIndex(sample_names)
