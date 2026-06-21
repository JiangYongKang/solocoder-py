from __future__ import annotations

import math

from .exceptions import (
    InvalidLearningRateError,
    InvalidSampleError,
    NotFittedError,
)


class SimpleLinearRegression:
    _BETA1 = 0.5
    _BETA2 = 0.999
    _EPS = 1e-8
    _CLIP_FACTOR = 10.0

    def __init__(
        self,
        learning_rate: float,
    ) -> None:
        if learning_rate < 0:
            raise InvalidLearningRateError(
                "learning rate must be non-negative"
            )
        if math.isnan(learning_rate) or math.isinf(learning_rate):
            raise InvalidLearningRateError(
                "learning rate must be a finite number"
            )
        self._learning_rate = learning_rate
        self._w = 0.0
        self._b = 0.0
        self._m_w = 0.0
        self._v_w = 0.0
        self._m_b = 0.0
        self._v_b = 0.0
        self._t = 0
        self._n = 0
        self._sum_x = 0.0
        self._sum_y = 0.0
        self._sum_x2 = 0.0
        self._sum_y2 = 0.0
        self._sum_xy = 0.0
        self._fitted = False

    @property
    def learning_rate(self) -> float:
        return self._learning_rate

    @property
    def w(self) -> float:
        return self._w

    @property
    def b(self) -> float:
        return self._b

    @property
    def n_samples(self) -> int:
        return self._n

    @staticmethod
    def _validate_sample(x: float, y: float) -> None:
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise InvalidSampleError("x and y must be numeric values")
        if math.isnan(x) or math.isnan(y):
            raise InvalidSampleError("sample contains NaN value")
        if math.isinf(x) or math.isinf(y):
            raise InvalidSampleError("sample contains Inf value")

    def update(self, x: float, y: float) -> None:
        self._validate_sample(x, y)
        x = float(x)
        y = float(y)

        y_pred = self._w * x + self._b
        error = y_pred - y

        dw = error * x
        db = error

        self._t += 1
        self._m_w = self._BETA1 * self._m_w + (1 - self._BETA1) * dw
        self._v_w = self._BETA2 * self._v_w + (1 - self._BETA2) * dw * dw
        self._m_b = self._BETA1 * self._m_b + (1 - self._BETA1) * db
        self._v_b = self._BETA2 * self._v_b + (1 - self._BETA2) * db * db

        bias_correction1 = 1 - self._BETA1 ** self._t
        bias_correction2 = 1 - self._BETA2 ** self._t

        m_hat_w = self._m_w / bias_correction1
        v_hat_w = self._v_w / bias_correction2
        m_hat_b = self._m_b / bias_correction1
        v_hat_b = self._v_b / bias_correction2

        max_grad_w = self._CLIP_FACTOR * math.sqrt(v_hat_w)
        max_grad_b = self._CLIP_FACTOR * math.sqrt(v_hat_b)

        clipped_m_w = max(min(m_hat_w, max_grad_w), -max_grad_w)
        clipped_m_b = max(min(m_hat_b, max_grad_b), -max_grad_b)

        self._w -= self._learning_rate * clipped_m_w
        self._b -= self._learning_rate * clipped_m_b

        self._n += 1
        self._sum_x += x
        self._sum_y += y
        self._sum_x2 += x * x
        self._sum_y2 += y * y
        self._sum_xy += x * y
        self._fitted = True

    def predict(self, x: float) -> float:
        if not self._fitted:
            raise NotFittedError(
                "model has not been fitted yet; call update() first"
            )
        if not isinstance(x, (int, float)):
            raise InvalidSampleError("x must be a numeric value")
        if math.isnan(x) or math.isinf(x):
            raise InvalidSampleError("x must be a finite number")
        return self._w * float(x) + self._b

    def r2_score(self) -> float:
        if not self._fitted:
            raise NotFittedError(
                "model has not been fitted yet; call update() first"
            )
        if self._n < 2:
            return 0.0

        ss_tot = self._sum_y2 - (self._sum_y * self._sum_y) / self._n
        if ss_tot == 0:
            return 0.0

        ss_res = (
            self._sum_y2
            + self._w * self._w * self._sum_x2
            + self._n * self._b * self._b
            - 2 * self._w * self._sum_xy
            - 2 * self._b * self._sum_y
            + 2 * self._w * self._b * self._sum_x
        )

        return 1.0 - ss_res / ss_tot
