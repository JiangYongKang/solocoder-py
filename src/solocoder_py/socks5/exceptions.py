from __future__ import annotations


class Socks5Error(Exception):
    pass


class Socks5HandshakeError(Socks5Error):
    pass


class Socks5AuthError(Socks5Error):
    pass


class Socks5RequestError(Socks5Error):
    pass


class Socks5ProtocolError(Socks5Error):
    pass


class Socks5ResolutionError(Socks5Error):
    pass
