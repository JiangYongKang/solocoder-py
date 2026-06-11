from __future__ import annotations


class ProxyError(Exception):
    pass


class UpstreamError(ProxyError):
    pass


class AllUpstreamsFailedError(UpstreamError):
    pass


class ConnectionPoolError(ProxyError):
    pass


class RewriterError(ProxyError):
    pass


class HeaderFilterError(ProxyError):
    pass


class InvalidConfigError(ProxyError):
    pass
