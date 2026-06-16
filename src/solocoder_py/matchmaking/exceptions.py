from __future__ import annotations


class MatchmakingError(Exception):
    pass


class DuplicatePlayerError(MatchmakingError):
    pass


class InvalidSkillRatingError(MatchmakingError):
    pass


class MatchNotFoundError(MatchmakingError):
    pass


class NoCandidateError(MatchmakingError):
    pass


class TeamSizeMismatchError(MatchmakingError):
    pass
