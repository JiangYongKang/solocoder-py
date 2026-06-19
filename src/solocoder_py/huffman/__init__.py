from __future__ import annotations

from .canonical import (
    build_canonical_codes,
    build_decode_table,
    generate_code_table,
    verify_prefix_code_property,
)
from .codec import (
    HuffmanDecoder,
    HuffmanEncoder,
    decode,
    encode,
)
from .exceptions import (
    HuffmanCodeLengthOverflowError,
    HuffmanDecodeError,
    HuffmanEmptyFrequencyTableError,
    HuffmanEmptyInputError,
    HuffmanError,
    HuffmanInvalidCodeError,
    HuffmanInvalidFrequencyError,
    HuffmanTruncatedCodeError,
)
from .frequency import (
    count_frequencies,
    count_frequencies_bytes,
    count_frequencies_text,
    filter_frequency_table,
    validate_frequency_table,
)
from .models import (
    CodeInfo,
    CodeLengthTable,
    CodeTable,
    EncodedData,
    FrequencyTable,
    HuffmanNode,
)
from .tree import (
    build_code_lengths,
    build_huffman_tree,
    extract_code_lengths,
)

__all__ = [
    "HuffmanError",
    "HuffmanEmptyInputError",
    "HuffmanEmptyFrequencyTableError",
    "HuffmanInvalidFrequencyError",
    "HuffmanCodeLengthOverflowError",
    "HuffmanDecodeError",
    "HuffmanInvalidCodeError",
    "HuffmanTruncatedCodeError",
    "HuffmanNode",
    "CodeInfo",
    "FrequencyTable",
    "CodeLengthTable",
    "CodeTable",
    "EncodedData",
    "count_frequencies",
    "count_frequencies_text",
    "count_frequencies_bytes",
    "validate_frequency_table",
    "filter_frequency_table",
    "build_huffman_tree",
    "extract_code_lengths",
    "build_code_lengths",
    "build_canonical_codes",
    "generate_code_table",
    "verify_prefix_code_property",
    "build_decode_table",
    "HuffmanEncoder",
    "HuffmanDecoder",
    "encode",
    "decode",
]
