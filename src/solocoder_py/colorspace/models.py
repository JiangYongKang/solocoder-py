from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


class ColorSpaceError(Exception):
    pass


class InvalidRGBError(ColorSpaceError):
    def __init__(self, r: float, g: float, b: float, message: Optional[str] = None):
        self.r = r
        self.g = g
        self.b = b
        if message is None:
            message = f"Invalid RGB values: r={r}, g={g}, b={b}"
        super().__init__(message)


class InvalidHexError(ColorSpaceError):
    def __init__(self, hex_str: str, message: Optional[str] = None):
        self.hex_str = hex_str
        if message is None:
            message = f"Invalid HEX color string: {hex_str!r}"
        super().__init__(message)


class InvalidHSLError(ColorSpaceError):
    def __init__(self, h: float, s: float, l: float, message: Optional[str] = None):
        self.h = h
        self.s = s
        self.l = l
        if message is None:
            message = f"Invalid HSL values: h={h}, s={s}, l={l}"
        super().__init__(message)


class InvalidHSVError(ColorSpaceError):
    def __init__(self, h: float, s: float, v: float, message: Optional[str] = None):
        self.h = h
        self.s = s
        self.v = v
        if message is None:
            message = f"Invalid HSV values: h={h}, s={s}, v={v}"
        super().__init__(message)


class InvalidAlphaError(ColorSpaceError):
    def __init__(self, alpha: float, message: Optional[str] = None):
        self.alpha = alpha
        if message is None:
            message = f"Invalid alpha value: {alpha}. Must be in [0, 1]."
        super().__init__(message)


def _clamp(value: float, lo: float, hi: float) -> float:
    if math.isnan(value):
        return lo
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _normalize_hue(h: float) -> float:
    if math.isnan(h):
        return 0.0
    h = h % 360.0
    if h < 0:
        h += 360.0
    return h


@dataclass(frozen=True)
class RGB:
    r: float
    g: float
    b: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "r", _clamp(float(self.r), 0.0, 255.0))
        object.__setattr__(self, "g", _clamp(float(self.g), 0.0, 255.0))
        object.__setattr__(self, "b", _clamp(float(self.b), 0.0, 255.0))
        object.__setattr__(self, "alpha", _clamp(float(self.alpha), 0.0, 1.0))

    @classmethod
    def from_float(cls, r: float, g: float, b: float, alpha: float = 1.0) -> "RGB":
        return cls(r * 255.0, g * 255.0, b * 255.0, alpha)

    @property
    def r_float(self) -> float:
        return self.r / 255.0

    @property
    def g_float(self) -> float:
        return self.g / 255.0

    @property
    def b_float(self) -> float:
        return self.b / 255.0

    def to_int(self) -> tuple[int, int, int]:
        return (round(self.r), round(self.g), round(self.b))

    def to_hsl(self) -> "HSL":
        from .converter import rgb_to_hsl
        return rgb_to_hsl(self)

    def to_hsv(self) -> "HSV":
        from .converter import rgb_to_hsv
        return rgb_to_hsv(self)

    def to_hex(self) -> "HEX":
        from .converter import rgb_to_hex
        return rgb_to_hex(self)


@dataclass(frozen=True)
class HSL:
    h: float
    s: float
    l: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "h", _normalize_hue(float(self.h)))
        object.__setattr__(self, "s", _clamp(float(self.s), 0.0, 100.0))
        object.__setattr__(self, "l", _clamp(float(self.l), 0.0, 100.0))
        object.__setattr__(self, "alpha", _clamp(float(self.alpha), 0.0, 1.0))

    def to_rgb(self) -> "RGB":
        from .converter import hsl_to_rgb
        return hsl_to_rgb(self)

    def to_hsv(self) -> "HSV":
        from .converter import hsl_to_hsv
        return hsl_to_hsv(self)

    def to_hex(self) -> "HEX":
        return self.to_rgb().to_hex()


@dataclass(frozen=True)
class HSV:
    h: float
    s: float
    v: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "h", _normalize_hue(float(self.h)))
        object.__setattr__(self, "s", _clamp(float(self.s), 0.0, 100.0))
        object.__setattr__(self, "v", _clamp(float(self.v), 0.0, 100.0))
        object.__setattr__(self, "alpha", _clamp(float(self.alpha), 0.0, 1.0))

    def to_rgb(self) -> "RGB":
        from .converter import hsv_to_rgb
        return hsv_to_rgb(self)

    def to_hsl(self) -> "HSL":
        from .converter import hsv_to_hsl
        return hsv_to_hsl(self)

    def to_hex(self) -> "HEX":
        return self.to_rgb().to_hex()


@dataclass(frozen=True)
class HEX:
    value: str

    def __post_init__(self) -> None:
        normalized = self._normalize(self.value)
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _normalize(hex_str: str) -> str:
        if not isinstance(hex_str, str):
            raise InvalidHexError(hex_str)

        s = hex_str.strip()

        if s.startswith("#"):
            s = s[1:]
        else:
            raise InvalidHexError(hex_str, f"HEX string must start with '#': {hex_str!r}")

        valid_chars = set("0123456789abcdefABCDEF")
        for ch in s:
            if ch not in valid_chars:
                raise InvalidHexError(hex_str, f"HEX string contains invalid character: {ch!r}")

        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        elif len(s) == 4:
            s = "".join(c * 2 for c in s)
        elif len(s) == 6:
            pass
        elif len(s) == 8:
            pass
        else:
            raise InvalidHexError(
                hex_str,
                f"HEX string must have 3, 4, 6, or 8 hex digits after '#', got {len(s)}",
            )

        return "#" + s.lower()

    @property
    def has_alpha(self) -> bool:
        return len(self.value) == 9

    def to_rgb(self) -> RGB:
        from .converter import hex_to_rgb
        return hex_to_rgb(self)

    def to_hsl(self) -> HSL:
        return self.to_rgb().to_hsl()

    def to_hsv(self) -> HSV:
        return self.to_rgb().to_hsv()

    def __str__(self) -> str:
        return self.value


__all__ = [
    "ColorSpaceError",
    "InvalidRGBError",
    "InvalidHexError",
    "InvalidHSLError",
    "InvalidHSVError",
    "InvalidAlphaError",
    "RGB",
    "HSL",
    "HSV",
    "HEX",
    "_clamp",
    "_normalize_hue",
]
