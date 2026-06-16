from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from typing import Any, TypeVar

from .exceptions import InvalidComponentError

C = TypeVar("C", bound=type)

_COMPONENT_MARKER = "_is_ecs_component"


def component(cls: C) -> C:
    if not is_dataclass(cls):
        cls = dataclass(cls)
    setattr(cls, _COMPONENT_MARKER, True)
    return cls


def is_component_type(cls: type) -> bool:
    return getattr(cls, _COMPONENT_MARKER, False)


def validate_component_type(cls: type) -> None:
    if not is_component_type(cls):
        raise InvalidComponentError(cls)


def get_component_type_name(cls: type) -> str:
    return cls.__name__


@component
class Position:
    x: float = 0.0
    y: float = 0.0


@component
class Velocity:
    x: float = 0.0
    y: float = 0.0


@component
class Health:
    current: int = 100
    max: int = 100


@component
class Name:
    value: str = ""


@component
class Tag:
    value: str = ""
