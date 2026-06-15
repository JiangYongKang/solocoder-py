from __future__ import annotations

import copy
from typing import Any, Iterable, Optional

from .datasource import InMemoryDataSource
from .exceptions import (
    InvalidConfigurationError,
    InvalidFieldError,
    MaskingError,
)
from .generalization import GeneralizationStrategy
from .kanonymity import KAnonymityChecker, KAnonymityReport
from .masking_strategy import MaskingStrategy
from .models import (
    DataRecord,
    FieldRule,
    GeneralizationConfig,
    MaskingConfig,
    MaskingStrategy as StrategyType,
    TokenizationConfig,
)
from .tokenization import TokenizationStrategy


class DataMaskingEngine:
    def __init__(
        self,
        rules: Optional[list[FieldRule]] = None,
        default_masking_config: Optional[MaskingConfig] = None,
        default_tokenization_config: Optional[TokenizationConfig] = None,
        tokenization_secret: Optional[bytes] = None,
    ) -> None:
        self._rules: dict[str, FieldRule] = {}
        self._masking_strategies: dict[str, MaskingStrategy] = {}
        self._tokenization_strategies: dict[str, TokenizationStrategy] = {}
        self._generalization_strategies: dict[str, GeneralizationStrategy] = {}
        self._default_masking_config = default_masking_config or MaskingConfig()
        self._default_tokenization_config = (
            default_tokenization_config or TokenizationConfig()
        )
        self._tokenization_secret = tokenization_secret

        if rules:
            for rule in rules:
                self.add_rule(rule)

    def add_rule(self, rule: FieldRule) -> "DataMaskingEngine":
        if rule.field_name in self._rules:
            raise InvalidConfigurationError(
                f"Rule for field '{rule.field_name}' already exists"
            )

        self._rules[rule.field_name] = rule
        self._initialize_strategy(rule)

        return self

    def remove_rule(self, field_name: str) -> bool:
        if field_name not in self._rules:
            return False

        del self._rules[field_name]
        self._masking_strategies.pop(field_name, None)
        self._tokenization_strategies.pop(field_name, None)
        self._generalization_strategies.pop(field_name, None)

        return True

    def get_rule(self, field_name: str) -> Optional[FieldRule]:
        return self._rules.get(field_name)

    def list_rules(self) -> list[FieldRule]:
        return list(self._rules.values())

    def _initialize_strategy(self, rule: FieldRule) -> None:
        field_name = rule.field_name
        config = rule.config or {}

        if rule.strategy == StrategyType.MASKING:
            masking_config = MaskingConfig(
                keep_prefix=config.get("keep_prefix", self._default_masking_config.keep_prefix),
                keep_suffix=config.get("keep_suffix", self._default_masking_config.keep_suffix),
                mask_char=config.get("mask_char", self._default_masking_config.mask_char),
            )
            self._masking_strategies[field_name] = MaskingStrategy(masking_config)

        elif rule.strategy == StrategyType.TOKENIZATION:
            token_config = TokenizationConfig(
                token_prefix=config.get(
                    "token_prefix", self._default_tokenization_config.token_prefix
                ),
                token_length=config.get(
                    "token_length", self._default_tokenization_config.token_length
                ),
                use_hash=config.get(
                    "use_hash", self._default_tokenization_config.use_hash
                ),
            )
            secret = self._tokenization_secret
            if "secret_key" in config:
                secret = config["secret_key"].encode() if isinstance(config["secret_key"], str) else config["secret_key"]
            self._tokenization_strategies[field_name] = TokenizationStrategy(
                token_config, secret_key=secret
            )

        elif rule.strategy == StrategyType.GENERALIZATION:
            field_type = config.get("field_type", "numeric")
            default_level = config.get("default_level", 0)

            if field_type == "age":
                self._generalization_strategies[field_name] = (
                    GeneralizationStrategy.create_age_generalizer(
                        default_level=default_level
                    )
                )
            elif field_type == "zipcode":
                zipcode_length = config.get("zipcode_length", 6)
                self._generalization_strategies[field_name] = (
                    GeneralizationStrategy.create_zipcode_generalizer(
                        default_level=default_level, zipcode_length=zipcode_length
                    )
                )
            elif field_type == "ip":
                self._generalization_strategies[field_name] = (
                    GeneralizationStrategy.create_ip_generalizer(
                        default_level=default_level
                    )
                )
            else:
                self._generalization_strategies[field_name] = GeneralizationStrategy(
                    field_type=field_type,
                    config=GeneralizationConfig(default_level=default_level),
                )

    def mask_record(self, record: DataRecord) -> DataRecord:
        masked_data = copy.deepcopy(record.data)
        masked_record = DataRecord(id=record.id, data=masked_data)

        for field_name, rule in self._rules.items():
            if field_name not in masked_data:
                continue

            original_value = masked_data[field_name]
            masked_value = self._apply_strategy(field_name, rule, original_value)
            masked_record.set(field_name, masked_value)

        return masked_record

    def _apply_strategy(
        self, field_name: str, rule: FieldRule, value: Any
    ) -> Any:
        try:
            if rule.strategy == StrategyType.MASKING:
                strategy = self._masking_strategies[field_name]
                return strategy.mask(value)

            elif rule.strategy == StrategyType.TOKENIZATION:
                strategy = self._tokenization_strategies[field_name]
                return strategy.tokenize(value)

            elif rule.strategy == StrategyType.GENERALIZATION:
                strategy = self._generalization_strategies[field_name]
                level = rule.config.get("level") if rule.config else None
                return strategy.generalize(value, level=level)

            else:
                raise InvalidConfigurationError(
                    f"Unknown strategy: {rule.strategy}"
                )

        except KeyError:
            raise InvalidFieldError(
                field_name, f"No strategy initialized for field"
            )
        except Exception as exc:
            raise MaskingError(
                f"Failed to mask field '{field_name}': {exc}"
            ) from exc

    def mask_datasource(
        self, datasource: InMemoryDataSource
    ) -> InMemoryDataSource:
        masked_records = []
        for record in datasource:
            masked_record = self.mask_record(record)
            masked_records.append(masked_record)
        return InMemoryDataSource(records=masked_records)

    def mask_records(
        self, records: Iterable[DataRecord]
    ) -> list[DataRecord]:
        return [self.mask_record(record) for record in records]

    def set_generalization_level(self, field_name: str, level: int) -> None:
        if field_name not in self._generalization_strategies:
            raise InvalidFieldError(
                field_name, "Field does not use generalization strategy"
            )
        self._generalization_strategies[field_name].set_level(level)

    def get_generalization_level(self, field_name: str) -> int:
        if field_name not in self._generalization_strategies:
            raise InvalidFieldError(
                field_name, "Field does not use generalization strategy"
            )
        return self._generalization_strategies[field_name].current_level

    def get_quasi_identifiers(self) -> list[str]:
        return [
            field_name
            for field_name, rule in self._rules.items()
            if rule.quasi_identifier
        ]

    def check_k_anonymity(
        self, records: Iterable[DataRecord], k: int
    ) -> KAnonymityReport:
        quasi_identifiers = self.get_quasi_identifiers()
        if not quasi_identifiers:
            raise InvalidConfigurationError(
                "No quasi-identifiers configured. "
                "Set quasi_identifier=True on at least one FieldRule."
            )
        checker = KAnonymityChecker(k=k, quasi_identifiers=quasi_identifiers)
        return checker.check(records)

    def clear_tokenization_cache(self, field_name: Optional[str] = None) -> None:
        if field_name:
            if field_name in self._tokenization_strategies:
                self._tokenization_strategies[field_name].clear()
        else:
            for strategy in self._tokenization_strategies.values():
                strategy.clear()

    def get_tokenization_strategy(
        self, field_name: str
    ) -> Optional[TokenizationStrategy]:
        return self._tokenization_strategies.get(field_name)

    def get_masking_strategy(self, field_name: str) -> Optional[MaskingStrategy]:
        return self._masking_strategies.get(field_name)

    def get_generalization_strategy(
        self, field_name: str
    ) -> Optional[GeneralizationStrategy]:
        return self._generalization_strategies.get(field_name)

    def __call__(self, record: DataRecord) -> DataRecord:
        return self.mask_record(record)


__all__ = [
    "DataMaskingEngine",
]
