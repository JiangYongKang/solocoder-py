class DeviceShadowError(Exception):
    pass


class VersionMismatchError(DeviceShadowError):
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version mismatch: expected {expected}, actual {actual}"
        )


class InvalidVersionError(DeviceShadowError):
    def __init__(self, version: int):
        self.version = version
        super().__init__(
            f"Invalid version: {version}, must be a positive integer"
        )


class NonSerializableValueError(DeviceShadowError):
    def __init__(self, path: str, value):
        self.path = path
        self.value = value
        super().__init__(
            f"Non-JSON-serializable value at '{path}': {repr(value)}"
        )


class InvalidStateError(DeviceShadowError):
    def __init__(self, reason: str):
        super().__init__(reason)
