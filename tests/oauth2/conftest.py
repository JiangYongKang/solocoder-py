from datetime import timedelta

from solocoder_py.oauth2 import OAuth2StateManager


def make_manager(
    default_code_expires_in: timedelta = timedelta(minutes=10),
) -> OAuth2StateManager:
    return OAuth2StateManager(default_code_expires_in=default_code_expires_in)
