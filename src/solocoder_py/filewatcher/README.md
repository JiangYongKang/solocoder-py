# FileWatcher - 文件变更监听器

## 模块功能

FileWatcher 是一个高性能的文件变更监听器模块，使用内存数据结构模拟文件系统事件源，支持递归目录监控、事件去抖合并和 Glob 模式过滤。

## 核心类职责

### ChangeType
枚举类型，表示文件变更类型：
- `CREATED`: 文件或目录被创建
- `MODIFIED`: 文件被修改
- `DELETED`: 文件或目录被删除
- `RENAMED`: 文件或目录被重命名

### FileEvent
文件事件数据类，包含：
- `change_type`: 变更类型
- `path`: 受影响的路径
- `timestamp`: 变更时间（带时区）
- `old_path`: 重命名时的旧路径（可选）

### MemoryEventSource
内存模拟的文件系统事件源，提供以下功能：
- 维护文件系统状态（路径是否存在、是否为目录、父子关系）
- 支持创建、修改、删除、重命名操作
- 自动跟踪监控的路径
- 发出原始文件变更事件

### GlobFilter
Glob 模式过滤器，支持：
- 包含模式：只监控匹配的文件路径
- 排除模式：不监控匹配的文件路径
- 通配符 `*` 匹配任意字符
- 双通配符 `**` 匹配任意深度的路径

### EventDebouncer
事件去抖合并器，负责：
- 在可配置的时间窗口内收集事件
- 同一路径的同类型事件只保留最后一次
- 创建+删除事件抵消（最终文件不存在则视为无变化）
- 窗口结束后统一触发回调

### PendingEvents
同一路径的待处理事件集合，实现事件合并逻辑。

### FileWatcher
核心文件监听器类，整合所有组件：
- 管理监控生命周期（启动/停止）
- 协调事件源、过滤器和去抖器
- 提供模拟文件系统操作的便捷方法
- 自动递归监控新增的子目录

## 递归监控机制

1. 启动时注册根目录到监控范围
2. 当监控范围内创建新目录时，自动将该目录加入监控
3. 删除目录时，递归移除该目录及其所有子目录的监控
4. 重命名目录时，更新所有子路径的监控状态
5. 停止监控时，一次性清除所有监控路径

## 事件去抖合并策略

### 时间窗口
事件到达时记录首次出现时间，当 `当前时间 - 首次出现时间 >= 去抖窗口` 时触发合并。

### 合并规则
1. **只有创建**：保留最后一次创建事件，若期间有修改则更新为修改时间
2. **只有删除**：保留最后一次删除事件
3. **只有修改**：保留最后一次修改事件
4. **创建 + 删除**：
   - 删除在创建之后：两个事件抵消，不产生最终事件
   - 创建在删除之后：保留创建事件
5. **重命名**：保留重命名事件，若后续有修改则转为修改事件
6. **混合事件**：以最后一个事件的类型为准

## Glob 模式过滤规则

### 过滤时机
过滤在事件生成阶段生效，被排除的文件变更：
- 不产生事件
- 不消耗去抖窗口
- 不触发回调

### 匹配优先级
1. 先检查排除模式，匹配则直接排除
2. 再检查包含模式（如果设置了），匹配则通过
3. 未设置包含模式时，所有未被排除的路径都通过

### 通配符说明
- `*`: 匹配任意字符（不包括路径分隔符）
- `**`: 匹配任意深度的路径
- `?`: 匹配单个字符
- `[seq]`: 匹配序列中的任意字符
- `[!seq]`: 匹配不在序列中的任意字符

### 示例
- `*.py`: 匹配所有 Python 文件
- `**/*.txt`: 匹配任意深度的文本文件
- `src/**/*.py`: 匹配 src 目录下任意深度的 Python 文件
- `!__pycache__/**`: 排除 __pycache__ 目录

## 使用示例

### 基本使用
```python
from datetime import timedelta
from pathlib import Path
from solocoder_py.filewatcher import FileWatcher, FileEvent

def on_events(events: list[FileEvent]) -> None:
    for event in events:
        print(f"{event.change_type}: {event.path} at {event.timestamp}")

watcher = FileWatcher(
    root_path=Path("/path/to/watch"),
    callback=on_events,
    debounce_window=timedelta(seconds=0.5),
    include_patterns=["*.py"],
    exclude_patterns=["__pycache__/**", "*.pyc"],
)

watcher.start()

# 模拟文件系统变更
watcher.simulate_create_file("main.py")
watcher.simulate_modify_file("main.py")
watcher.simulate_delete_file("temp.txt")

# 触发去抖窗口检查
watcher.tick()

watcher.stop()
```

### 仅使用 Glob 过滤器
```python
from solocoder_py.filewatcher import GlobFilter

filter = GlobFilter(
    include_patterns=["**/*.py", "**/*.txt"],
    exclude_patterns=["**/__pycache__/**", "**/.git/**"],
)

filter.matches("src/main.py")        # True
filter.matches("tests/test.txt")     # True
filter.matches("__pycache__/x.pyc")  # False
filter.matches(".git/config")        # False
```

### 仅使用事件去抖器
```python
from datetime import timedelta
from solocoder_py.filewatcher import EventDebouncer, FileEvent, ChangeType

def on_flush(events: list[FileEvent]) -> None:
    print(f"Flushed {len(events)} events")

debouncer = EventDebouncer(
    debounce_window=timedelta(seconds=0.5),
    callback=on_flush,
)
debouncer.start()

# 添加多个同路径事件
debouncer.add_event(FileEvent.created(Path("test.py")))
debouncer.add_event(FileEvent.modified(Path("test.py")))
debouncer.add_event(FileEvent.modified(Path("test.py")))

# 等待窗口结束后自动合并为一个事件
debouncer.check_and_flush()
```

### 递归监控子目录
```python
watcher = FileWatcher(
    root_path=Path("/project"),
    callback=on_events,
)
watcher.start()

# 创建子目录会自动被监控
watcher.simulate_create_directory("src")
watcher.simulate_create_directory("src/utils")

# 子目录中的文件变更会被捕获
watcher.simulate_create_file("src/utils/helpers.py")

watcher.tick()
watcher.stop()
```
