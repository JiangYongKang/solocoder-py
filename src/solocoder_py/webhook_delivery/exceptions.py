from __future__ import annotations


class WebhookDeliveryError(Exception):
    pass


class InvalidWebhookTargetError(WebhookDeliveryError):
    pass


class InvalidUrlError(InvalidWebhookTargetError):
    pass


class InvalidSigningSecretError(InvalidWebhookTargetError):
    pass


class InvalidRetryStrategyError(WebhookDeliveryError):
    pass


class WebhookTargetNotFoundError(WebhookDeliveryError):
    pass


class SignatureVerificationError(WebhookDeliveryError):
    pass


class DeliveryFailedError(WebhookDeliveryError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class MaxRetriesExceededError(WebhookDeliveryError):
    def __init__(self, retries: int, message_id: str) -> None:
        self.retries = retries
        self.message_id = message_id
        super().__init__(
            f"Message {message_id} exceeded maximum retries ({retries})"
        )


class DeliveryNotReadyError(WebhookDeliveryError):
    def __init__(
        self,
        message_id: str,
        next_delivery_at: float,
        current_time: float,
    ) -> None:
        self.message_id = message_id
        self.next_delivery_at = next_delivery_at
        self.current_time = current_time
        wait_seconds = next_delivery_at - current_time
        super().__init__(
            f"Message {message_id} is not ready for delivery yet. "
            f"Next delivery available in {wait_seconds:.2f}s."
        )
