from __future__ import annotations

from typing import List, Optional, Tuple

from .constants import ATYP_DOMAINNAME
from .exceptions import Socks5Error
from .models import Socks5Address, UdpDatagram


class TcpRelay:
    def __init__(self) -> None:
        self._client_buffer: bytes = b""
        self._remote_buffer: bytes = b""

    def send_from_client(self, data: bytes) -> None:
        self._client_buffer += data

    def recv_for_remote(self) -> bytes:
        data = self._client_buffer
        self._client_buffer = b""
        return data

    def send_from_remote(self, data: bytes) -> None:
        self._remote_buffer += data

    def recv_for_client(self) -> bytes:
        data = self._remote_buffer
        self._remote_buffer = b""
        return data


class UdpRelay:
    def __init__(self, bind_port: int, dns_resolver=None, on_close: Optional[callable] = None) -> None:
        self._bind_port = bind_port
        self._active = True
        self._on_close = on_close
        self._dns_resolver = dns_resolver
        self._client_to_remote: List[Tuple[Tuple[str, int], bytes]] = []
        self._remote_to_client: List[UdpDatagram] = []

    @property
    def active(self) -> bool:
        return self._active

    @property
    def bind_port(self) -> int:
        return self._bind_port

    def send_from_client(self, datagram: UdpDatagram) -> None:
        if not self._active:
            raise Socks5Error("UDP association is not active")
        host = datagram.address.host
        if datagram.address.atyp == ATYP_DOMAINNAME and self._dns_resolver is not None:
            resolved = self._dns_resolver.resolve(host)
            if resolved is not None:
                host = resolved
        self._client_to_remote.append(
            ((host, datagram.address.port), datagram.data)
        )

    def recv_for_remote(self) -> List[Tuple[Tuple[str, int], bytes]]:
        data = list(self._client_to_remote)
        self._client_to_remote.clear()
        return data

    def send_from_remote(self, data: bytes, addr: Tuple[str, int]) -> None:
        if not self._active:
            raise Socks5Error("UDP association is not active")
        host, port = addr
        dg = UdpDatagram(
            rsv=0,
            frag=0,
            address=Socks5Address(atyp=0x01, host=host, port=port),
            data=data,
        )
        self._remote_to_client.append(dg)

    def recv_for_client(self) -> List[UdpDatagram]:
        data = list(self._remote_to_client)
        self._remote_to_client.clear()
        return data

    def close(self) -> None:
        self._active = False
        self._client_to_remote.clear()
        self._remote_to_client.clear()
