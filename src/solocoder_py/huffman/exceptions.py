from __future__ import annotations


class HuffmanError(Exception):
    pass


class HuffmanEmptyInputError(HuffmanError):
    pass


class HuffmanEmptyFrequencyTableError(HuffmanError):
    pass


class HuffmanInvalidFrequencyError(HuffmanError):
    pass


class HuffmanCodeLengthOverflowError(HuffmanError):
    pass


class HuffmanDecodeError(HuffmanError):
    pass


class HuffmanInvalidCodeError(HuffmanDecodeError):
    pass


class HuffmanTruncatedCodeError(HuffmanDecodeError):
    pass
