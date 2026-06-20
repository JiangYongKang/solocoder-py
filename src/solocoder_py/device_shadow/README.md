# Device Shadow（数字孪生）

设备影子模块实现了 IoT 场景中的数字孪生模式，用于在内存中维护设备状态的镜像，支持云端与设备之间的状态同步与差异感知。

## 模块功能

- **双态模型**：每个设备影子维护 `desired`（预期态）和 `reported`（上报态）两个独立状态副本
- **状态合并**：将 desired 和 reported 合并为完整状态视图
- **差异计算**：结构化对比两个状态的差异
- **乐观锁版本同步**：基于单调递增版本号防止并发写入冲突

## 核心类

### `DeviceShadow`

设备影子的主类，维护一个设备的双态数据与版本信息。

| 属性/方法 | 说明 |
|---|---|
| `device_id` | 设备唯一标识 |
| `desired` | 预期态的只读副本 |
| `reported` | 上报态的只读副本 |
| `version` | 当前版本号 |
| `set_desired(state, expected_version)` | 设置预期态，需传入预期版本号 |
| `set_reported(state, expected_version)` | 设置上报态，需传入预期版本号 |
| `merge()` | 合并 desired 和 reported 为完整状态 |
| `diff()` | 计算 desired 与 reported 的结构化差异 |
| `to_dict()` | 将影子数据导出为字典 |

### `ShadowDiff`

差异计算结果的结构化数据类。

| 属性 | 说明 |
|---|---|
| `desired_only` | 仅存在于 desired 中的字段（期望但未达成） |
| `reported_only` | 仅存在于 reported 中的字段（设备实际有但未期望） |
| `value_diff` | 相同路径但值不同的字段 |
| `has_differences` | 是否存在任何差异 |

### `FieldDiff`

单个字段差异的描述。

| 属性 | 说明 |
|---|---|
| `path` | 字段路径（嵌套时用 `.` 分隔，如 `config.network.ip`） |
| `desired_value` | desired 端的值（不存在时为 `None`） |
| `reported_value` | reported 端的值（不存在时为 `None`） |

### 异常类

| 异常 | 说明 |
|---|---|
| `DeviceShadowError` | 所有模块异常的基类 |
| `VersionMismatchError` | 乐观锁版本不匹配 |
| `InvalidVersionError` | 版本号为负数等无效值 |
| `NonSerializableValueError` | 状态包含非 JSON 可序列化的值 |
| `InvalidStateError` | 状态为 None 或非 dict 类型 |

## 双态模型语义

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│  Cloud App   │ ──set──▶│  DeviceShadow    │◀──set───│   Device    │
│              │ desired │                  │ reported│             │
│              │         │  desired: {...}  │         │             │
│              │         │  reported: {...} │         │             │
│              │◀─merge──│                  │────diff─▶│             │
│              │         │  version: N      │         │             │
└─────────────┘         └──────────────────┘         └─────────────┘
```

- **desired（预期态）**：由云端应用设置，表示期望设备达到的目标状态
- **reported（上报态）**：由设备上报，表示设备当前的实际状态
- 两个状态独立存储，互不覆盖

## 合并规则

`merge()` 将 desired 和 reported 合并为完整状态视图：

1. 以 desired 为基础
2. reported 中的字段覆盖 desired 中的同名字段（**reported 优先，设备实际值为准**）
3. desired 中存在但 reported 中不存在的字段保留（表示尚未达成的期望）
4. reported 中存在但 desired 中不存在的字段添加（设备额外属性）
5. 嵌套字典递归合并

## 差异计算规则

`diff()` 返回 `ShadowDiff` 结构，包含三部分：

| 差异类型 | 含义 | 示例 |
|---|---|---|
| `desired_only` | 仅 desired 中存在 | 云端期望设置 `fan=on`，但设备尚未上报 |
| `reported_only` | 仅 reported 中存在 | 设备上报了 `pressure=1013`，但云端未期望 |
| `value_diff` | 相同路径值不同 | desired `temperature=25`，reported `temperature=22` |

嵌套字段路径使用 `.` 分隔，如 `config.network.ip`。

## 乐观锁版本同步机制

每个设备影子维护一个单调递增的版本号：

- 初始版本号默认为 `1`（可通过 `initial_version` 参数设为 `0`）
- 每次成功的 `set_desired` 或 `set_reported` 操作使版本号 +1
- 调用方必须传入 `expected_version`，表示其基于哪个版本进行修改
- 如果 `expected_version` 与当前版本不一致，抛出 `VersionMismatchError`，拒绝本次更新
- 版本号为负数时抛出 `InvalidVersionError`

```
Client A: read (version=1) ────────────────────── set_desired(v=1) ✓ → version=2
Client B: read (version=1) ───── set_desired(v=1) ✗ VersionMismatchError!
                                          (actual version is now 2)
```

## 使用示例

### 基本用法

```python
from solocoder_py.device_shadow import DeviceShadow

shadow = DeviceShadow(device_id="thermostat-001")

# 云端设置预期态
shadow.set_desired({"temperature": 25, "fan": "on"}, expected_version=1)
# version → 2

# 设备上报实际状态
shadow.set_reported({"temperature": 22, "fan": "on"}, expected_version=2)
# version → 3

# 查看合并状态（reported 优先）
merged = shadow.merge()
# {"temperature": 22, "fan": "on"}

# 查看差异
diff = shadow.diff()
# desired_only: []  (无仅 desired 的字段)
# reported_only: []  (无仅 reported 的字段)
# value_diff: [FieldDiff(path="temperature", desired_value=25, reported_value=22)]
```

### 乐观锁冲突处理

```python
shadow = DeviceShadow(device_id="sensor-001")
shadow.set_desired({"mode": "auto"}, expected_version=1)  # version → 2

try:
    shadow.set_desired({"mode": "manual"}, expected_version=1)  # 过期版本
except VersionMismatchError as e:
    print(f"冲突: 期望版本 {e.expected}, 实际版本 {e.actual}")
    # 重新读取最新状态后重试
    current_version = shadow.version  # 2
    shadow.set_desired({"mode": "manual"}, expected_version=current_version)  # ✓
```

### 深层嵌套 JSON

```python
shadow = DeviceShadow(device_id="gateway-001")
shadow.set_desired({
    "config": {"network": {"ip": "192.168.1.1", "port": 8080}}
}, expected_version=1)

shadow.set_reported({
    "config": {"network": {"ip": "10.0.0.1", "subnet": "255.255.255.0"}}
}, expected_version=2)

merged = shadow.merge()
# {"config": {"network": {"ip": "10.0.0.1", "port": 8080, "subnet": "255.255.255.0"}}}

diff = shadow.diff()
# value_diff:     [FieldDiff(path="config.network.ip", ...)]
# desired_only:   [FieldDiff(path="config.network.port", ...)]
# reported_only:  [FieldDiff(path="config.network.subnet", ...)]
```
