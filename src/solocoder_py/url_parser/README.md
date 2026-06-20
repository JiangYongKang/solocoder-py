# URL Parser & Builder (RFC 3986)

RFC 3986 规范的 URL 解析与构建器模块，提供完整的 URL 组件解析、查询参数操作、百分号编解码和 Builder 模式构建功能。

## 模块功能

- **URL 组件解析**：将 URL 字符串按 RFC 3986 规范解析为 scheme、authority（userinfo、host、port）、path、query、fragment
- **Scheme 校验**：校验 scheme 合法性，提供已知 scheme 注册列表
- **查询参数操作**：支持多同名键的增删改查
- **百分号编解码**：遵循 percent-encoding 规则，正确处理 UTF-8 多字节字符
- **URL 构建器**：Builder 模式逐步拼装 URL，自动处理路径斜杠

## RFC 3986 URL 组件结构

```
  https://user:pass@example.com:8080/path/to/res?key=val#frag
  \___/   \_______/ \_________/ \__/\___________/ \______/ \__/
    |         |          |        |       |          |       |
  scheme  userinfo     host     port    path     query  fragment
           \__________________________/
                       |
                   authority
```

| 组件       | 必选 | 说明                                         |
| ---------- | ---- | -------------------------------------------- |
| scheme     | 是   | 协议名，以字母开头，后跟字母/数字/`+`/`-`/`.` |
| authority  | 否   | 包含 userinfo、host、port                    |
| userinfo   | 否   | 格式 `user:pass`，`@` 分隔                   |
| host       | 否   | 域名 / IPv4 / IPv6（方括号包裹）             |
| port       | 否   | 数字端口号                                    |
| path       | 否   | 路径，`/` 分隔                                |
| query      | 否   | `?` 开头的键值对                              |
| fragment   | 否   | `#` 开头的片段标识                            |

## 核心类职责

| 类/模块            | 职责                                                |
| ------------------ | --------------------------------------------------- |
| `UrlParser`        | 解析 URL 字符串为 `UrlComponents`                   |
| `UrlComponents`    | 数据类，存储解析后的各组件，支持 `rebuild()` 重建   |
| `QueryParams`      | 查询参数的键值对列表，支持多同名键的增删改查        |
| `UrlBuilder`       | Builder 模式，逐步构建完整 URL 字符串               |
| `percent` 模块     | 独立的百分号编解码函数                              |
| `scheme` 模块      | Scheme 合法性校验与已知 scheme 注册表               |

## 百分号编解码规则

### 编码（`percent_encode`）

对 UTF-8 字节流中**非保留字符**以外的每个字节，使用 `%XX`（大写十六进制）替换。

**保留字符（UNRESERVED）**：`A-Z a-z 0-9 - . _ ~`

可通过 `safe` 参数指定额外不需要编码的字符。

### 解码（`percent_decode`）

将 `%XX` 序列还原为原始字节，再以 UTF-8 解码为字符串。

**异常处理策略**（`errors` 参数）：
- `"strict"`：遇到不完整或非法编码抛出 `PercentDecodeError`
- `"replace"`：替换为 Unicode 替换字符 `U+FFFD`
- `"ignore"`：跳过非法序列

## Builder 使用模式

```python
from solocoder_py.url_parser import UrlBuilder

url = (
    UrlBuilder()
    .scheme("https")
    .host("api.example.com")
    .port(443)
    .path_segment("v2")
    .path_segment("users")
    .add_query_param("limit", "10")
    .add_query_param("sort", "name")
    .fragment("results")
    .build()
)
# => "https://api.example.com:443/v2/users?limit=10&sort=name#results"
```

路径拼接时自动去除多余斜杠：

```python
url = UrlBuilder().scheme("http").host("x.com").path("//a//b//").build()
# => "http://x.com/a/b"
```

## 使用示例

### 解析 URL

```python
from solocoder_py.url_parser import parse_url

result = parse_url("https://user:pass@example.com:8080/api?q=test#section")
print(result.scheme)    # "https"
print(result.userinfo)  # "user:pass"
print(result.host)      # "example.com"
print(result.port)      # 8080
print(result.path)      # "/api"
print(result.query)     # "q=test"
print(result.fragment)  # "section"
```

### 查询参数操作

```python
from solocoder_py.url_parser import QueryParams

qp = QueryParams.from_string("a=1&b=2&a=3")
qp.get_param("a")          # "3" (最后一个)
qp.get_param_all("a")      # ["1", "3"]
qp.set_param("a", "new")   # 替换所有同名键
qp.add_param("c", "4")     # 追加
qp.remove_param("b")       # 删除
qp.to_string()             # "a=new&c=4"
```

### 百分号编解码

```python
from solocoder_py.url_parser import percent_encode, percent_decode

encoded = percent_encode("中文 / path")
# "%E4%B8%AD%E6%96%87%20/%20path"

decoded = percent_decode("%E4%B8%AD%E6%96%87")
# "中文"
```

### Scheme 校验

```python
from solocoder_py.url_parser import validate_scheme, is_scheme_known, register_scheme

validate_scheme("http")       # 通过
validate_scheme("1bad")       # 抛出 InvalidSchemeError

is_scheme_known("ftp")        # True
register_scheme("my-proto")   # 注册自定义 scheme
```
