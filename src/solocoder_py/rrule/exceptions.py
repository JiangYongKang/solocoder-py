class RRuleError(Exception):
    pass


class InvalidFrequencyError(RRuleError):
    pass


class InvalidIntervalError(RRuleError):
    pass


class InvalidDateRangeError(RRuleError):
    pass


class InvalidCountError(RRuleError):
    pass
