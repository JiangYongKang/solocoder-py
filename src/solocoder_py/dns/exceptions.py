from __future__ import annotations


class DNSError(Exception):
    pass


class DNSCacheError(DNSError):
    pass


class DNSResolutionError(DNSError):
    pass


class DNSTimeoutError(DNSResolutionError):
    pass


class DNSCNAMELoopError(DNSResolutionError):
    def __init__(self, message: str, chain: list[str] | None = None) -> None:
        super().__init__(message)
        self.chain = chain or []


class DNSNoRecordsError(DNSResolutionError):
    pass


class DNSInvalidRecordError(DNSError):
    pass
