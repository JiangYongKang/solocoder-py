from __future__ import annotations


class KruskalError(Exception):
    pass


class NodeNotFoundError(KruskalError):
    pass


class EdgeNotFoundError(KruskalError):
    pass
