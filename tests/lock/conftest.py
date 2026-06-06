from datetime import timedelta

from solocoder_py.lock import DistributedLockManager


def make_manager(
    default_lease_duration: timedelta = timedelta(seconds=30),
) -> DistributedLockManager:
    return DistributedLockManager(default_lease_duration=default_lease_duration)
