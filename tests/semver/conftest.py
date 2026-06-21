import pytest

from solocoder_py.semver import SemverVersion, VersionRange


@pytest.fixture
def parse_version():
    return SemverVersion.parse


@pytest.fixture
def parse_range():
    return VersionRange.parse
