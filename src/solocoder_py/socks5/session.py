from __future__ import annotations

from typing import List, Optional

from .auth import AuthProvider, NoAuthAuthProvider
from .constants import (
    SOCKS_VERSION,
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    AUTH_NO_ACCEPTABLE,
    CMD_CONNECT,
    CMD_UDP_ASSOCIATE,
    ATYP_IPV4,
    ATYP_DOMAINNAME,
    REP_SUCCEEDED,
    REP_GENERAL_FAILURE,
    REP_CONNECTION_REFUSED,
    REP_COMMAND_NOT_SUPPORTED,
    REP_ADDRESS_TYPE_NOT_SUPPORTED,
    REP_HOST_UNREACHABLE,
)
from .exceptions import (
    Socks5Error,
    Socks5HandshakeError,
    Socks5AuthError,
    Socks5RequestError,
    Socks5ProtocolError,
    Socks5ResolutionError,
)
from .models import (
    Socks5Address,
    SessionState,
    SimulatedConnection,
    DnsResolver,
    SimulatedNetwork,
    UdpAssociation,
)
from .protocol import (
    parse_greeting,
    build_method_selection,
    parse_auth_request,
    build_auth_reply,
    parse_request,
    build_reply,
)


class Socks5Session:
    def __init__(
        self,
        session_id: str,
        auth_provider: AuthProvider,
        dns_resolver: DnsResolver,
        network: SimulatedNetwork,
        supported_methods: Optional[List[int]] = None,
        supported_atyps: Optional[List[int]] = None,
        next_relay_port: int = 10000,
    ) -> None:
        self._session_id = session_id
        self._state = SessionState.INIT
        self._auth_provider = auth_provider
        self._dns_resolver = dns_resolver
        self._network = network
        self._supported_methods = supported_methods if supported_methods is not None else [AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD]
        self._supported_atyps = supported_atyps if supported_atyps is not None else [ATYP_IPV4, ATYP_DOMAINNAME]
        self._selected_method: Optional[int] = None
        self._connection: Optional[SimulatedConnection] = None
        self._udp_association: Optional[UdpAssociation] = None
        self._next_relay_port = next_relay_port
        self._closed = False

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def selected_method(self) -> Optional[int]:
        return self._selected_method

    @property
    def connection(self) -> Optional[SimulatedConnection]:
        return self._connection

    @property
    def udp_association(self) -> Optional[UdpAssociation]:
        return self._udp_association

    def process(self, data: bytes) -> bytes:
        if self._closed:
            raise Socks5Error("Session is closed")

        if self._state == SessionState.INIT:
            return self._handle_greeting(data)
        elif self._state == SessionState.AUTHENTICATING:
            return self._handle_auth(data)
        elif self._state == SessionState.AUTHENTICATED:
            return self._handle_request(data)
        elif self._state in (SessionState.RELAYING, SessionState.UDP_ASSOCIATED):
            raise Socks5Error("Session is already in relay mode; use relay methods")
        else:
            raise Socks5Error(f"Unexpected state: {self._state}")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._state = SessionState.CLOSED
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._udp_association is not None:
            self._udp_association.active = False
            self._udp_association = None

    def _handle_greeting(self, data: bytes) -> bytes:
        try:
            greeting = parse_greeting(data)
        except Socks5ProtocolError as e:
            self.close()
            raise Socks5HandshakeError(str(e))

        if greeting.version != SOCKS_VERSION:
            self.close()
            raise Socks5HandshakeError(f"Unsupported SOCKS version: {greeting.version}")

        chosen = AUTH_NO_ACCEPTABLE
        for method in greeting.methods:
            if method in self._supported_methods:
                chosen = method
                break

        self._selected_method = chosen

        if chosen == AUTH_NO_ACCEPTABLE:
            self._state = SessionState.CLOSED
            self._closed = True
            return build_method_selection(AUTH_NO_ACCEPTABLE)

        if chosen == AUTH_USERNAME_PASSWORD:
            self._state = SessionState.AUTHENTICATING
        else:
            self._state = SessionState.AUTHENTICATED

        return build_method_selection(chosen)

    def _handle_auth(self, data: bytes) -> bytes:
        try:
            auth_req = parse_auth_request(data)
        except Socks5ProtocolError as e:
            self.close()
            raise Socks5AuthError(str(e))

        success = self._auth_provider.authenticate(auth_req.username, auth_req.password)

        if success:
            self._state = SessionState.AUTHENTICATED
            return build_auth_reply(True)
        else:
            self._state = SessionState.CLOSED
            self._closed = True
            return build_auth_reply(False)

    def _handle_request(self, data: bytes) -> bytes:
        try:
            request = parse_request(data)
        except Socks5ProtocolError as e:
            self.close()
            raise Socks5RequestError(str(e))

        if request.address.atyp not in self._supported_atyps:
            bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
            self._state = SessionState.CLOSED
            self._closed = True
            return build_reply(REP_ADDRESS_TYPE_NOT_SUPPORTED, bind_addr)

        if request.command == CMD_CONNECT:
            return self._handle_connect(request)
        elif request.command == CMD_UDP_ASSOCIATE:
            return self._handle_udp_associate(request)
        else:
            bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
            self._state = SessionState.CLOSED
            self._closed = True
            return build_reply(REP_COMMAND_NOT_SUPPORTED, bind_addr)

    def _resolve_target(self, address: Socks5Address) -> str:
        if address.atyp == ATYP_DOMAINNAME:
            try:
                return self._dns_resolver.resolve(address.host)
            except Exception:
                raise Socks5ResolutionError(
                    f"Failed to resolve domain: {address.host}"
                )
        return address.host

    def _handle_connect(self, request: Socks5Request) -> bytes:
        try:
            target_host = self._resolve_target(request.address)
        except Socks5ResolutionError:
            bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
            self._state = SessionState.CLOSED
            self._closed = True
            return build_reply(REP_HOST_UNREACHABLE, bind_addr)

        try:
            conn = self._network.connect(target_host, request.address.port)
        except ConnectionRefusedError:
            bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
            self._state = SessionState.CLOSED
            self._closed = True
            return build_reply(REP_CONNECTION_REFUSED, bind_addr)
        except Exception:
            bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
            self._state = SessionState.CLOSED
            self._closed = True
            return build_reply(REP_GENERAL_FAILURE, bind_addr)

        self._connection = conn
        self._state = SessionState.RELAYING

        bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
        return build_reply(REP_SUCCEEDED, bind_addr)

    def _handle_udp_associate(self, request: Socks5Request) -> bytes:
        relay_port = self._next_relay_port
        self._next_relay_port += 1

        client_addr: Optional[tuple[str, int]] = None
        if request.address.atyp == ATYP_IPV4:
            client_addr = (request.address.host, request.address.port)
        elif request.address.atyp == ATYP_DOMAINNAME:
            try:
                resolved = self._dns_resolver.resolve(request.address.host)
                client_addr = (resolved, request.address.port)
            except Exception:
                client_addr = None

        self._udp_association = UdpAssociation(
            relay_port=relay_port,
            client_address=client_addr,
            control_session_id=self._session_id,
            active=True,
        )
        self._state = SessionState.UDP_ASSOCIATED

        bind_addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=relay_port)
        return build_reply(REP_SUCCEEDED, bind_addr)

    def relay_send(self, data: bytes) -> None:
        if self._state != SessionState.RELAYING or self._connection is None:
            raise Socks5Error("Session is not in TCP relay mode")
        self._connection.send(data)

    def relay_recv(self) -> bytes:
        if self._state != SessionState.RELAYING or self._connection is None:
            raise Socks5Error("Session is not in TCP relay mode")
        return self._connection.recv()

    def relay_remote_send(self, data: bytes) -> None:
        if self._state != SessionState.RELAYING or self._connection is None:
            raise Socks5Error("Session is not in TCP relay mode")
        self._connection.deliver(data)

    def relay_remote_recv(self) -> bytes:
        if self._state != SessionState.RELAYING or self._connection is None:
            raise Socks5Error("Session is not in TCP relay mode")
        return self._connection.collect()
