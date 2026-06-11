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
    TcpRelay,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    REP_SUCCEEDED,
    UDP_MAX_DATAGRAM_SIZE,
    MAX_DOMAIN_LENGTH,
    Socks5Error,
    Socks5ProtocolError,
    build_greeting,
    build_auth_request,
    build_request,
    build_reply,
    build_udp_datagram,
    parse_method_selection,
    parse_auth_reply,
    parse_reply,
    parse_udp_datagram,
)
from .conftest import (
    make_no_auth_server,
    make_auth_server,
    make_full_server,
    handshake_no_auth,
    handshake_with_auth,
    do_connect,
)


class TestEmptyCredentialsNoAuthMode:
    def test_empty_credentials_with_no_auth(self):
        server = Socks5Server(
            auth_provider=InMemoryAuthProvider({}),
            supported_methods=[AUTH_NO_AUTH],
        )
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_AUTH
        assert session.state == SessionState.AUTHENTICATED

    def test_empty_credentials_auth_method_not_offered(self):
        server = Socks5Server(
            auth_provider=InMemoryAuthProvider({}),
            supported_methods=[AUTH_NO_AUTH],
        )
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == 0xFF

    def test_no_auth_server_ignores_auth_method_request(self):
        server = Socks5Server(
            auth_provider=InMemoryAuthProvider({}),
            supported_methods=[AUTH_NO_AUTH],
        )
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_AUTH
        assert session.state == SessionState.AUTHENTICATED


class TestUdpDatagramNearMaxSize:
    def test_large_udp_datagram_forward(self):
        server = make_full_server()
        server.dns_resolver.add_record("example.com", "93.184.216.34")

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")
        assert relay is not None

        header_size = 3 + 1 + 4 + 2
        payload_size = min(UDP_MAX_DATAGRAM_SIZE - header_size, 65000)
        large_payload = b"A" * payload_size

        target_addr = Socks5Address(atyp=ATYP_IPV4, host="93.184.216.34", port=53)
        datagram = UdpDatagram(rsv=0, frag=0, address=target_addr, data=large_payload)
        relay.send_from_client(datagram)

        forwarded = relay.recv_for_remote()
        assert len(forwarded) == 1
        assert forwarded[0][1] == large_payload

    def test_large_udp_datagram_reply(self):
        server = make_full_server()

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")

        large_payload = b"B" * 65000
        relay.send_from_remote(large_payload, ("93.184.216.34", 53))

        datagrams = relay.recv_for_client()
        assert len(datagrams) == 1
        assert datagrams[0].data == large_payload


class TestDomainNearMaxLength:
    def test_domain_exactly_255_chars(self):
        server = make_full_server()
        domain = "a" * 255
        server.dns_resolver.add_record(domain, "1.2.3.4")
        server.network.register_target("1.2.3.4", 80)

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host=domain, port=80)
        assert len(addr.host) == MAX_DOMAIN_LENGTH

        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED

    def test_domain_exceeding_255_chars_rejected(self):
        domain = "a" * 256
        with pytest.raises(ValueError, match="Domain name exceeds maximum length"):
            Socks5Address(atyp=ATYP_DOMAINNAME, host=domain, port=80)


class TestCrossedDataArrival:
    def test_client_and_remote_data_interleaved(self):
        server = make_no_auth_server()
        server.network.register_target("10.0.0.1", 8080)

        handshake_no_auth(server, "s1")
        do_connect(server, "s1", "10.0.0.1", 8080)

        relay = server.get_tcp_relay("s1")

        relay.send_from_client(b"client-1")
        relay.send_from_remote(b"remote-1")
        relay.send_from_client(b"client-2")
        relay.send_from_remote(b"remote-2")
        relay.send_from_client(b"client-3")
        relay.send_from_remote(b"remote-3")

        all_remote = relay.recv_for_remote()
        assert all_remote == b"client-1client-2client-3"

        all_client = relay.recv_for_client()
        assert all_client == b"remote-1remote-2remote-3"

    def test_udp_crossed_datagrams(self):
        server = make_full_server()

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")

        target1 = Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=53)
        target2 = Socks5Address(atyp=ATYP_IPV4, host="5.6.7.8", port=53)

        relay.send_from_client(UdpDatagram(rsv=0, frag=0, address=target1, data=b"out-1"))
        relay.send_from_remote(b"in-1", ("1.2.3.4", 53))
        relay.send_from_client(UdpDatagram(rsv=0, frag=0, address=target2, data=b"out-2"))
        relay.send_from_remote(b"in-2", ("5.6.7.8", 53))

        forwarded = relay.recv_for_remote()
        assert len(forwarded) == 2
        assert forwarded[0] == (("1.2.3.4", 53), b"out-1")
        assert forwarded[1] == (("5.6.7.8", 53), b"out-2")

        datagrams = relay.recv_for_client()
        assert len(datagrams) == 2
        assert datagrams[0].data == b"in-1"
        assert datagrams[1].data == b"in-2"


class TestProtocolParsingEdgeCases:
    def test_greeting_with_multiple_methods(self):
        server = make_auth_server()
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_AUTH

    def test_greeting_prefers_no_auth_when_both_offered(self):
        server = make_auth_server()
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD, AUTH_NO_AUTH])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_USERNAME_PASSWORD

    def test_auth_empty_username_password(self):
        server = make_auth_server({"": ""})
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parse_method_selection(response)

        auth_req = build_auth_request("", "")
        response = server.process_session("s1", auth_req)
        auth_rep = parse_auth_reply(response)
        assert auth_rep.success is True

    def test_udp_datagram_build_and_parse_roundtrip(self):
        addr = Socks5Address(atyp=ATYP_IPV4, host="10.0.0.1", port=53)
        datagram = UdpDatagram(rsv=0, frag=0, address=addr, data=b"test payload")
        raw = build_udp_datagram(datagram)
        parsed = parse_udp_datagram(raw)
        assert parsed.rsv == 0
        assert parsed.frag == 0
        assert parsed.address.host == "10.0.0.1"
        assert parsed.address.port == 53
        assert parsed.data == b"test payload"

    def test_udp_datagram_domain_address_roundtrip(self):
        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=80)
        datagram = UdpDatagram(rsv=0, frag=0, address=addr, data=b"hello")
        raw = build_udp_datagram(datagram)
        parsed = parse_udp_datagram(raw)
        assert parsed.address.atyp == ATYP_DOMAINNAME
        assert parsed.address.host == "example.com"
        assert parsed.address.port == 80
        assert parsed.data == b"hello"

    def test_socks5_address_port_validation(self):
        with pytest.raises(ValueError, match="Port out of range"):
            Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=65536)

        with pytest.raises(ValueError, match="Port out of range"):
            Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=-1)

    def test_socks5_address_invalid_atyp(self):
        with pytest.raises(ValueError, match="Invalid address type"):
            Socks5Address(atyp=0x05, host="test", port=80)

    def test_connection_refused_on_target(self):
        server = make_no_auth_server()
        handshake_no_auth(server, "s1")

        addr = Socks5Address(atyp=ATYP_IPV4, host="1.2.3.4", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == 0x05

    def test_session_process_after_close_raises(self):
        server = make_no_auth_server()
        session = server.create_session("s1")
        server.close_session("s1")

        with pytest.raises(Socks5Error, match="Session is closed"):
            session.process(build_greeting([AUTH_NO_AUTH]))
