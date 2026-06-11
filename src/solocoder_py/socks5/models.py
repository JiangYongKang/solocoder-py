from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .constants import (
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    ATYP_IPV6,
    MAX_DOMAIN_LENGTH,
)


class SessionState(str, Enum):
    INIT = "INIT"
    AUTHENTICATING = "AUTHENTICATING"
    AUTHENTICATED = "AUTHENTICATED"
    RELAYING = "RELAYING"
    UDP_ASSOCIATED = "UDP_ASSOCIATED"
    CLOSED = "CLOSED"


@dataclass
class Socks5Address:
    atyp: int
    host: str
    port: int

    def __post_init__(self) -> None:
        valid_atyps = (ATYP_IPV4, ATYP_DOMAINNAME, ATYP_IPV6)
        if self.atyp not in valid_atyps:
            raise ValueError(
                f"Invalid address type: 0x{self.atyp:02x}"
            )
        if not (0 <= self.port <= 65535):
            raise ValueError(
                f"Port out of range: {self.port}"
            )
        if self.atyp == ATYP_DOMAINNAME and len(self.host) > MAX_DOMAIN_LENGTH:
            raise ValueError(
                f"Domain name exceeds maximum length of {MAX_DOMAIN_LENGTH}"
            )


@dataclass
class UdpDatagram:
    rsv: int
    frag: int
    address: Socks5Address
    data: bytes


@dataclass
class MethodSelection:
    version: int
    method: int


@dataclass
class AuthReply:
    version: int
    success: bool


@dataclass
class Socks5Reply:
    version: int
    reply_code: int
    bind_address: Socks5Address


@dataclass
class TargetConnection:
    host: str
    port: int
    incoming: list = field(default_factory=list)
    outgoing: list = field(default_factory=list)
