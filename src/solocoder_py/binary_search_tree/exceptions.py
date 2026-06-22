class BSTError(Exception):
    pass


class ValueNotFoundError(BSTError):
    pass


class DuplicateValueError(BSTError):
    pass


class InvalidComparisonError(BSTError):
    pass
