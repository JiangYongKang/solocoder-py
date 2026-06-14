# 语音编码索引模块

本模块提供基于语音编码的姓名模糊匹配功能，使用内存数据结构存储姓名索引，
支持 Soundex 和 Metaphone 两种经典语音编码算法，可实现"听起来像"的姓名检索。

## 模块功能

- **Soundex 编码**：将英文姓名转换为定长（1 字母 + 3 数字）的语音编码，
  适用于快速同音姓名匹配
- **Metaphone 编码**：作为 Soundex 的改进版本，输出变长字母序列，
  对辅音的映射规则更精确，支持更准确的英语发音匹配
- **语音索引构建**：将一批姓名分别计算 Soundex 码和 Metaphone 码后存入内存索引，
  支持增量添加、批量添加、删除和更新操作
- **模糊匹配查询**：查询时输入姓名，分别用两种编码去索引中查找编码相同的候选姓名，
  支持三种匹配模式：Soundex 匹配、Metaphone 匹配、两者并集匹配
- **结果智能排序**：并集模式下，结果按匹配质量排序（双编码匹配 > Soundex 匹配 >
  Metaphone 匹配），同质量按姓名字典序排列

## 核心类与函数

### `soundex(name: str) -> str`

计算姓名的 Soundex 编码。返回格式为 1 个大写字母后跟 3 位数字（共 4 字符）。

### `metaphone(name: str, max_length: int | None = None) -> str`

计算姓名的 Metaphone 编码。返回由大写字母（含特殊字符 `0` 表示 th 音）组成的
变长序列。可通过 `max_length` 参数截断编码以控制匹配精度。

### `MatchMode`

匹配模式枚举：

| 模式 | 说明 |
|------|------|
| `MatchMode.SOUNDEX` | 仅按 Soundex 编码匹配 |
| `MatchMode.METAPHONE` | 仅按 Metaphone 编码匹配 |
| `MatchMode.BOTH` | 按两种编码的并集匹配（默认） |

### `PhoneticCode`

语音编码数据类，包含两个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `soundex` | `str` | Soundex 编码 |
| `metaphone` | `str` | Metaphone 编码 |

### `MatchResult`

匹配结果数据类，包含三个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 匹配到的姓名 |
| `soundex_match` | `bool` | 是否通过 Soundex 编码匹配 |
| `metaphone_match` | `bool` | 是否通过 Metaphone 编码匹配 |

### `PhoneticIndex`

语音索引主类，提供以下核心方法与属性：

| 方法 / 属性 | 说明 |
|------------|------|
| `add(name)` | 添加单个姓名到索引，返回其语音编码 |
| `add_batch(names)` | 批量添加姓名，返回姓名到编码的字典 |
| `remove(name)` | 从索引中删除姓名，返回是否成功 |
| `update(old_name, new_name)` | 更新姓名，返回新的语音编码 |
| `clear()` | 清空索引 |
| `contains(name)` | 检查姓名是否在索引中 |
| `get_code(name)` | 计算姓名的语音编码（不添加到索引） |
| `search(query, mode)` | 按指定模式查询发音相近的姓名 |
| `names` | 当前索引中的所有姓名（排序后列表，属性） |
| `name_count` | 当前索引中的姓名数量（属性） |
| `metaphone_max_length` | Metaphone 编码最大长度（属性） |

构造参数：

- `names`：初始姓名列表，默认为 `None`
- `metaphone_max_length`：Metaphone 编码最大长度，默认为 `None`（不截断）

`search` 方法参数：

- `query`：查询姓名
- `mode`：匹配模式，可为 `MatchMode` 枚举或字符串 `"soundex"` / `"metaphone"` /
  `"both"`，默认 `MatchMode.BOTH`

## Soundex 编码规则

Soundex 算法将姓名编码为 **首字母 + 三位数字** 的格式（不足补 0，超过截断）。

### 辅音到数字的映射表

| 数字 | 辅音字母 | 说明 |
|------|----------|------|
| 1 | B, F, P, V | 唇音 |
| 2 | C, G, J, K, Q, S, X, Z | 软腭音和齿龈音 |
| 3 | D, T | 齿龈塞音 |
| 4 | L | 边音 |
| 5 | M, N | 鼻音 |
| 6 | R | 卷舌音 |

### 算法步骤

1. **保留首字母**：取姓名首字母作为编码的第一个字符，转为大写
2. **过滤字符**：
   - 跳过元音字母（A, E, I, O, U, Y）和 H、W
   - 非字母字符直接忽略
3. **编码其余字母**：按上表将其余辅音转换为对应数字
4. **去重规则**：
   - 相邻且编码相同的辅音合并为一个数字
   - H 和 W 不编码也不打断相邻重复（即 BH F 编码为 B1）
   - 元音字母打断相邻重复（即 B O B 编码为 B100，而非 B000）
