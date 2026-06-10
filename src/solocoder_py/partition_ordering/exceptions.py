from __future__ import annotations


class PartitionOrderingError(Exception):
    pass


class PartitionNotFoundError(PartitionOrderingError):
    pass


class UnknownPartitionError(PartitionOrderingError):
    pass


class OutOfOrderCommitError(PartitionOrderingError):
    pass


class OffsetOutOfRangeError(PartitionOrderingError):
    pass


class ConsumerNotFoundError(PartitionOrderingError):
    pass


class PartitionAlreadyAssignedError(PartitionOrderingError):
    pass


class RebalanceInProgressError(PartitionOrderingError):
    pass


class EmptyBatchError(PartitionOrderingError):
    pass


class NotAssignedPartitionError(PartitionOrderingError):
    pass
