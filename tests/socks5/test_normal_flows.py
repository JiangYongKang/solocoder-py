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
    UdpRelay,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    REP_SUCCEEDED,
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


class TestNoAuthConnectAndRelay:
    def test_no_auth_handshake_and_connect(self):
        server = make_no_auth_server()
        assert isinstance(server.network, InMemoryNetwork)
        server.network.register_target("1.2.3.4", 80)

        session = handshake_no_auth(server, "s1")
        assert session.state == SessionState.AUTHENTICATED

        response = do_connect(server, "s1", "1.2.3.4", 80)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED
        assert session.state == SessionState.RELAYING

    def test_no_auth_relay_data_bidirectional(self):
        server = make_no_auth_server()
        target_conn = server.network.register_target("10.0.0.1", 8080)

        session = handshake_no_auth(server, "s1")
        do_connect(server, "s1", "10.0.0.1", 8080)

        relay = server.get_tcp_relay("s1")
        assert relay is not None

        relay.send_from_client(b"Hello, remote!")
        received = relay.recv_for_remote()
        assert received == b"Hello, remote!"

        relay.send_from_remote(b"Hi, client!")
        client_data = relay.recv_for_client()
        assert client_data == b"Hi, client!"

    def test_no_auth_multiple_data_exchanges(self):
        server = make_no_auth_server()
        target_conn = server.network.register_target("10.0.0.1", 8080)

        session = handshake_no_auth(server, "s1")
        do_connect(server, "s1", "10.0.0.1", 8080)

        relay = server.get_tcp_relay("s1")
        assert relay is not None

        for i in range(5):
            relay.send_from_client(f"msg-{i}".encode())
            relay.send_from_remote(f"reply-{i}".encode())

        all_remote = relay.recv_for_remote()
        for i in range(5):
            assert f"msg-{i}".encode() in all_remote

        all_client = relay.recv_for_client()
        for i in range(5):
            assert f"reply-{i}".encode() in all_client


class TestUsernamePasswordAuth:
    def test_auth_success(self):
        server = make_auth_server()
        assert isinstance(server.network, InMemoryNetwork)
        server.network.register_target("1.2.3.4", 80)

        session = handshake_with_auth(server, "alice", "password123", "s1")
        assert session.state == SessionState.AUTHENTICATED

        response = do_connect(server, "s1", "1.2.3.4", 80)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED
        assert session.state == SessionState.RELAYING

    def test_auth_no_auth_method_also_available(self):
        server = make_auth_server()
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_NO_AUTH
        assert session.state == SessionState.AUTHENTICATED

    def test_auth_with_password_auth_method(self):
        server = make_auth_server()
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_USERNAME_PASSWORD])
        response = server.process_session("s1", greeting)
        parsed = parse_method_selection(response)
        assert parsed.method == AUTH_USERNAME_PASSWORD

        auth_req = build_auth_request("alice", "password123")
        response = server.process_session("s1", auth_req)
        auth_rep = parse_auth_reply(response)
        assert auth_rep.success is True
        assert session.state == SessionState.AUTHENTICATED

    def test_auth_then_connect_and_relay(self):
        server = make_auth_server()
        target_conn = server.network.register_target("5.5.5.5", 443)

        session = handshake_with_auth(server, "bob", "secret", "s1")
        response = do_connect(server, "s1", "5.5.5.5", 443)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED

        relay = server.get_tcp_relay("s1")
        relay.send_from_client(b"secure data")
        assert relay.recv_for_remote() == b"secure data"

        relay.send_from_remote(b"secure reply")
        assert relay.recv_for_client() == b"secure reply"


class TestConnectCommand:
    def test_connect_ipv4(self):
        server = make_no_auth_server()
        server.network.register_target("192.168.1.1", 80)

        session = handshake_no_auth(server, "s1")
        response = do_connect(server, "s1", "192.168.1.1", 80)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED
        assert session.state == SessionState.RELAYING
        assert session.connection is not None

    def test_connect_and_bidirectional_relay(self):
        server = make_no_auth_server()
        target_conn = server.network.register_target("10.0.0.1", 8080)

        handshake_no_auth(server, "s1")
        do_connect(server, "s1", "10.0.0.1", 8080)

        relay = server.get_tcp_relay("s1")

        relay.send_from_client(b"request")
        assert relay.recv_for_remote() == b"request"

        relay.send_from_remote(b"response")
        assert relay.recv_for_client() == b"response"


class TestUdpAssociate:
    def test_udp_associate_basic(self):
        server = make_full_server()
        session = server.create_session("s1")

        greeting = build_greeting([AUTH_NO_AUTH])
        response = server.process_session("s1", greeting)
        parse_method_selection(response)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED
        assert session.state == SessionState.UDP_ASSOCIATED
        assert reply.bind_address.port > 0

    def test_udp_associate_forward_datagram(self):
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

        target_addr = Socks5Address(atyp=ATYP_IPV4, host="93.184.216.34", port=53)
        datagram = UdpDatagram(rsv=0, frag=0, address=target_addr, data=b"DNS query")
        relay.send_from_client(datagram)

        forwarded = relay.recv_for_remote()
        assert len(forwarded) == 1
        (dest_addr, payload) = forwarded[0]
        assert dest_addr == ("93.184.216.34", 53)
        assert payload == b"DNS query"

    def test_udp_associate_reply_from_remote(self):
        server = make_full_server()

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")

        relay.send_from_remote(b"DNS response", ("93.184.216.34", 53))
        datagrams = relay.recv_for_client()
        assert len(datagrams) == 1
        assert datagrams[0].data == b"DNS response"
        assert datagrams[0].address.host == "93.184.216.34"
        assert datagrams[0].address.port == 53

    def test_udp_associate_domain_resolution(self):
        server = make_full_server()
        server.dns_resolver.add_record("example.com", "93.184.216.34")

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        request = build_request(0x03, addr)
        server.process_session("s1", request)

        relay = server.get_udp_relay("s1")

        target_addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=53)
        datagram = UdpDatagram(rsv=0, frag=0, address=target_addr, data=b"query")
        relay.send_from_client(datagram)

        forwarded = relay.recv_for_remote()
        assert len(forwarded) == 1
        (dest_addr, payload) = forwarded[0]
        assert dest_addr == ("93.184.216.34", 53)
        assert payload == b"query"


class TestDomainRemoteResolution:
    def test_domain_resolution_connect(self):
        server = make_full_server()
        server.dns_resolver.add_record("example.com", "93.184.216.34")
        server.network.register_target("93.184.216.34", 80)

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=80)
        request = build_request(0x01, addr)
        response = server.process_session("s1", request)
        reply = parse_reply(response)
        assert reply.reply_code == REP_SUCCEEDED
        assert session.state == SessionState.RELAYING

    def test_domain_resolution_relay_data(self):
        server = make_full_server()
        server.dns_resolver.add_record("example.com", "93.184.216.34")
        target_conn = server.network.register_target("93.184.216.34", 80)

        session = server.create_session("s1")
        greeting = build_greeting([AUTH_NO_AUTH])
        server.process_session("s1", greeting)

        addr = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=80)
        request = build_request(0x01, addr)
        server.process_session("s1", request)

        relay = server.get_tcp_relay("s1")
        relay.send_from_client(b"GET / HTTP/1.1\r\n\r\n")
        assert relay.recv_for_remote() == b"GET / HTTP/1.1\r\n\r\n"

        relay.send_from_remote(b"HTTP/1.1 200 OK\r\n\r\n")
        assert relay.recv_for_client() == b"HTTP/1.1 200 OK\r\n\r\n"
