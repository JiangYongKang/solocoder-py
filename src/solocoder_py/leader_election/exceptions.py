from __future__ import annotations


class LeaderElectionError(Exception):
    pass


class StaleTermError(LeaderElectionError):
    pass


class AlreadyVotedError(LeaderElectionError):
    pass


class NodeNotFoundError(LeaderElectionError):
    pass


class NotLeaderError(LeaderElectionError):
    pass
