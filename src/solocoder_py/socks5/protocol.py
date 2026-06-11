from __future__ import annotations

import ipaddress
import struct
from typing import List, Tuple

from .constants import (
    SOCKS_VERSION,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    ATYP_IPV6,
)
from .models import (
    Socks5Address,
    UdpDatagram,
    MethodSelection,
    AuthReply,
    Socks5Reply,
)


def _encode_address(addr: Socks5Address) -> bytes:
    if addr.atyp == ATYP_IPV4:
        return struct.pack("!B4sH", ATYP_IPV4, ipaddress.IPv4Address(addr.host).packed, addr.port)
    elif addr.atyp == ATYP_DOMAINNAME:
        domain_bytes = addr.host.encode("ascii")
        return struct.pack("!BB", ATYP_DOMAINNAME, len(domain_bytes)) + domain_bytes + struct.pack("!H", addr.port)
    elif addr.atyp == ATYP_IPV6:
        return struct.pack("!B16sH", ATYP_IPV6, ipaddress.IPv6Address(addr.host).packed, addr.port)
    else:
        raise ValueError(f"Unsupported address type: 0x{addr.atyp:02x}")


def _decode_address(data: bytes, offset: int) -> Tuple[Socks5Address, int]:
    atyp = data[offset]
    offset += 1

    if atyp == ATYP_IPV4:
        host = str(ipaddress.IPv4Address(data[offset:offset + 4]))
        offset += 4
        port = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
        return Socks5Address(atyp=ATYP_IPV4, host=host, port=port), offset
    elif atyp == ATYP_DOMAINNAME:
        domain_len = data[offset]
        offset += 1
        host = data[offset:offset + domain_len].decode("ascii")
        offset += domain_len
        port = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
        return Socks5Address(atyp=ATYP_DOMAINNAME, host=host, port=port), offset
    elif atyp == ATYP_IPV6:
        host = str(ipaddress.IPv6Address(data[offset:offset + 16]))
        offset += 16
        port = struct.unpack("!H", data[offset:offset + 2])[0]
        offset += 2
        return Socks5Address(atyp=ATYP_IPV6, host=host, port=port), offset
    else:
        raise ValueError(f"Unsupported address type: 0x{atyp:02x}")


def build_greeting(methods: List[int]) -> bytes:
    return struct.pack("!BB", SOCKS_VERSION, len(methods)) + bytes(methods)


def parse_method_selection(data: bytes) -> MethodSelection:
    version = data[0]
    method = data[1]
    return MethodSelection(version=version, method=method)


def build_method_selection(method: int) -> bytes:
    return struct.pack("!BB", SOCKS_VERSION, method)


def build_auth_request(username: str, password: str) -> bytes:
    uname = username.encode("utf-8")
    passwd = password.encode("utf-8")
    return (
        struct.pack("!BB", 0x01, len(uname))
        + uname
        + struct.pack("!B", len(passwd))
        + passwd
    )


def parse_auth_request(data: bytes) -> Tuple[str, str]:
    offset = 0
    ver = data[offset]
    offset += 1
    ulen = data[offset]
    offset += 1
    username = data[offset:offset + ulen].decode("utf-8")
    offset += ulen
    plen = data[offset]
    offset += 1
    password = data[offset:offset + plen].decode("utf-8")
    return username, password


def parse_auth_reply(data: bytes) -> AuthReply:
    version = data[0]
    status = data[1]
    return AuthReply(version=version, success=(status == 0x00))


def build_auth_reply(success: bool) -> bytes:
    return struct.pack("!BB", 0x01, 0x00 if success else 0x01)


def build_request(cmd: int, addr: Socks5Address) -> bytes:
    return struct.pack("!BBB", SOCKS_VERSION, cmd, 0x00) + _encode_address(addr)


def parse_request(data: bytes) -> Tuple[int, Socks5Address]:
    version = data[0]
    cmd = data[1]
    rsv = data[2]
    addr, _ = _decode_address(data, 3)
    return cmd, addr


def build_reply(reply_code: int, bind_address: Socks5Address) -> bytes:
    return struct.pack("!BBB", SOCKS_VERSION, reply_code, 0x00) + _encode_address(bind_address)


def parse_reply(data: bytes) -> Socks5Reply:
    version = data[0]
    reply_code = data[1]
    rsv = data[2]
    bind_address, _ = _decode_address(data, 3)
    return Socks5Reply(version=version, reply_code=reply_code, bind_address=bind_address)


def build_udp_datagram(datagram: UdpDatagram) -> bytes:
    return struct.pack("!HB", datagram.rsv, datagram.frag) + _encode_address(datagram.address) + datagram.data


def parse_udp_datagram(data: bytes) -> UdpDatagram:
    offset = 0
    rsv = struct.unpack("!H", data[offset:offset + 2])[0]
    offset += 2
    frag = data[offset]
    offset += 1
    addr, offset = _decode_address(data, offset)
    payload = data[offset:]
    return UdpDatagram(rsv=rsv, frag=frag, address=addr, data=payload)
