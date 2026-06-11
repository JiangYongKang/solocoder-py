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
    AUTH_NO_AUTH,
    AUTH_USERNAME_PASSWORD,
    REP_SUCCEEDED,
    build_greeting,
    build_auth_request,
    build_request,
    build_udp_datagram,
    parse_method_selection,
    parse_auth_reply,
    parse_reply,
)


def make_no_auth_server() -> Socks5Server:
    return Socks5Server(
        auth_provider=NoAuthAuthProvider(),
        supported_methods=[AUTH_NO_AUTH],
    )


def make_auth_server(credentials=None) -> Socks5Server:
    creds = credentials if credentials is not None else {"alice": "password123", "bob": "secret"}
    return Socks5Server(
        auth_provider=InMemoryAuthProvider(creds),
        supported_methods=[AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD],
    )


def make_full_server(credentials=None) -> Socks5Server:
    creds = credentials if credentials is not None else {"alice": "password123", "bob": "secret"}
    network = InMemoryNetwork()
    dns = InMemoryDnsResolver()
    return Socks5Server(
        auth_provider=InMemoryAuthProvider(creds),
        dns_resolver=dns,
        network=network,
        supported_methods=[AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD],
    )


def handshake_no_auth(server: Socks5Server, session_id: str = "test") -> Socks5Session:
    session = server.create_session(session_id)
    greeting = build_greeting([AUTH_NO_AUTH])
    response = server.process_session(session_id, greeting)
    parsed = parse_method_selection(response)
    assert parsed.method == AUTH_NO_AUTH
    assert session.state == SessionState.AUTHENTICATED
    return session


def handshake_with_auth(
    server: Socks5Server,
    username: str,
    password: str,
    session_id: str = "test",
) -> Socks5Session:
    session = server.create_session(session_id)
    greeting = build_greeting([AUTH_USERNAME_PASSWORD])
    response = server.process_session(session_id, greeting)
    parsed = parse_method_selection(response)
    assert parsed.method == AUTH_USERNAME_PASSWORD
    assert session.state == SessionState.AUTHENTICATING

    auth_req = build_auth_request(username, password)
    response = server.process_session(session_id, auth_req)
    auth_rep = parse_auth_reply(response)
    return session


def do_connect(
    server: Socks5Server,
    session_id: str,
    host: str = "1.2.3.4",
    port: int = 80,
    atyp: int = ATYP_IPV4,
) -> bytes:
    addr = Socks5Address(atyp=atyp, host=host, port=port)
    request = build_request(0x01, addr)
    return server.process_session(session_id, request)
