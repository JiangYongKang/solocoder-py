from typing import Optional

from solocoder_py.singleflight import Clock, SingleFlight


def make_sf(clock: Optional[Clock] = None) -> SingleFlight:
    if clock is not None:
        return SingleFlight(clock=clock)
    return SingleFlight()
