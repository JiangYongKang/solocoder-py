from __future__ import annotations


class InboxError(Exception):
    pass


class DedupWindowConfigError(InboxError):
    pass
