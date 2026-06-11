from __future__ import annotations


class SerializerError(Exception):
    pass


class BufferOverflowError(SerializerError):
    pass


class VarintDecodeError(SerializerError):
    pass


class ZigZagOverflowError(SerializerError):
    pass


class SchemaError(SerializerError):
    pass


class SchemaCompatibilityError(SchemaError):
    pass


class UnknownFieldError(SchemaError):
    pass


class DeserializationError(SerializerError):
    pass
