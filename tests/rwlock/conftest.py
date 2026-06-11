from solocoder_py.rwlock import ManualScheduler, RWLock


def make_scheduler() -> ManualScheduler:
    return ManualScheduler()


def make_lock(scheduler: ManualScheduler) -> RWLock:
    return RWLock(scheduler=scheduler)
