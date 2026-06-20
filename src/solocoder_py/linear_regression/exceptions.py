from __future__ import annotations


class LinearRegressionError(Exception):
    pass


class InvalidLearningRateError(LinearRegressionError):
    pass


class InvalidSampleError(LinearRegressionError):
    pass


class NotFittedError(LinearRegressionError):
    pass
