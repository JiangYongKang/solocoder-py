from __future__ import annotations


class QuorumError(Exception):
    pass


class InvalidQuorumConfigError(QuorumError):
    def __init__(self, n: int, w: int, r: int) -> None:
        self.n = n
        self.w = w
        self.r = r
        super().__init__(
            f"Invalid quorum configuration: N={n}, W={w}, R={r}. "
            f"Must satisfy W>0, R>0, W<=N, R<=N, and W+R>N"
        )


class QuorumWriteError(QuorumError):
    def __init__(self, key: str, successful: int, required: int) -> None:
        self.key = key
        self.successful = successful
        self.required = required
        super().__init__(
            f"Quorum write failed for key '{key}': "
            f"{successful}/{required} replicas acknowledged"
        )


class QuorumReadError(QuorumError):
    def __init__(self, key: str, successful: int, required: int) -> None:
        self.key = key
        self.successful = successful
        self.required = required
        super().__init__(
            f"Quorum read failed for key '{key}': "
            f"{successful}/{required} replicas responded"
        )


class ReplicaUnreachableError(QuorumError):
    def __init__(self, replica_id: str) -> None:
        self.replica_id = replica_id
        super().__init__(f"Replica '{replica_id}' is unreachable")


class VersionConflictError(QuorumError):
    def __init__(self, key: str, versions: list[tuple[str, int]]) -> None:
        self.key = key
        self.versions = versions
        version_str = ", ".join(f"{rid}={v}" for rid, v in versions)
        super().__init__(
            f"Version conflict detected for key '{key}': [{version_str}]"
        )
