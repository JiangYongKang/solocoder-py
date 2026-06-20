from __future__ import annotations

import pytest

from solocoder_py.config_parser import ConfigParser, parse_toml, parse_ini


@pytest.fixture
def make_parser():
    def _make_parser() -> ConfigParser:
        return ConfigParser()
    return _make_parser


@pytest.fixture
def sample_toml_text():
    return '''# Main configuration
title = "Example Config"

# Server settings
[server]
host = "localhost"
port = 8080
enabled = true

[server.tls]
cert_file = "/etc/ssl/cert.pem"
key_file = "/etc/ssl/key.pem"

# Database configuration
[[database]]
name = "primary"
host = "db1.example.com"
port = 5432

[[database]]
name = "secondary"
host = "db2.example.com"
port = 5432
'''


@pytest.fixture
def sample_ini_text():
    return '''; Sample INI config
# Global settings
global_setting = "hello"

[section1]
key1 = value1
key2 = 42
key3 = true

[section2]
; Another comment
float_val = 3.14
string_val = "a string"
'''
