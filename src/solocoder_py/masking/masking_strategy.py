from __future__ import annotations

from typing import Any, Optional

from .exceptions import InvalidConfigurationError, InvalidValueError
from .models import MaskingConfig


class MaskingStrategy:
    def __init__(self, config: Optional[MaskingConfig] = None) -> None:
        self._config: MaskingConfig = config or MaskingConfig()

    @property
    def config(self) -> MaskingConfig:
        return self._config

    def mask(self, value: Any) -> str:
        if value is None:
            return ""

        str_value = str(value)
        if not str_value:
            return ""

        keep_prefix = self._config.keep_prefix
        keep_suffix = self._config.keep_suffix
        mask_char = self._config.mask_char

        total_length = len(str_value)

        if keep_prefix + keep_suffix >= total_length:
            return mask_char * total_length

        prefix = str_value[:keep_prefix] if keep_prefix > 0 else ""
        suffix = str_value[-keep_suffix:] if keep_suffix > 0 else ""
        masked_length = total_length - keep_prefix - keep_suffix
        masked_part = mask_char * masked_length

        return prefix + masked_part + suffix

    def mask_phone(self, phone: str) -> str:
        if phone is None:
            return ""
        str_phone = str(phone).strip()
        if not str_phone:
            return ""
        if len(str_phone) < 7:
            return "*" * len(str_phone)
        return str_phone[:3] + "*" * (len(str_phone) - 7) + str_phone[-4:]

    def mask_id_card(self, id_card: str) -> str:
        if id_card is None:
            return ""
        str_id = str(id_card).strip()
        if not str_id:
            return ""
        if len(str_id) < 2:
            return "*" * len(str_id)
        return str_id[0] + "*" * (len(str_id) - 2) + str_id[-1]

    def mask_email(self, email: str) -> str:
        if email is None:
            return ""
        str_email = str(email).strip()
        if not str_email:
            return ""
        if "@" not in str_email:
            return "*" * len(str_email)

        username, domain = str_email.split("@", 1)
        if len(username) <= 2:
            masked_username = "*" * len(username)
        else:
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]

        return masked_username + "@" + domain

    def __call__(self, value: Any) -> str:
        return self.mask(value)


__all__ = [
    "MaskingStrategy",
]
