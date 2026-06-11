from __future__ import annotations


class EloRatingError(Exception):
    pass


class PlayerNotFoundError(EloRatingError):
    pass


class MatchValidationError(EloRatingError):
    pass


class ProtectionPeriodViolationError(EloRatingError):
    pass


class ForfeitMatchError(EloRatingError):
    pass
