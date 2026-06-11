from __future__ import annotations


class SchemaMigrationError(Exception):
    pass


class MigrationNotFoundError(SchemaMigrationError):
    pass


class MigrationOrderError(SchemaMigrationError):
    pass


class MigrationIdempotencyError(SchemaMigrationError):
    pass


class MigrationRollbackError(SchemaMigrationError):
    pass


class MigrationExecutionError(SchemaMigrationError):
    pass
