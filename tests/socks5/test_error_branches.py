from __future__ import annotations

import struct
import pytest

from solocoder_py.socks5 import (
    Socks5Server,
    InMemoryDnsResolver,
    InMemoryNetwork,
    InMemoryAuthProvider,
    NoAuthAuthProvider,
    Socks5Session,
    SessionState,
    Socks5Address,
    UdpDatagram,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    ATYP_IPV6,
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    AUTH_NO_ACCEPTABLE,
    REP_SUCCEEDED,
    REP_GENERAL_FAILURE,
    REP_HOST_UNREACHABLE,
    REP_CONNECTION_REFUSED,
    REP_COMMAND_NOT_SUPPORTED,
    REP_ADDRESS_TYPE_NOT_SUPPORTED,
    UDP_MAX_DATAGRAM_SIZE,
    MAX_DOMAIN_LENGTH,
    Socks5Error,
    Socks5HandshakeError,
    Socks5AuthError,
    Socks5RequestError,
    Socks5ProtocolError,
    Socks5ResolutionError,
    build_greeting,
    build_auth_request,
    build_request,
    build_reply,
    build_udp_datagram,
    parse_method_selection,
    parse_auth_reply,
    parse_reply,
)
from .conftest import (
    make_no_auth_server,
    make_auth_server,
    make_full_server,
    handshake_no_auth,
    handshake_with_auth,
    do_connect,
)


class TestAuthFailure:
    def test_wrong_password(self):
        server = make_auth_server({"alice": "password123"})
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parse_method_selection(response)

        auth_req = build_auth_request("alice", "wrong_password")
        response = server.process_session("s1", auth_req)
        auth_rep = parse_auth_reply(response)
        assert auth_rep.success is False
        assert session.state == SessionState.CLOSED

    def test_wrong_username(self):
        server = make_auth_server({"alice": "password123"})
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parse_method_selection(response)

        auth_req = build_auth_request("nonexistent", "password123")
        response = server.process_session("s1", auth_req)
        auth_rep = parse_auth_reply(response)
        assert auth_rep.success is False
        assert session.state == SessionState.CLOSED

    def test_auth_failure_closes_session(self):
        server = make_auth_server({"alice": "password123"})
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        server.process_session("s1", greeting)

        auth_req = build_auth_request("alice", "bad")
        server.process_session("s1", auth_req)

        with pytest.raises(Socks5Error, match="Session is closed"):
            session.process(b"\x05\x01\x00\x01\x01\x02\x03\x04\x00\x50")


class TestUdpRelayControlConnectionBinding:
    def test_udp_relay_closes_on_control_disconnect(self):
        server = make_full_server()

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")
        assert relay is not None
        assert relay.active is True

        server.close_session("s1")

        assert relay.active is False

    def test_udp_relay_unavailable_after_close(self):
        server = make_full_server()

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")

        server.close_session("s1")

        with pytest.raises(Socks5Error, match="UDP association is not active"):
            relay.send_from_client(
                UdpDatagram(
                    rsv=0,
                    frag=0,
                    address=Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=53),
                    data=b"test",
                )
            )


class TestDomainResolutionFailure:
    def test_unresolvable_domain_returns_host_unreachable(self):
        server = make_full_server()

        session = handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="nonexistent.example.com", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_HOST_UNREACHABLE
        assert session.state == SessionState.CLOSED


class TestUnsupportedAuthMethod:
    def test_no_acceptable_method(self):
        server = make_auth_server({"alice": "password123"})
        session = server.create_session("s1")

        greeting = build_greeting([0x03, 0x04, 0x05])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_ACCEPTABLE
        assert session.state == SessionState.CLOSED

    def test_no_auth_not_in_supported(self):
        server = Socks5Server(
            auth_provider=InMemoryAuthProvider({"alice": "pass"}),
            supported_methods=[AUTH_USERNAME_PASSWORD],
        )
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_ACCEPTABLE
        assert session.state == SessionState.CLOSED


class TestUnsupportedCommand:
    def test_bind_command_not_supported(self):
        server = make_no_auth_server()
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=80)
        request = build_request(0x02, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_COMMAND_NOT_SUPPORTED

    def test_unknown_command_not_supported(self):
        server = make_no_auth_server()
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=80)
        request = build_request(0xFF, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_COMMAND_NOT_SUPPORTED


class TestTargetConnectionFailure:
    def test_connection_refused(self):
        server = make_no_auth_server()
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_CONNECTION_REFUSED
        assert session.state == SessionState.CLOSED if (session := server.get_session("s1")) else True


class TestUnsupportedAddressType:
    def test_ipv6_not_supported_when_excluded(self):
        server = Socks5Server(
            auth_provider=NoAuthAuthProvider(),
            supported_methods=[AUTH_NO_AUTH],
            supported_atyps=[ATYP_IPV4],
        )
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_IPV6, host="::1", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_ADDRESS_TYPE_NOT_SUPPORTED

    def test_domain_not_supported_when_excluded(self):
        server = Socks5Server(
            auth_provider=NoAuthAuthProvider(),
            supported_methods=[AUTH_NO_AUTH],
            supported_atyps=[ATYP_IPV4],
        )
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_ADDRESS_TYPE_NOT_SUPPORTED
