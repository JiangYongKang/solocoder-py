# 公平读写锁域模块

## 模块功能

本模块实现了基于内存数据结构模拟的公平读写锁（Read-Write Lock），支持以下核心能力：

1. **读共享（Read Sharing）**：多个读者线程可以同时持有读锁，适用于读多写少的并发场景，可显著提高并发吞吐量。
2. **写独占（Write Exclusivity）**：写者持有写锁时，不允许任何读者或其他写者进入，确保写操作的原子性和数据一致性。
3. **写优先防饥饿（Write-Priority / Anti-Writer-Starvation）**：当有写者在等待获取锁时，后续到达的新读者不会插队获取锁，而是进入等待队列排在等待写者之后，防止在写入密集场景下写者因读者持续涌入而永远饿死。
4. **可注入调度器（Injectable Scheduler）**：锁的内部调度逻辑不直接依赖 `time.sleep` 或真实线程调度，而是通过一个可注入的 `Scheduler` 抽象来模拟锁的获取等待和公平排队。实际测试时可通过注入测试调度器验证公平性，而不需要真正启动多线程。
5. **锁重入（Reentrancy）**：同一线程可对同一种锁模式进行重入（读者重入读锁、写者重入写锁），内部维护重入计数。
6. **升级保护**：不允许锁升级（持有写锁时获取读锁、持有读锁时获取写锁），避免死锁风险。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `RWLockError` | 读写锁模块异常基类 |
| `RWLockNotHeldError` | 线程未持有锁却尝试释放锁，或释放者身份不匹配 |
| `RWLockNotAcquiredError` | 获取锁失败（预留异常类型） |
| `RWLockUpgradeError` | 锁升级被拒绝（持有写锁获取读锁、或持有读锁获取写锁） |

### models.py

| 类名 | 职责 |
|------|------|
| `LockMode` | 锁模式枚举：`FREE`（空闲）、`READ`（读模式）、`WRITE`（写模式） |
| `WaiterType` | 等待者类型枚举：`READER`（读者）、`WRITER`（写者） |
| `Waiter` | 等待者数据模型，记录线程 ID、等待者类型、排队票号 |
| `RWLockState` | 读写锁完整状态数据模型，包括当前模式、持有者、等待队列、票号计数器等，并提供多个便捷属性查询 |

### scheduler.py

| 类名 | 职责 |
|------|------|
| `Parked` | 特殊异常，用于 `ManualScheduler.park()` 抛出以模拟线程被挂起（控制流中断） |
| `Scheduler` | 调度器抽象基类，定义 `current_thread_id()`、`park()`、`unpark()`、`unpark_all()` 四个抽象方法 |
| `ManualScheduler` | 手动调度器实现，用于单线程测试环境。可通过 `set_current_thread()` 模拟切换当前线程；`park()` 将线程标记为已挂起并抛出 `Parked` 异常；`unpark()` 和 `unpark_all()` 用于唤醒等待线程 |

### lock.py

| 类名 | 职责 |
|------|------|
| `RWLock` | 公平读写锁核心实现。提供 `acquire_read()`（获取读锁）、`acquire_write()`（获取写锁）、`release()`（释放锁）三个主要方法。内部通过两个等待队列（读者等待队列、写者等待队列）和写优先策略实现公平调度 |

## 公平性保证策略

### 写优先防饥饿机制

本模块采用"写优先"（Writer-Preference）策略来防止写者饥饿，核心规则如下：

1. **读者获取条件**：读者仅在以下两种情况可立即获取读锁：
   - 锁处于 `FREE` 空闲状态；
   - 锁处于 `READ` 读模式，且**写者等待队列为空**（即没有写者在等待）。

2. **写者插队拦截**：当有写者正在等待（写者等待队列非空）时，新到达的读者无法直接获取读锁，而是必须进入读者等待队列排队。这确保了等待中的写者不会被持续涌入的读者"插队"而永远获取不到锁。

3. **释放唤醒优先级**：当锁被释放后回到 `FREE` 状态时，`_wake_waiters()` 方法按以下优先级唤醒等待者：
   - **优先唤醒写者**：如果写者等待队列非空，唤醒队首的第一个写者，将锁切换为 `WRITE` 模式并分配给该写者（FIFO 顺序）。
   - **其次批量唤醒读者**：如果没有等待的写者，则一次性批量唤醒读者等待队列中的所有读者，将锁切换为 `READ` 模式并将所有等待读者同时登记为持有者。

### 公平排队顺序

- 写者之间采用 FIFO（先进先出）顺序，先排队的写者先被唤醒。
- 被写者阻塞的读者们会在写者释放后被同时批量唤醒，全部同时获得读锁。

### 状态转移图

```
                    新读者到达 & 无等待写者
     ┌──────────────────────────────────────────────┐
     │                                              ▼
┌─────────┐  读者获取/写者获取                ┌─────────┐
│  FREE   │ ───────────────────────────────► │  READ   │
└─────────┘                              ┌────┴────┬────┘
     ▲                                   │         │
     │                                   │         │ 最后一个读者 release()
     │                                   │         ▼
     │                                   │   ┌─────────┐
     │ 写者 release() / 最后读者 release()│   │有等待写者?│
     │                                   │   └────┬────┘
     │                                   │        │
     │              写者获取              ▼        │Yes
     │  ┌────────────────────────────  WRITE ◄────┘
     │  │                                 │
     │  │                                 │ 写者 release()
     │  │                                 ▼
     │  │                           检查等待队列
     │  │                                 │
     │  └─────────────────────────────────┘
     │              No
     ▼
  检查等待队列
     │
     ├─► 有等待写者? ──Yes──► 唤醒第一个写者 → WRITE
     │
     └─► No ──► 有等待读者? ──Yes──► 批量唤醒所有读者 → READ
                     │
                     No
                     ▼
                  保持 FREE
```