5. **补零或截断**：最终结果需为 4 字符，不足补 0，超过截断

### 典型示例

| 姓名 | Soundex 码 | 说明 |
|------|------------|------|
| Robert | R163 | R(1) + b(1, 去重) + t(3) + r(6) |
| Rupert | R163 | 与 Robert 发音相近，编码相同 |
| Rubin | R150 | R(1) + b(1, 去重) + n(5) + 补 0 |
| Smith | S530 | S(5) + m(5, 去重) + t(3) + 补 0 |
| Smythe | S530 | 与 Smith 发音相近，编码相同 |
| Ashcraft | A261 | A + s(2) + c(2, 去重) + r(6) + f(1) |
| Pfister | P236 | P + f(1, 去重) + s(2) + t(3) + r(6) |

## Metaphone 编码规则

Metaphone 是 Soundex 的改进版本，输出 **变长字母序列**，对英语发音的模拟更精确。

### 辅音到字母的映射表

| 原字母 | 条件 | Metaphone 编码 |
|--------|------|----------------|
| B | 非 "MB" 结尾 | B |
| C | "CIA" 中 | X |
| C | "CE"/"CI"/"CY" 中且前非 S | S |
| C | "CH" 中后接元音 | X |
| C | "CH" 中后不接元音 | K |
| C | "CK" 中（后接 K）且前非 S | K（跳过后续 K） |
| C | 其他情况 | K |
| D | "DGE"/"DGI"/"DGY" 中 | J |
| D | 其他情况 | T |
| G | "GE"/"GI"/"GY" 中 | J |
| G | "GN"/"GED" 结尾 | 省略 |
| G | "GH" 中 | K（后接元音）或省略 |
| G | 其他情况 | K |
| H | 开头且后接元音 | H |
| H | 前为 C/S/T/P/G/W | 省略 |
| H | 其他后接元音情况 | H |
| K | 前为 C | 省略 |
| P | "PH" 中 | F |
| P | 其他情况 | P |
| Q | 任何情况 | K |
| S | "SH" 中 | X |
| S | "SIA"/"SIO" 中 | X |
| S | 其他情况 | S |
| T | "TIA"/"TIO" 中 | X |
| T | "TH" 中 | 0（th 音记号） |
| T | "TCH" 中 | 省略 |
| T | 其他情况 | T |
| V | 任何情况 | F |
| W | 后接元音 | W |
| X | 开头 | S |
| X | 其他情况 | KS |
| Y | 后接元音 | Y |
| Z | 任何情况 | S |

### 特殊前缀处理

| 前缀 | 处理方式 | 示例 |
|------|----------|------|
| KN, GN, PN, WR | 跳过首字母 | KNight → NMT, WRite → RT |
| WH | 转为 W，跳过 H | WHale → WL |
| X（开头） | 转为 S | XAvier → SFR |

### 算法要点

1. **元音处理**：仅保留开头的元音字母，中间和结尾的元音全部省略
2. **重复字母**：相邻重复字母（除 C 外）合并为一个
3. **变长输出**：编码长度不固定，可通过 `max_length` 参数控制
4. **大小写不敏感**：输入自动转为大写处理，非字母字符忽略

### 典型示例

| 姓名 | Metaphone 码 | 说明 |
|------|--------------|------|
| Smith | SM0 | S + M + TH(0) |
| Smythe | SM0 | 与 Smith 编码相同 |
| Schmidt | XMT | SCH(X) + M + T |
| Catherine | K0RN | C(K) + A(省略) + TH(0) + R + N |
| Katherine | K0RN | 与 Catherine 编码相同 |
| Phone | FN | PH(F) + N |
| Knight | NT | K(省略) + N + T |
| Think | 0NK | TH(0) + N + K |
| Edge | AJ | A + DGE(J) |
| Jackson | JKSN | J + A(省略) + CK(K) + S + O(省略) + N |
| Back | BK | B + A(省略) + CK(K) |
| Check | XK | CH(X) + E(省略) + CK(K) |

## 匹配策略

### 索引结构

内部使用两个倒排索引：

- `_soundex_index: dict[str, set[str]]`：Soundex 码 → 姓名集合
- `_metaphone_index: dict[str, set[str]]`：Metaphone 码 → 姓名集合

另维护 `_name_codes: dict[str, PhoneticCode]` 存储每个姓名的原始编码，
用于支持删除和更新操作。

### 查询流程

