from __future__ import annotations


class PartitionAssignorError(Exception):
    pass


class ConsumerAlreadyRegisteredError(PartitionAssignorError):
    pass


class ConsumerNotFoundError(PartitionAssignorError):
    pass


class PartitionNotFoundError(PartitionAssignorError):
    pass


class EmptyConsumerGroupError(PartitionAssignorError):
    pass


class InvalidPartitionIdError(PartitionAssignorError):
    pass
