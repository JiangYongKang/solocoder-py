from solocoder_py.timeseries import MultiResolutionStore, TimeSeries


def make_timeseries() -> TimeSeries:
    return TimeSeries()


def make_multi_resolution_store() -> MultiResolutionStore:
    store = MultiResolutionStore()
    store.add_granularity("5min", 300, retention_seconds=2592000)
    store.add_granularity("hourly", 3600, retention_seconds=7776000)
    store.add_granularity("daily", 86400, retention_seconds=None)
    store.set_retention_policy("raw", retention_seconds=604800)
    return store
