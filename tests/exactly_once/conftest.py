from solocoder_py.exactly_once import (
    CheckpointStore,
    Clock,
    DedupStore,
    ExactlyOnceProcessor,
    InMemoryMessageSource,
    ManualClock,
    SystemClock,
)


def make_clock(start_time: float = 0.0) -> ManualClock:
    return ManualClock(start_time=start_time)


def make_message_source(
    clock: Clock | None = None,
) -> InMemoryMessageSource:
    return InMemoryMessageSource(
        _clock=clock if clock is not None else SystemClock()
    )


def make_dedup_store(
    max_size: int | None = None,
    clock: Clock | None = None,
) -> DedupStore:
    return DedupStore(
        max_size=max_size,
        _clock=clock if clock is not None else SystemClock(),
    )


def make_checkpoint_store(
    clock: Clock | None = None,
) -> CheckpointStore:
    return CheckpointStore(
        _clock=clock if clock is not None else SystemClock()
    )


def make_processor(
    max_dedup_size: int | None = None,
    auto_commit_interval: int = 1,
    clock: Clock | None = None,
) -> ExactlyOnceProcessor:
    effective_clock = clock if clock is not None else SystemClock()
    return ExactlyOnceProcessor(
        message_source=InMemoryMessageSource(_clock=effective_clock),
        dedup_store=DedupStore(
            max_size=max_dedup_size, _clock=effective_clock
        ),
        checkpoint_store=CheckpointStore(_clock=effective_clock),
        _clock=effective_clock,
        _auto_commit_interval=auto_commit_interval,
    )


def make_processor_with_components(
    message_source: InMemoryMessageSource,
    dedup_store: DedupStore,
    checkpoint_store: CheckpointStore,
    auto_commit_interval: int = 1,
    clock: Clock | None = None,
) -> ExactlyOnceProcessor:
    effective_clock = clock if clock is not None else SystemClock()
    return ExactlyOnceProcessor(
        message_source=message_source,
        dedup_store=dedup_store,
        checkpoint_store=checkpoint_store,
        _clock=effective_clock,
        _auto_commit_interval=auto_commit_interval,
    )
