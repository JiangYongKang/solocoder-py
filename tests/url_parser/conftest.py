import pytest

from solocoder_py.url_parser import (
    UrlBuilder,
    UrlParser,
    QueryParams,
    parse_url,
)


@pytest.fixture
def parser():
    return UrlParser()


@pytest.fixture
def builder():
    return UrlBuilder()
