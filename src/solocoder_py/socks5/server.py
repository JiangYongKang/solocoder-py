from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from .auth import AuthProvider
from .constants import (
    SOCKS_VERSION,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    AUTH_NO_ACCEPTABLE,
    CMD_CONNECT,
    CMD_BIND,
    CMD_UDP_ASSOCIATE,
    REP_SUCCEEDED,
    REP_GENERAL_FAILURE,
    REP_HOST_UNREACHABLE,
    REP_CONNECTION_REFUSED,
    REP_COMMAND_NOT_SUPPORTED,
    REP_ADDRESS_TYPE_NOT_SUPPORTED,
    DEFAULT_SUPPORTED_ATYPS,
)
from .exceptions import Socks5Error
from .models import SessionState, Socks5Address, TargetConnection
from .network import InMemoryDnsResolver, InMemoryNetwork
from .protocol import (
    build_method_selection,
    build_auth_reply,
    build_reply,
    parse_request,
    parse_auth_request,
)
from .relay import TcpRelay, UdpRelay


class Socks5Session:
    def __init__(self, session_id: str, server: Socks5Server) -> None:
        self._id = session_id
        self._server = server
        self._state = SessionState.INIT
        self._connection: Optional[TargetConnection] = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> SessionState:
        return self._state

    @state.setter
    def state(self, value: SessionState) -> None:
        self._state = value

    @property
    def connection(self) -> Optional[TargetConnection]:
        return self._connection

    @connection.setter
    def connection(self, value: Optional[TargetConnection]) -> None:
        self._connection = value

    def process(self, data: bytes) -> bytes:
        if self._state == SessionState.CLOSED:
            raise Socks5Error("Session is closed")

        if self._state == SessionState.INIT:
            return self._handle_greeting(data)
        elif self._state == SessionState.AUTHENTICATING:
            return self._handle_auth(data)
        elif self._state == SessionState.AUTHENTICATED:
            return self._handle_request(data)
        else:
            raise Socks5Error(f"Invalid session state for processing: {self._state}")

    def _handle_greeting(self, data: bytes) -> bytes:
        nmethods = data[1]
        server_methods = set(self._server.supported_methods)

        client_methods_list = list(data[2:2 + nmethods])
        chosen = None
        for m in client_methods_list:
            if m in server_methods:
                chosen = m
                break

        if chosen is None:
            self._state = SessionState.CLOSED
            return build_method_selection(AUTH_NO_ACCEPTABLE)

        if chosen == AUTH_NO_AUTH:
            self._state = SessionState.AUTHENTICATED
        elif chosen == AUTH_USERNAME_PASSWORD:
            self._state = SessionState.AUTHENTICATING

        return build_method_selection(chosen)

    def _handle_auth(self, data: bytes) -> bytes:
        username, password = parse_auth_request(data)

        if self._server.auth_provider.authenticate(username, password):
            self._state = SessionState.AUTHENTICATED
            return build_auth_reply(True)
        else:
            self._state = SessionState.CLOSED
            return build_auth_reply(False)

    def _handle_request(self, data: bytes) -> bytes:
        cmd, addr = parse_request(data)

        if addr.atyp not in self._server.supported_atyps:
            self._state = SessionState.CLOSED
            return build_reply(
                REP_ADDRESS_TYPE_NOT_SUPPORTED,
                Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0),
            )

        if cmd == CMD_CONNECT:
            return self._handle_connect(addr)
        elif cmd == CMD_UDP_ASSOCIATE:
            return self._handle_udp_associate(addr)
        elif cmd == CMD_BIND:
            self._state = SessionState.CLOSED
            return build_reply(
                REP_COMMAND_NOT_SUPPORTED,
                Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0),
            )
        else:
            self._state = SessionState.CLOSED
            return build_reply(
                REP_COMMAND_NOT_SUPPORTED,
                Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0),
            )

    def _resolve_address(self, addr: Socks5Address) -> Optional[str]:
        if addr.atyp == ATYP_DOMAINNAME:
            dns = self._server.dns_resolver
            if dns is None:
                return None
            return dns.resolve(addr.host)
        return addr.host

    def _handle_connect(self, addr: Socks5Address) -> bytes:
        resolved_host = self._resolve_address(addr)

        if addr.atyp == ATYP_DOMAINNAME and resolved_host is None:
            self._state = SessionState.CLOSED
            return build_reply(
                REP_HOST_UNREACHABLE,
                Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0),
            )

        target_host = resolved_host if resolved_host is not None else addr.host
        network = self._server.network
        target = network.connect(target_host, addr.port)

        if target is None:
            self._state = SessionState.CLOSED
            return build_reply(
                REP_CONNECTION_REFUSED,
                Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0),
            )

        self._connection = target
        self._state = SessionState.RELAYING

        relay = TcpRelay()
        self._server._tcp_relays[self._id] = relay

        bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        return build_reply(REP_SUCCEEDED, bind_addr)

    def _handle_udp_associate(self, addr: Socks5Address) -> bytes:
        bind_port = self._server._allocate_udp_port()
        dns = self._server.dns_resolver

        relay = UdpRelay(bind_port=bind_port, dns_resolver=dns)
        self._server._udp_relays[self._id] = relay
        self._state = SessionState.UDP_ASSOCIATED

        bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=bind_port)
        return build_reply(REP_SUCCEEDED, bind_addr)


