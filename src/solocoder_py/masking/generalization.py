from __future__ import annotations

from typing import Any, Optional

from .exceptions import GeneralizationError, InvalidConfigurationError
from .models import GeneralizationConfig, GeneralizationLevel


def generalize_age(value: Any, level: int, step_years: Optional[int] = None) -> str:
    if value is None:
        return ""

    try:
        age = int(value)
    except (ValueError, TypeError):
        return str(value)

    if age < 0:
        return "invalid"

    if step_years is not None and step_years > 0:
        return _generalize_age_dynamic(age, level, step_years)

    if level == 0:
        return str(age)
    elif level == 1:
        if age < 18:
            return "<18"
        elif age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65+"
    elif level == 2:
        if age < 18:
            return "<18"
        elif age < 35:
            return "18-34"
        elif age < 55:
            return "35-54"
        else:
            return "55+"
    elif level == 3:
        if age < 18:
            return "minor"
        else:
            return "adult"
    elif level >= 4:
        return "*"
    else:
        return str(age)


def _generalize_age_dynamic(age: int, level: int, step: int) -> str:
    if level == 0:
        return str(age)
    elif level == 1:
        start = (age // step) * step
        end = start + step
        return f"{start}-{end}"
    elif level == 2:
        step2 = step * 2
        start = (age // step2) * step2
        end = start + step2
        return f"{start}-{end}"
    elif level == 3:
        if age < 18:
            return "minor"
        else:
            return "adult"
    elif level >= 4:
        return "*"
    else:
        return str(age)


def generalize_zipcode(value: Any, level: int) -> str:
    if value is None:
        return ""

    zip_str = str(value).strip()
    if not zip_str:
        return ""

    length = len(zip_str)
    if level >= length:
        return "*" * length

    keep_length = length - level
    return zip_str[:keep_length] + "*" * level


def generalize_ip(value: Any, level: int) -> str:
    if value is None:
        return ""

    ip_str = str(value).strip()
    if not ip_str:
        return ""

    parts = ip_str.split(".")
    if len(parts) != 4:
        return ip_str

    try:
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return ip_str
    except ValueError:
        return ip_str

    if level == 0:
        return ip_str
    elif level == 1:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.*"
    elif level == 2:
        return f"{parts[0]}.{parts[1]}.*.*"
    elif level == 3:
        return f"{parts[0]}.*.*.*"
    elif level >= 4:
        return "*.*.*.*"
    else:
        return ip_str


def generalize_numeric_range(
    value: Any,
    level: int,
    bins: Optional[list[tuple[int, int, str]]] = None,
) -> str:
    if value is None:
        return ""

    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    default_bins = [
        (float("-inf"), 10, "<10"),
        (10, 20, "10-19"),
        (20, 30, "20-29"),
        (30, 50, "30-49"),
        (50, 100, "50-99"),
        (100, float("inf"), "100+"),
    ]

    active_bins = bins or default_bins

    if level == 0:
        return str(num) if num != int(num) else str(int(num))
    elif level == 1:
        for low, high, label in active_bins:
            if low <= num < high:
                return label
        return str(num)
    elif level == 2:
        if num < 50:
            return "<50"
        else:
            return "50+"
    elif level >= 3:
        return "*"
    else:
        return str(num)


def generalize_category(value: Any, level: int) -> str:
    if value is None:
        return ""

    cat = str(value).strip()
    if not cat:
        return ""

    if level == 0:
        return cat
    elif level == 1:
        if cat.lower() in {"male", "female"}:
            return cat.lower()
        return "other"
    elif level == 2:
        return "person"
    elif level >= 3:
        return "*"
    else:
        return cat


class GeneralizationStrategy:
    def __init__(
        self,
        config: Optional[GeneralizationConfig] = None,
        field_type: str = "numeric",
    ) -> None:
        self._config: GeneralizationConfig = config or GeneralizationConfig()
        self._field_type: str = field_type
        self._current_level: int = self._config.default_level

    @property
    def config(self) -> GeneralizationConfig:
        return self._config

    @property
    def current_level(self) -> int:
        return self._current_level

    @property
    def max_level(self) -> int:
        return self._config.get_max_level()

    def set_level(self, level: int) -> None:
        if level < 0:
            raise InvalidConfigurationError(f"Level cannot be negative: {level}")
        if self._config.levels and level > self.max_level:
            raise InvalidConfigurationError(
                f"Level {level} exceeds max level {self.max_level}"
            )
        self._current_level = level

    def generalize(self, value: Any, level: Optional[int] = None) -> Any:
        target_level = level if level is not None else self._current_level

        if self._config.levels:
            max_level = len(self._config.levels) - 1
            if target_level < 0:
                raise GeneralizationError(
                    f"Level {target_level} cannot be negative"
                )
            if target_level > max_level:
                target_level = max_level
            level_config = self._config.levels[target_level]
            return level_config.generalize_func(value)

        return self._default_generalize(value, target_level)

    def _default_generalize(self, value: Any, level: int) -> Any:
        if self._field_type == "age":
            return generalize_age(value, level)
        elif self._field_type == "zipcode":
            return generalize_zipcode(value, level)
        elif self._field_type == "ip":
            return generalize_ip(value, level)
        elif self._field_type == "numeric":
            return generalize_numeric_range(value, level)
        elif self._field_type == "category":
            return generalize_category(value, level)
        else:
            return generalize_numeric_range(value, level)

    def __call__(self, value: Any, level: Optional[int] = None) -> Any:
        return self.generalize(value, level)

    @classmethod
    def create_age_generalizer(
        cls, default_level: int = 0, step_years: Optional[int] = None
    ) -> "GeneralizationStrategy":
        if step_years and step_years > 0:
            level1_desc = f"{step_years}-year ranges"
            level2_desc = f"{step_years * 2}-year ranges"
        else:
            level1_desc = "10-year ranges"
            level2_desc = "20-year ranges"

        levels = [
            GeneralizationLevel(
                level=0,
                description="Exact age",
                generalize_func=lambda v: generalize_age(v, 0, step_years=step_years),
            ),
            GeneralizationLevel(
                level=1,
                description=level1_desc,
                generalize_func=lambda v: generalize_age(v, 1, step_years=step_years),
            ),
            GeneralizationLevel(
                level=2,
                description=level2_desc,
                generalize_func=lambda v: generalize_age(v, 2, step_years=step_years),
            ),
            GeneralizationLevel(
                level=3,
                description="Adult/minor",
                generalize_func=lambda v: generalize_age(v, 3, step_years=step_years),
            ),
            GeneralizationLevel(
                level=4,
                description="Full suppression",
                generalize_func=lambda v: generalize_age(v, 4, step_years=step_years),
            ),
        ]
        return cls(
            config=GeneralizationConfig(levels=levels, default_level=default_level),
            field_type="age",
        )

    @classmethod
    def create_zipcode_generalizer(
        cls, default_level: int = 0, zipcode_length: int = 6
    ) -> "GeneralizationStrategy":
        levels = []
        for lvl in range(zipcode_length + 1):
            levels.append(
                GeneralizationLevel(
                    level=lvl,
                    description=f"Mask {lvl} trailing digits",
                    generalize_func=lambda v, level=lvl: generalize_zipcode(v, level),
                )
            )
        return cls(
            config=GeneralizationConfig(levels=levels, default_level=default_level),
            field_type="zipcode",
        )

    @classmethod
    def create_ip_generalizer(
        cls, default_level: int = 0
    ) -> "GeneralizationStrategy":
        levels = [
            GeneralizationLevel(
                level=0,
                description="Full IP address",
                generalize_func=lambda v: generalize_ip(v, 0),
            ),
            GeneralizationLevel(
                level=1,
                description="Mask last octet",
                generalize_func=lambda v: generalize_ip(v, 1),
            ),
            GeneralizationLevel(
                level=2,
                description="Mask last two octets",
                generalize_func=lambda v: generalize_ip(v, 2),
            ),
            GeneralizationLevel(
                level=3,
                description="Mask last three octets",
                generalize_func=lambda v: generalize_ip(v, 3),
            ),
            GeneralizationLevel(
                level=4,
                description="Full suppression",
                generalize_func=lambda v: generalize_ip(v, 4),
            ),
        ]
        return cls(
            config=GeneralizationConfig(levels=levels, default_level=default_level),
            field_type="ip",
        )


__all__ = [
    "GeneralizationStrategy",
    "generalize_age",
    "generalize_zipcode",
    "generalize_ip",
    "generalize_numeric_range",
    "generalize_category",
]
