import pytest

from solocoder_py.csv_parser import CSVParser


@pytest.fixture
def parser() -> CSVParser:
    return CSVParser()


@pytest.fixture
def parser_no_header() -> CSVParser:
    return CSVParser(has_header=False)


@pytest.fixture
def parser_align() -> CSVParser:
    return CSVParser(align_fields=True)
