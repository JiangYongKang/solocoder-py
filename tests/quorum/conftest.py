from typing import List, Optional
import uuid

from solocoder_py.quorum import (
    QuorumCoordinator,
    Replica,
)


def make_replica(
    replica_id: Optional[str] = None,
    name: Optional[str] = None,
) -> Replica:
    rid = replica_id or str(uuid.uuid4())
    return Replica(id=rid, name=name or f"replica-{rid[:8]}")


def make_replicas(count: int) -> List[Replica]:
    return [make_replica(replica_id=f"replica-{i}", name=f"replica-{i}") for i in range(count)]


def make_coordinator(
    n: int = 3,
    w: Optional[int] = None,
    r: Optional[int] = None,
) -> QuorumCoordinator:
    if w is None:
        w = n // 2 + 1
    if r is None:
        r = n // 2 + 1
    replicas = make_replicas(n)
    return QuorumCoordinator(replicas=replicas, w=w, r=r)
