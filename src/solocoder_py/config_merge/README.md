# 配置分层合并模块 (Config Merge)

## 模块功能

配置分层合并模块提供了一个灵活的多层配置管理系统，支持将不同来源的配置按照优先级进行合并。模块使用内存数据结构模拟数据源，提供了深层次嵌套配置的智能合并、灵活的数组合并策略以及临时覆盖机制。

## 核心类的职责

### ConfigLayerType (枚举)
定义配置层级的类型：
- `DEFAULT`: 默认配置层，优先级最低
- `ENVIRONMENT`: 环境配置层，中等优先级
- `OVERRIDE`: 覆盖配置层，优先级最高（存储层）

### ArrayMergeStrategy (枚举)
定义数组类型配置的合并策略：
- `REPLACE`: 完全覆盖策略，高层级数组替换低层级数组
- `APPEND`: 追加合并策略，高层级数组元素追加到低层级数组之后

### ConfigLayer (数据类)
表示单个配置层级的数据存储：
- 存储具体的配置数据（字典类型）
- 提供基本的 get/set/update/clear 操作
- 自动进行数据深拷贝以保证数据隔离

### ConfigMergeManager (核心管理器)
配置合并的核心管理类，负责：
- 管理三个配置层的数据存储和访问
- 执行多层配置的优先级合并
- 处理深度嵌套配置的逐字段合并
- 支持不同的数组合并策略
- 提供临时覆盖配置功能
- 检测循环引用和类型冲突

## 配置层级模型

模块采用三层配置架构，优先级从低到高依次为：

```
默认配置层 (DEFAULT) < 环境配置层 (ENVIRONMENT) < 覆盖配置层 (OVERRIDE)
```

**合并规则：**
1. 合并时从最低优先级层开始，逐层向上覆盖
2. 对于字典类型的配置项，按照字段逐字段深度合并，而非整体替换
3. 高优先级层的同名配置项会覆盖低优先级层的配置
4. 如果低优先级层有某配置项但高优先级层没有，则保留低优先级的配置

### 示例：三层同 key 的逐层覆盖

```python
# 默认层配置
default_config = {
    "app": {
        "name": "MyApp",
        "version": "1.0.0",
        "debug": False,
    },
    "server": {
        "host": "localhost",
        "port": 8080,
    },
}

# 环境层配置（覆盖部分字段）
environment_config = {
    "app": {
        "debug": True,
    },
    "server": {
        "host": "0.0.0.0",
    },
}

# 覆盖层配置（再覆盖部分字段）
override_config = {
    "server": {
        "port": 9090,
    },
}

# 合并结果：
# {
#     "app": {
#         "name": "MyApp",      # 来自默认层
#         "version": "1.0.0",   # 来自默认层
#         "debug": True,        # 来自环境层（覆盖了默认层的 False）
#     },
#     "server": {
#         "host": "0.0.0.0",    # 来自环境层（覆盖了默认层的 localhost）
#         "port": 9090,         # 来自覆盖层（覆盖了环境层的 8080）
#     },
# }
```

## 合并策略

### 深度嵌套配置合并

对于字典类型的嵌套配置，模块会递归地逐字段合并，而非整体替换：

```python
# 默认层
default = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "credentials": {
            "username": "admin",
            "password": "default",
        },
        "options": {
            "ssl": False,
            "timeout": 30,
        },
    },
}

# 环境层只覆盖 credentials.password 和 options.ssl
environment = {
    "database": {
        "credentials": {
            "password": "env_secret",
        },
        "options": {
            "ssl": True,
        },
    },
}

# 合并结果：
# {
#     "database": {
#         "host": "localhost",           # 保留默认值
#         "port": 5432,                  # 保留默认值
#         "credentials": {
#             "username": "admin",       # 保留默认值
#             "password": "env_secret",  # 被环境层覆盖
#         },
#         "options": {
#             "ssl": True,               # 被环境层覆盖
#             "timeout": 30,             # 保留默认值
#         },
#     },
# }
```

### 数组合并策略

模块提供两种数组合并策略，可在合并时根据业务场景选择：

#### 1. REPLACE 策略（默认）
高层级数组完全替换低层级数组：

```python
# 默认层
default = {"features": ["auth", "logging", "cache"]}

# 环境层
environment = {"features": ["auth", "metrics"]}

# 使用 REPLACE 策略合并结果：
# {"features": ["auth", "metrics"]}
```

