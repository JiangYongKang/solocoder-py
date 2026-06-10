from __future__ import annotations

from typing import Mapping, Optional

from .exceptions import (
    InvalidRetryStrategyError,
    InvalidSigningSecretError,
    InvalidUrlError,
    WebhookTargetNotFoundError,
)
from .models import (
    RetryStrategy,
    WebhookTarget,
    _is_valid_url,
    generate_target_id,
)


class WebhookTargetRepository:
    def __init__(self) -> None:
        self._targets: dict[str, WebhookTarget] = {}

    def register(
        self,
        url: str,
        signing_secret: str,
        retry_strategy: Optional[RetryStrategy] = None,
        target_id: Optional[str] = None,
    ) -> WebhookTarget:
        if not _is_valid_url(url):
            raise InvalidUrlError(f"Invalid webhook URL: {url}")
        if not isinstance(signing_secret, str) or not signing_secret:
            raise InvalidSigningSecretError(
                "signing_secret must be a non-empty string"
            )

        tid = target_id or generate_target_id()

        if tid in self._targets:
            raise ValueError(f"Target with id {tid} already exists")

        strategy = retry_strategy or RetryStrategy()

        target = WebhookTarget(
            id=tid,
            url=url,
            signing_secret=signing_secret,
            retry_strategy=strategy,
            is_active=True,
        )
        self._targets[tid] = target
        return target

    def update(
        self,
        target_id: str,
        url: Optional[str] = None,
        signing_secret: Optional[str] = None,
        retry_strategy: Optional[RetryStrategy] = None,
        is_active: Optional[bool] = None,
    ) -> WebhookTarget:
        target = self.get(target_id)

        if url is not None:
            if not _is_valid_url(url):
                raise InvalidUrlError(f"Invalid webhook URL: {url}")
            target = WebhookTarget(
                id=target.id,
                url=url,
                signing_secret=target.signing_secret,
                retry_strategy=target.retry_strategy,
                is_active=target.is_active,
            )

        if signing_secret is not None:
            if not isinstance(signing_secret, str) or not signing_secret:
                raise InvalidSigningSecretError(
                    "signing_secret must be a non-empty string"
                )
            target = WebhookTarget(
                id=target.id,
                url=target.url,
                signing_secret=signing_secret,
                retry_strategy=target.retry_strategy,
                is_active=target.is_active,
            )

        if retry_strategy is not None:
            if not isinstance(retry_strategy, RetryStrategy):
                raise InvalidRetryStrategyError(
                    "retry_strategy must be a RetryStrategy instance"
                )
            target = WebhookTarget(
                id=target.id,
                url=target.url,
                signing_secret=target.signing_secret,
                retry_strategy=retry_strategy,
                is_active=target.is_active,
            )

        if is_active is not None:
            target = WebhookTarget(
                id=target.id,
                url=target.url,
                signing_secret=target.signing_secret,
                retry_strategy=target.retry_strategy,
                is_active=is_active,
            )

        self._targets[target_id] = target
        return target

    def delete(self, target_id: str) -> None:
        if target_id not in self._targets:
            raise WebhookTargetNotFoundError(
                f"Webhook target not found: {target_id}"
            )
        del self._targets[target_id]

    def get(self, target_id: str) -> WebhookTarget:
        if target_id not in self._targets:
            raise WebhookTargetNotFoundError(
                f"Webhook target not found: {target_id}"
            )
        return self._targets[target_id]

    def list_all(self) -> list[WebhookTarget]:
        return list(self._targets.values())

    def list_active(self) -> list[WebhookTarget]:
        return [t for t in self._targets.values() if t.is_active]

    def exists(self, target_id: str) -> bool:
        return target_id in self._targets

    def count(self) -> int:
        return len(self._targets)
