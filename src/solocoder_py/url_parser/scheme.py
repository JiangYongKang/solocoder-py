from __future__ import annotations

import re

from .exceptions import InvalidSchemeError

_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+\-.]*$")

_KNOWN_SCHEMES: set[str] = {
    "http",
    "https",
    "ftp",
    "ftps",
    "ssh",
    "telnet",
    "mailto",
    "file",
    "data",
    "blob",
    "ws",
    "wss",
    "urn",
    "tel",
    "fax",
    "modem",
    "sip",
    "sips",
    "ldap",
    "ldaps",
    "nfs",
    "git",
    "svn",
    "sftp",
    "irc",
    "mms",
    "rtsp",
    "rtmp",
    "rtmps",
    "jdbc",
    "mysql",
    "postgresql",
    "postgres",
    "mongodb",
    "redis",
    "amqp",
    "jms",
    "otpauth",
    "chrome",
    "chrome-extension",
    "moz-extension",
}


def validate_scheme(scheme: str) -> None:
    if not scheme:
        raise InvalidSchemeError("Scheme cannot be empty")
    if not _SCHEME_PATTERN.match(scheme):
        raise InvalidSchemeError(
            f"Invalid scheme '{scheme}': must start with a letter and contain "
            f"only letters, digits, '+', '-', or '.'"
        )


def is_scheme_known(scheme: str) -> bool:
    return scheme.lower() in _KNOWN_SCHEMES


def register_scheme(scheme: str) -> None:
    validate_scheme(scheme)
    _KNOWN_SCHEMES.add(scheme.lower())


def get_known_schemes() -> frozenset[str]:
    return frozenset(_KNOWN_SCHEMES)
