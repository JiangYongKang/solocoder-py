# SOCKS5 代理模块

本模块实现了 SOCKS5 代理协议（RFC 1928），使用内存数据结构模拟客户端连接与远程目标，适用于测试与教学场景。

## 模块功能

- **SOCKS5 握手与认证**：支持无认证（0x00）和用户名密码认证（0x02）两种方式
- **CONNECT 命令**：建立 TCP 中继，双向转发客户端与远程目标之间的数据
- **UDP ASSOCIATE 命令**：建立 UDP 中继通道，转发 UDP 数据报
- **域名远程解析**：代理端完成 DNS 解析，客户端无需本地解析域名

## 核心类的职责

| 类 | 职责 |
|---|---|
| `Socks5Server` | 代理服务器，管理会话、中继、认证提供者和网络资源 |
| `Socks5Session` | 单个客户端会话，驱动 SOCKS5 状态机（INIT → AUTHENTICATING → AUTHENTICATED → RELAYING/UDP_ASSOCIATED） |
| `TcpRelay` | TCP 数据中继，缓存客户端→远程和远程→客户端方向的数据 |
| `UdpRelay` | UDP 数据报中继，转发客户端数据报到目标地址并回传响应，支持域名解析 |
| `InMemoryAuthProvider` | 基于内存字典的用户名密码认证提供者 |
| `NoAuthAuthProvider` | 无认证提供者 |
| `InMemoryNetwork` | 内存模拟网络，维护已注册的目标连接 |
| `InMemoryDnsResolver` | 内存 DNS 解析器，维护域名到 IP 的映射 |

## SOCKS5 握手与认证流程

```
客户端                                    代理
  |---- VER | NMETHODS | METHODS ------->|   (1) 客户端发送问候
  |<--- VER | METHOD -------------------|   (2) 代理选择认证方式
  |                                       |
  |  [如果选择用户名密码认证]               |
  |---- VER | ULEN | UNAME | PLEN | PWD->|   (3) 客户端发送凭据
  |<--- VER | STATUS --------------------|   (4) 代理返回认证结果
  |                                       |
  |---- VER | CMD | RSV | ATYP | ADDR -->|   (5) 客户端发送请求
  |<--- VER | REP | RSV | ATYP | BND ----|   (6) 代理返回回复
```

1. **问候阶段**：客户端发送支持的认证方法列表，代理按客户端优先顺序选择第一个自身支持的方法
2. **认证阶段**：若选择用户名密码认证（0x02），客户端发送凭据，代理校验后返回成功或失败
3. **请求阶段**：认证通过后，客户端发送 CONNECT 或 UDP ASSOCIATE 命令

## UDP ASSOCIATE 中继机制

1. 客户端通过 TCP 控制连接发送 UDP ASSOCIATE 请求
2. 代理分配临时 UDP 端口，通过回复中的 BND.ADDR 告知客户端
3. 客户端将 SOCKS5 UDP 数据报（含 RSV、FRAG、ATYP、DST.ADDR、DATA）发送到代理的 UDP 端口
4. 代理将数据报转发到目标地址，并将目标的回复封装为 SOCKS5 UDP 数据报返回客户端
5. UDP 中继的存活时间与控制连接绑定：控制连接断开后，UDP 中继自动关闭（`UdpRelay.active` 置为 False）

## 域名远程解析规则

- 目标地址类型（ATYP）支持 IPv4（0x01）、域名（0x03）和 IPv6（0x04）
- 当 ATYP 为域名时，代理通过 `InMemoryDnsResolver` 解析域名为 IP 地址
- 解析成功后，代理使用解析后的 IP 连接目标
- 解析失败时，返回 `REP_HOST_UNREACHABLE`（0x04）错误
- 不支持的地址类型返回 `REP_ADDRESS_TYPE_NOT_SUPPORTED`（0x08）错误

## 使用示例

### 无认证模式

```python
from solocoder_py.socks5 import (
    Socks5Server, NoAuthAuthProvider, InMemoryNetwork,
    AUTH_NO_AUTH, build_greeting, build_request,
    parse_method_selection, parse_reply, Socks5Address, ATYP_IPV4,
)

server = Socks5Server(
    auth_provider=NoAuthAuthProvider(),
    supported_methods=[AUTH_NO_AUTH],
)
server.network.register_target("10.0.0.1", 8080)

session = server.create_session("s1")

# 握手
greeting = build_greeting([AUTH_NO_AUTH])
response = server.process_session("s1", greeting)
parsed = parse_method_selection(response)
assert parsed.method == AUTH_NO_AUTH

# CONNECT 请求
addr = Socks5Address(atyp=ATYP_IPV4, host="10.0.0.1", port=8080)
request = build_request(0x01, addr)
response = server.process_session("s1", request)
reply = parse_reply(response)
assert reply.reply_code == 0x00

# 数据中继
relay = server.get_tcp_relay("s1")
relay.send_from_client(b"Hello!")
assert relay.recv_for_remote() == b"Hello!"
```

### 用户名密码认证模式

```python
from solocoder_py.socks5 import (
    Socks5Server, InMemoryAuthProvider, InMemoryNetwork,
    AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD,
    build_greeting, build_auth_request,
    parse_method_selection, parse_auth_reply, parse_reply,
    build_request, Socks5Address, ATYP_IPV4,
)

server = Socks5Server(
    auth_provider=InMemoryAuthProvider({"alice": "password123"}),
    supported_methods=[AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD],
)
server.network.register_target("10.0.0.1", 8080)

session = server.create_session("s1")

# 握手 - 选择用户名密码认证
greeting = build_greeting([AUTH_USERNAME_PASSWORD])
response = server.process_session("s1", greeting)
assert parse_method_selection(response).method == AUTH_USERNAME_PASSWORD

# 认证
auth_req = build_auth_request("alice", "password123")
response = server.process_session("s1", auth_req)
assert parse_auth_reply(response).success is True

# CONNECT 请求与数据中继...
```

### UDP ASSOCIATE

```python
from solocoder_py.socks5 import (
    Socks5Server, InMemoryAuthProvider, InMemoryDnsResolver, InMemoryNetwork,
    UdpDatagram, Socks5Address, ATYP_IPV4, ATYP_DOMAINNAME,
    AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD,
    build_greeting, build_request,
    parse_method_selection, parse_reply,
)

server = Socks5Server(
    auth_provider=InMemoryAuthProvider({"alice": "pass"}),
    supported_methods=[AUTH_NO_AUTH, AUTH_USERNAME_PASSWORD],
)
server.dns_resolver.add_record("example.com", "93.184.216.34")

session = server.create_session("s1")
greeting = build_greeting([AUTH_NO_AUTH])
server.process_session("s1", greeting)

# UDP ASSOCIATE 请求
addr = Socks5Address(atyp=ATYP_IPV4, host="0.0.0.0", port=0)
request = build_request(0x03, addr)
response = server.process_session("s1", request)
reply = parse_reply(response)
assert reply.reply_code == 0x00

relay = server.get_udp_relay("s1")

# 发送 UDP 数据报到域名目标（自动解析）
target = Socks5Address(atyp=ATYP_DOMAINNAME, host="example.com", port=53)
relay.send_from_client(UdpDatagram(rsv=0, frag=0, address=target, data=b"query"))
forwarded = relay.recv_for_remote()
assert forwarded[0] == (("93.184.216.34", 53), b"query")

# 远程回复
relay.send_from_remote(b"response", ("93.184.216.34", 53))
datagrams = relay.recv_for_client()
assert datagrams[0].data == b"response"
```
