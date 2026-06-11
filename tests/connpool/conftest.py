from solocoder_py.connpool import (
    ConnectionPool,
    ManualClock,
    PoolConfig,
    PoolWaitStrategy,
)


def make_clock() -> ManualClock:
    return ManualClock()


def make_config(**kwargs) -> PoolConfig:
    defaults = dict(
        max_size=5,
        wait_strategy=PoolWaitStrategy.FAIL,
        wait_timeout=1.0,
        idle_timeout=60.0,
        eviction_interval=0,
        max_lifetime=300.0,
        health_check_on_borrow=True,
        health_check_timeout=1.0,
    )
    defaults.update(kwargs)
    return PoolConfig(**defaults)


def make_pool(
    host: str = "localhost",
    port: int = 6379,
    config: PoolConfig | None = None,
    clock: ManualClock | None = None,
) -> tuple[ConnectionPool, ManualClock]:
    if clock is None:
        clock = make_clock()
    if config is None:
        config = make_config()
    pool = ConnectionPool(host=host, port=port, config=config, clock=clock)
    return pool, clock