## 使用示例

### 基本使用：读共享

```python
from solocoder_py.rwlock import ManualScheduler, RWLock, Parked

scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

# 线程 reader-1 获取读锁
scheduler.set_current_thread("reader-1")
lock.acquire_read()

# 线程 reader-2 同时获取读锁（读共享）
scheduler.set_current_thread("reader-2")
lock.acquire_read()

print(f"Reader count: {lock.state.reader_count}")  # 2
print(f"Mode: {lock.state.mode}")  # READ

# 释放读锁
scheduler.set_current_thread("reader-1")
lock.release()
scheduler.set_current_thread("reader-2")
lock.release()
```

### 写独占与写优先

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

# 写者获取写锁
scheduler.set_current_thread("writer-1")
lock.acquire_write()
print(f"Mode: {lock.state.mode}")  # WRITE

# 新读者尝试获取，被阻塞（进入等待队列）
try:
    scheduler.set_current_thread("reader-1")
    lock.acquire_read()
except Parked:
    pass  # 模拟线程挂起
print(f"Reader parked: {scheduler.is_parked('reader-1')}")  # True

# 写者释放，读者被唤醒
scheduler.set_current_thread("writer-1")
lock.release()
print(f"Reader parked: {scheduler.is_parked('reader-1')}")  # False
print(f"Mode: {lock.state.mode}")  # READ
```

### 写优先防饥饿场景

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

# reader-1 持有读锁
scheduler.set_current_thread("reader-1")
lock.acquire_read()

# writer-1 到达，无法获取写锁，进入等待队列
try:
    scheduler.set_current_thread("writer-1")
    lock.acquire_write()
except Parked:
    pass

# reader-2 到达——由于 writer-1 在等待，reader-2 不能插队！
try:
    scheduler.set_current_thread("reader-2")
    lock.acquire_read()
except Parked:
    pass
print(f"reader-2 parked: {scheduler.is_parked('reader-2')}")  # True

# reader-1 释放锁
scheduler.set_current_thread("reader-1")
lock.release()

# 写者 writer-1 优先被唤醒（不是 reader-2）
print(f"Writer thread: {lock.state.writer_thread_id}")  # writer-1
print(f"Mode: {lock.state.mode}")  # WRITE
print(f"reader-2 still parked: {scheduler.is_parked('reader-2')}")  # True

# writer-1 释放锁后，reader-2 才能被唤醒
scheduler.set_current_thread("writer-1")
lock.release()
print(f"Mode: {lock.state.mode}")  # READ
print(f"Reader count: {lock.state.reader_count}")  # 1
```

### 显式指定线程 ID

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

# 不依赖 scheduler.set_current_thread，直接传入 thread_id 参数
lock.acquire_read(thread_id="worker-A")
lock.acquire_read(thread_id="worker-B")

print(f"Reader count: {lock.state.reader_count}")  # 2

lock.release(thread_id="worker-A")
lock.release(thread_id="worker-B")
```

### 可重入锁

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

# 同一写者多次获取写锁（重入）
scheduler.set_current_thread("writer-1")
lock.acquire_write()
lock.acquire_write()
lock.acquire_write()
print(f"Write lock count: {lock.state.write_lock_count}")  # 3

# 需要释放相同次数才真正释放
lock.release()  # 计数变为 2
print(f"Mode: {lock.state.mode}")  # WRITE
lock.release()  # 计数变为 1
lock.release()  # 计数变为 0，完全释放
print(f"Mode: {lock.state.mode}")  # FREE
```

### 异常场景：升级被拒绝

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

scheduler.set_current_thread("thread-1")
lock.acquire_write()

try:
    lock.acquire_read()  # 持有写锁时尝试获取读锁（升级）
except RWLockUpgradeError as e:
    print(f"Upgrade rejected: {e}")
```

### 异常场景：未持有锁时释放

```python
scheduler = ManualScheduler()
lock = RWLock(scheduler=scheduler)

scheduler.set_current_thread("thread-1")
try:
    lock.release()
except RWLockNotHeldError as e:
    print(f"Release rejected: {e}")
```

## 实现设计说明

### 无需真实线程的测试能力

本模块的核心设计目标之一是"无需启动真实线程即可测试锁的公平性"。实现思路：

1. `Scheduler` 抽象将"线程标识获取"和"线程挂起/唤醒"的职责从锁的调度逻辑中解耦。
2. `ManualScheduler` 提供手动控制能力：
   - 通过 `set_current_thread(thread_id)` 模拟"当前执行线程"的切换。
   - `park(thread_id)` 将线程加入"已挂起"集合并抛出 `Parked` 异常——在测试代码中捕获该异常即可模拟"线程因等待锁而被阻塞"。
   - `unpark(thread_id)` 和 `unpark_all(thread_ids)` 将线程从"已挂起"集合中移除，模拟线程被唤醒。
3. 锁的 `release()` 方法在释放锁后，会根据写优先策略主动调用 `scheduler.unpark()` 或 `scheduler.unpark_all()` 来唤醒等待线程，与真实 `Condition` 变量的 `notify()` / `notify_all()` 行为一致。

这种设计使得整个读写锁的状态转移、排队顺序、公平性策略都可以在单线程中通过精心编排的步骤进行精确测试。

## 运行测试

```bash
pytest tests/rwlock/ -v
```
