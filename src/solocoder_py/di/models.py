from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Lifetime(str, Enum):
    SINGLETON = "SINGLETON"
    TRANSIENT = "TRANSIENT"
    SCOPED = "SCOPED"


@dataclass
class ServiceDescriptor:
    service_type: type
    implementation_type: type
    lifetime: Lifetime
    instance: Optional[Any] = None
