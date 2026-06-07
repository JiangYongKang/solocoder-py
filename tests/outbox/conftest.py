from solocoder_py.outbox import OutboxRepository


def make_repository(
    default_max_retries: int = 3,
    default_retry_delay_seconds: int = 5,
) -> OutboxRepository:
    return OutboxRepository(
        default_max_retries=default_max_retries,
        default_retry_delay_seconds=default_retry_delay_seconds,
    )