#### 2. APPEND 策略
高层级数组元素追加到低层级数组之后：

```python
# 默认层
default = {"features": ["auth", "logging", "cache"]}

# 环境层
environment = {"features": ["metrics", "tracing"]}

# 使用 APPEND 策略合并结果：
# {"features": ["auth", "logging", "cache", "metrics", "tracing"]}
```

### 类型冲突处理

当同一配置键在不同层的类型不兼容时（例如一层是字典，另一层是列表），会抛出 `ConfigTypeConflictError` 异常。

## 临时覆盖功能

`ConfigMergeManager.merge()` 方法支持 `temp_override` 参数，允许传入一组临时配置：

- 临时覆盖的优先级最高（比 OVERRIDE 层还高）
- 临时覆盖仅在当次查询中生效
- 不会修改已存在的各层配置数据

```python
# 设置各层配置
manager.set_layer_data(ConfigLayerType.DEFAULT, {"app": {"debug": False}})
manager.set_layer_data(ConfigLayerType.OVERRIDE, {"app": {"debug": True}})

# 正常合并结果：debug = True
result1 = manager.merge()
# result1 = {"app": {"debug": True}}

# 使用临时覆盖：debug = False（仅本次生效）
result2 = manager.merge(temp_override={"app": {"debug": False}})
# result2 = {"app": {"debug": False}}

# 再次正常合并，临时覆盖不生效
result3 = manager.merge()
# result3 = {"app": {"debug": True}}
```

## 循环引用检测

模块会自动检测配置数据中的循环引用，防止合并过程中出现无限递归。如果检测到循环引用，会抛出 `CircularReferenceError` 异常。

## 使用示例

### 基本使用

```python
from solocoder_py.config_merge import (
    ArrayMergeStrategy,
    ConfigLayerType,
    ConfigMergeManager,
)

# 创建管理器实例
manager = ConfigMergeManager()

# 设置各层配置
manager.set_layer_data(
    ConfigLayerType.DEFAULT,
    {
        "app": {"name": "MyApp", "version": "1.0.0", "debug": False},
        "server": {"host": "localhost", "port": 8080},
        "features": ["auth", "logging"],
    },
)

manager.set_layer_data(
    ConfigLayerType.ENVIRONMENT,
    {
        "app": {"debug": True},
        "server": {"host": "0.0.0.0"},
        "features": ["metrics"],
    },
)

manager.set_layer_data(
    ConfigLayerType.OVERRIDE,
    {
        "server": {"port": 9090},
    },
)

# 使用默认的 REPLACE 策略合并
merged = manager.merge()
print(merged)
# {
#     "app": {"name": "MyApp", "version": "1.0.0", "debug": True},
#     "server": {"host": "0.0.0.0", "port": 9090},
#     "features": ["metrics"],
# }

# 使用 APPEND 策略合并数组
merged_append = manager.merge(array_strategy=ArrayMergeStrategy.APPEND)
print(merged_append)
# {
#     "app": {"name": "MyApp", "version": "1.0.0", "debug": True},
#     "server": {"host": "0.0.0.0", "port": 9090},
#     "features": ["auth", "logging", "metrics"],
# }

# 获取单个配置项
debug_mode = manager.get("app")  # 返回整个 app 字典
print(debug_mode)
# {"name": "MyApp", "version": "1.0.0", "debug": True}

# 使用临时覆盖
with_override = manager.merge(temp_override={"server": {"port": 3000}})
print(with_override["server"]["port"])  # 3000

# 再次合并，临时覆盖已失效
normal = manager.merge()
print(normal["server"]["port"])  # 9090
```

### 更新和清除配置层

```python
# 增量更新某层配置
manager.update_layer(
    ConfigLayerType.ENVIRONMENT,
    {"new_feature": True},
)

# 清除某层配置
manager.clear_layer(ConfigLayerType.OVERRIDE)

# 清除所有层配置
manager.clear_all()
```

### 访问嵌套配置

```python
# 通过 get_nested 方法访问深层嵌套配置
host = manager.get_nested(["server", "host"])
print(host)  # "0.0.0.0"

# 不存在时返回默认值
timeout = manager.get_nested(["server", "timeout"], default=60)
print(timeout)  # 60
```