1. 计算查询姓名的 Soundex 码和 Metaphone 码
2. 根据匹配模式从对应索引中获取候选姓名集合
3. 合并结果（并集模式），标记每个姓名的匹配来源
4. 按匹配质量排序：
   - 优先级 1：Soundex 和 Metaphone 同时匹配
   - 优先级 2：仅 Soundex 匹配
   - 优先级 3：仅 Metaphone 匹配
   - 同优先级按姓名字典序排列

### 模式对比

| 模式 | 召回率 | 精确率 | 适用场景 |
|------|--------|--------|----------|
| Soundex | 高 | 中 | 快速粗过滤，兼容传统系统 |
| Metaphone | 中 | 高 | 精确匹配，发音区分度好 |
| Both | 最高 | 中高 | 综合结果，不遗漏可能匹配 |

## 异常类

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `PhoneticError` | 语音编码操作的基类异常 | — |
| `EmptyNameError` | 姓名为空时抛出 | 编码或添加空字符串 |
| `NameNotFoundError` | 姓名不存在时抛出 | 删除或更新不存在的姓名 |
| `NameExistsError` | 姓名已存在时抛出 | 添加重复姓名 |
| `InvalidMatchModeError` | 匹配模式无效时抛出 | 使用未定义的模式字符串 |

## 使用示例

```python
from solocoder_py.phonetic import (
    MatchMode,
    PhoneticIndex,
    metaphone,
    soundex,
)

# 单独使用编码函数
code = soundex("Robert")  # "R163"
code = metaphone("Catherine")  # "K0RN"

# 限制 Metaphone 编码长度
code = metaphone("Supercalifragilisticexpialidocious", max_length=5)

# 创建语音索引
names = [
    "Robert", "Rupert", "Rubin",
    "Smith", "Smythe", "Schmidt",
    "Catherine", "Katherine", "Katheryn",
    "John", "Jon", "Sean", "Shawn",
]
idx = PhoneticIndex(names)

# 增量添加姓名
idx.add("Stephen")
idx.add_batch(["Steven", "Steve"])

# 删除和更新
idx.remove("Rubin")
idx.update("Stephen", "Steven")  # 注意目标姓名不能已存在

# 按 Soundex 匹配
results = idx.search("Robert", mode=MatchMode.SOUNDEX)
for r in results:
    print(f"{r.name}: soundex={r.soundex_match}, metaphone={r.metaphone_match}")
# Robert: soundex=True, metaphone=True
# Rupert: soundex=True, metaphone=False

# 按 Metaphone 匹配
results = idx.search("Smith", mode=MatchMode.METAPHONE)
result_names = [r.name for r in results]  # ["Smith", "Smythe"]

# 并集匹配（默认模式）
results = idx.search("Shawn", mode=MatchMode.BOTH)
# 按匹配质量排序：双匹配在前，单匹配在后

# 也可以用字符串指定模式
results = idx.search("John", mode="both")

# 配置 Metaphone 最大长度（更宽松的匹配）
idx_lenient = PhoneticIndex(names, metaphone_max_length=2)
results = idx_lenient.search("Catherine", mode=MatchMode.METAPHONE)

# 查看索引状态
print(f"索引中共有 {idx.name_count} 个姓名")
print(f"所有姓名: {idx.names}")
print(f"包含 'John'? {idx.contains('John')}")

# 获取编码（不添加到索引）
code = idx.get_code("Williams")
print(f"Williams: soundex={code.soundex}, metaphone={code.metaphone}")

# 清空索引
idx.clear()

# 异常处理
from solocoder_py.phonetic import (
    EmptyNameError,
    NameExistsError,
    NameNotFoundError,
    InvalidMatchModeError,
)

try:
    soundex("")
except EmptyNameError:
    print("姓名不能为空")

try:
    idx.add("Robert")
    idx.add("Robert")
except NameExistsError:
    print("姓名已存在")

try:
    idx.remove("Nonexistent")
except NameNotFoundError:
    print("姓名不存在")

try:
    idx.search("John", mode="invalid")
except InvalidMatchModeError:
    print("无效的匹配模式")
```

## 边界情况处理

| 输入 | Soundex | Metaphone | 说明 |
|------|---------|-----------|------|
| `""` | 抛异常 | 抛异常 | 空字符串 |
| `"123"` | `"0000"` | `""` | 全非字母 |
| `"A"` | `"A000"` | `"A"` | 单字符元音 |
| `"B"` | `"B000"` | `"B"` | 单字符辅音 |
| `"AEIOU"` | `"A000"` | `"A"` | 全元音 |
| `"O'Brien"` | `"O165"` | `"OBRN"` | 含特殊字符 |
| `"John123"` | `"J500"` | `"JN"` | 含数字 |
| 超长姓名 | 4 字符 | 变长 | Metaphone 可截断 |
