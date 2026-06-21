from __future__ import annotations

import pytest

from solocoder_py.di import Container, Lifetime


class SimpleService:
    pass


class ServiceWithCounter:
    call_count = 0

    def __init__(self) -> None:
        ServiceWithCounter.call_count += 1


class Logger:
    pass


class Database:
    pass


class Repository:
    def __init__(self, database: Database) -> None:
        self.database = database


class Controller:
    def __init__(self, repository: Repository, logger: Logger) -> None:
        self.repository = repository
        self.logger = logger


class INotifier:
    pass


class EmailNotifier(INotifier):
    pass


class SmsNotifier(INotifier):
    pass


class ScopedService:
    pass


class TransientService:
    pass


class SingletonService:
    pass


@pytest.fixture
def container():
    return Container()


@pytest.fixture
def container_with_services():
    c = Container()
    c.register_singleton(SingletonService)
    c.register_transient(TransientService)
    c.register_scoped(ScopedService)
    return c