class Socks5Server:
    def __init__(
        self,
        auth_provider: AuthProvider,
        supported_methods: Optional[List[int]] = None,
        dns_resolver: Optional[InMemoryDnsResolver] = None,
        network: Optional[InMemoryNetwork] = None,
        supported_atyps: Optional[Tuple[int, ...]] = None,
    ) -> None:
        self._auth_provider = auth_provider
        self._supported_methods = supported_methods or auth_provider.get_supported_methods()
        self._dns_resolver = dns_resolver or InMemoryDnsResolver()
        self._network = network or InMemoryNetwork()
        self._supported_atyps = supported_atyps or DEFAULT_SUPPORTED_ATYPS
        self._sessions: Dict[str, Socks5Session] = {}
        self._tcp_relays: Dict[str, TcpRelay] = {}
        self._udp_relays: Dict[str, UdpRelay] = {}
        self._next_udp_port = 10000
        self._lock = threading.Lock()

    @property
    def auth_provider(self) -> AuthProvider:
        return self._auth_provider

    @property
    def supported_methods(self) -> List[int]:
        return list(self._supported_methods)

    @property
    def supported_atyps(self) -> Tuple[int, ...]:
        return self._supported_atyps

    @property
    def dns_resolver(self) -> InMemoryDnsResolver:
        return self._dns_resolver

    @property
    def network(self) -> InMemoryNetwork:
        return self._network

    def _allocate_udp_port(self) -> int:
        with self._lock:
            port = self._next_udp_port
            self._next_udp_port += 1
            return port

    def create_session(self, session_id: str) -> Socks5Session:
        session = Socks5Session(session_id, self)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Socks5Session]:
        return self._sessions.get(session_id)

    def process_session(self, session_id: str, data: bytes) -> bytes:
        session = self._sessions.get(session_id)
        if session is None:
            raise Socks5Error(f"Session not found: {session_id}")
        return session.process(data)

    def get_tcp_relay(self, session_id: str) -> Optional[TcpRelay]:
        return self._tcp_relays.get(session_id)

    def get_udp_relay(self, session_id: str) -> Optional[UdpRelay]:
        return self._udp_relays.get(session_id)

    def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.state = SessionState.CLOSED

        udp_relay = self._udp_relays.get(session_id)
        if udp_relay is not None:
            udp_relay.close()

        self._tcp_relays.pop(session_id, None)
        self._udp_relays.pop(session_id, None)
