# Log Level 模块

本模块提供日志级别动态控制器，支持按 Logger 粒度的级别覆盖、层级继承传播和运行时热切换。

## 模块功能

- **按 Logger 粒度的级别覆盖**：每个 Logger 通过点号分隔的层级名称标识（如 `app`、`app.service`、`app.service.db`），可独立设置日志级别
- **级别继承传播**：未显式设置级别的 Logger 自动向上查找父级 Logger 的级别，直到根 Logger；若均无显式级别则使用默认级别 INFO
- **运行时热切换**：随时修改任意 Logger 的级别，修改立即生效，受继承影响的子孙 Logger 同步变更

## 核心类

### LogLevel

日志级别的枚举类型，继承自 `IntEnum`，定义五个级别及对应数值：

| 级别 | 数值 |
|------|------|
| DEBUG | 10 |
| INFO | 20 |
| WARNING | 30 |
| ERROR | 40 |
| CRITICAL | 50 |

级别数值关系为 DEBUG < INFO < WARNING < ERROR < CRITICAL，日志级别大于等于 Logger 当前生效级别时输出。

### LogLevelManager

日志级别动态控制器，使用内存数据结构管理所有 Logger 的级别配置。

| 方法 | 说明 |
|------|------|
| `set_level(name, level)` | 为指定 Logger 设置日志级别，立即生效 |
| `get_effective_level(name)` | 获取指定 Logger 的当前生效级别（考虑继承） |
| `is_enabled(name, level)` | 判断指定 Logger 在给定级别下是否应输出日志 |
| `clear_level(name)` | 清除指定 Logger 的显式级别设置，返回是否成功 |
| `has_explicit_level(name)` | 检查指定 Logger 是否有显式级别设置 |
| `clear_all()` | 清除所有 Logger 的显式级别设置 |

## 级别继承传播规则

1. 每个 Logger 按名称通过点号分隔形成层级关系，父 Logger 名称为去掉最后一段点号后的名称
2. 当 Logger 有显式级别时，直接使用该级别
3. 当 Logger 无显式级别时，沿层级向上查找父级 Logger 的显式级别
4. 若一直查找到根 Logger（空字符串 `""`）也无显式级别，则使用默认级别 INFO
5. 已显式设置级别的子孙 Logger 不受父级变更影响

## 热切换机制

调用 `set_level()` 修改任意 Logger 的级别后，修改立即生效：

- 该 Logger 自身的生效级别立即更新
- 所有未显式设置级别且通过继承获取该 Logger 级别的子孙 Logger，其生效级别同步更新
- 已显式设置级别的子孙 Logger 不受影响
- 无需重启或刷新，下一次 `is_enabled()` 调用即反映新配置

## 使用示例

```python
from solocoder_py.log_level import LogLevel, LogLevelManager

mgr = LogLevelManager()

# 设置根 Logger 级别
mgr.set_level("app", "WARNING")

# 子 Logger 综合父级级别
mgr.get_effective_level("app.service")  # WARNING（继承）
mgr.get_effective_level("app.service.db")  # WARNING（继承）

# 为子 Logger 设置独立级别
mgr.set_level("app.service", "DEBUG")
mgr.get_effective_level("app.service")  # DEBUG（显式设置）
mgr.get_effective_level("app.service.db")  # DEBUG（继承自 app.service）

# 判断日志是否应输出
mgr.is_enabled("app.service", "DEBUG")  # True
mgr.is_enabled("app", "DEBUG")  # False（app 级别为 WARNING）

# 运行时热切换
mgr.set_level("app", "DEBUG")
mgr.is_enabled("app", "DEBUG")  # True
mgr.is_enabled("app.service", "DEBUG")  # True（app.service 有显式 DEBUG）

# 清除显式级别后重新继承
mgr.clear_level("app.service")
mgr.get_effective_level("app.service")  # DEBUG（继承自 app）
```
