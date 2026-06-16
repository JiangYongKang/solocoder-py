from __future__ import annotations


class SCCError(Exception):
    pass


class NodeNotFoundError(SCCError):
    pass


class EmptyGraphError(SCCError):
    pass
