# Semver — 语义版本解析比较器

基于 Semver 2.0.0 规范的语义版本解析、比较与范围判定模块。

## 模块功能

- **版本解析**：将版本字符串分解为主版本号、次版本号、修订号、预发布标签和构建元数据
- **优先级比较**：支持 `<`, `<=`, `>`, `>=`, `==` 等完整比较运算
- **构建元数据剥离**：比较时忽略构建元数据，并提供剥离方法
- **范围满足判定**：解析版本范围表达式，判断版本是否满足约束

## 核心类职责

| 类 | 文件 | 职责 |
|---|---|---|
| `SemverVersion` | `version.py` | 版本解析、比较、字符串表示 |
| `VersionRange` | `range.py` | 范围表达式解析与满足判定 |
| `SemverError` | `exceptions.py` | 异常基类 |
| `InvalidVersionError` | `exceptions.py` | 非法版本字符串异常 |
| `InvalidRangeError` | `exceptions.py` | 非法范围表达式异常 |

## Semver 2.0 版本结构

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
  │     │     │      │            │
  │     │     │      │            └─ 构建元数据（可选，不影响比较）
  │     │     │      └────────────── 预发布标签（可选，影响比较）
  │     │     └───────────────────── 修订号（必填，非负整数，无前导零）
  │     └─────────────────────────── 次版本号（必填，非负整数，无前导零）
  └───────────────────────────────── 主版本号（必填，非负整数，无前导零）
```

示例：

```
1.2.3              → 正式版本
1.2.3-alpha        → 含预发布标签
1.2.3+build.42     → 含构建元数据
1.2.3-rc.1+build.5 → 预发布 + 构建元数据
```

## 预发布标签优先级规则

1. **核心比较优先**：先比较 MAJOR → MINOR → PATCH（数值比较）
2. **正式版 > 预发布版**：核心版本相同时，无预发布标签的版本优先级更高
   - `1.0.0 > 1.0.0-rc.1`
3. **逐段比较**：两个预发布版本从左到右逐段比较点号分隔的标识符
4. **数值标识符**：按数值比较（`beta.2 < beta.11`）
5. **字母标识符**：按字典序比较（`alpha < beta`）
6. **数值 < 字母**：纯数字标识符优先级始终低于字母标识符（`1.0.0-1 < 1.0.0-alpha`）
7. **短者较低**：所有前置标识符相同时，标识符更少的版本优先级更低（`alpha < alpha.1`）

完整优先级示例：

```
1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta
< 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0
```

## 构建元数据剥离策略

- 构建元数据（`+` 号后内容）**不参与**优先级比较
- `1.0.0+build1 == 1.0.0+build2`
- `1.0.0+build == 1.0.0`（无构建元数据）
- 使用 `without_build_metadata()` 方法获取剥离构建元数据后的版本字符串

## 范围表达式语法

| 语法 | 含义 | 示例 |
|---|---|---|
| `=X.Y.Z` | 精确匹配 | `=1.2.3` |
| `>=X.Y.Z` | 大于等于 | `>=1.2.3` |
| `>X.Y.Z` | 大于 | `>1.0.0` |
| `<=X.Y.Z` | 小于等于 | `<=2.0.0` |
| `<X.Y.Z` | 小于 | `<2.0.0` |
| 空格分隔 | 多条件 AND 组合 | `>=1.2.3 <2.0.0` |

多个条件以空格分隔，全部满足才判定为满足范围。

## 使用示例

### 版本解析

```python
from solocoder_py.semver import SemverVersion

v = SemverVersion.parse("1.2.3-alpha+build.1")
v.major           # 1
v.minor           # 2
v.patch           # 3
v.prerelease      # "alpha"
v.build_metadata  # "build.1"
str(v)            # "1.2.3-alpha+build.1"
```

### 版本比较

```python
from solocoder_py.semver import SemverVersion

v1 = SemverVersion.parse("1.0.0")
v2 = SemverVersion.parse("1.0.0-alpha")

v1 > v2   # True — 正式版优先于预发布版
v1 == v2  # False

v3 = SemverVersion.parse("1.0.0+build1")
v4 = SemverVersion.parse("1.0.0+build2")
v3 == v4  # True — 构建元数据不影响比较
```

### 构建元数据剥离

```python
from solocoder_py.semver import SemverVersion

v = SemverVersion.parse("1.2.3-alpha+build.1")
v.without_build_metadata()  # "1.2.3-alpha"
```

### 范围满足判定

```python
from solocoder_py.semver import SemverVersion, VersionRange

r = VersionRange.parse(">=1.2.3 <2.0.0")
r.satisfies(SemverVersion.parse("1.5.0"))  # True
r.satisfies(SemverVersion.parse("2.0.0"))  # False

r2 = VersionRange.parse("=1.2.3")
r2.satisfies(SemverVersion.parse("1.2.3+build"))  # True
```
