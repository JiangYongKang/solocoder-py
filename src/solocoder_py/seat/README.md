# 座位预留域模块

## 模块功能

本模块实现了基于内存数据结构模拟的座位预留系统，支持以下核心能力：

1. **座位基本操作**：查看可用座位、预留座位、取消预留、确认占用。
2. **并发抢座保护**：多个用户同时请求同一个座位时，只有第一个请求能成功预留，其余请求得到"已被占用"的结果，不会出现同一座位被重复分配。
3. **预留超时自动释放**：座位被预留后如果在指定时间内未确认占用，系统自动释放该座位使其重新变为可用状态。
4. **连座分配约束**：当用户请求连续 N 个座位时，系统只能在同一个连续区域内分配，不能将不相邻的座位拼凑返回。

## 核心类职责

### exceptions.py

| 类名 | 职责 |
|------|------|
| `SeatReservationError` | 座位预留模块异常基类 |
| `SeatNotFoundError` | 座位不存在 |
| `SeatAlreadyReservedError` | 座位已被预留（抢座失败） |
| `SeatAlreadyOccupiedError` | 座位已被占用 |
| `SeatNotReservedError` | 座位未被预留（取消/确认时） |
| `SeatReservationExpiredError` | 预留已超时自动释放 |
| `SeatReservationMismatchError` | 预留用户不匹配（非预留者尝试取消/确认） |
| `ConsecutiveSeatsNotFoundError` | 找不到指定数量的连续可用座位 |
| `InvalidSeatCountError` | 连座数量无效（<=0） |

### clock.py

| 类名 | 职责 |
|------|------|
| `Clock` | 时钟抽象基类，提供 `now()` 和 `sleep()` 接口 |
| `SystemClock` | 基于系统单调时钟的实现，用于生产环境 |
| `ManualClock` | 可手动推进时间的模拟时钟，用于单元测试 |

### models.py

| 类名 | 职责 |
|------|------|
| `SeatState` | 座位状态枚举：`AVAILABLE`（可用）、`RESERVED`（已预留）、`OCCUPIED`（已占用） |
| `SeatId` | 座位标识符不可变值对象，由 `row`（行号）和 `column`（列号）组成 |
| `Seat` | 座位数据模型，记录座位 ID、状态、预留者、预留时间、占用者等，并提供预留、取消预留、确认占用、强制释放等状态变更方法 |

### manager.py

| 类名 | 职责 |
|------|------|
| `SeatReservationManager` | 座位预留管理器，线程安全，维护所有座位的内存存储，提供查询可用座位、单座预留、连座预留、取消预留、确认占用等操作，内部自动处理超时释放 |

## 座位状态生命周期

```
                  reserve() 成功
     ┌──────────────────────────────────────────┐
     │                                          ▼
┌───────────┐  reserve() 成功             ┌───────────┐
│ AVAILABLE │ ─────────────────────────►  │ RESERVED  │
└─────┬─────┘                              └────┬──────┘
      │                                         │
      │                                         │ 超时 / cancel_reservation()
      │                                         ▼
      │                                    ┌─────────┐
      └────────────────────────────────────► AVAILABLE
                confirm_occupancy() 成功            │
                      │                            │
                      ▼                            │
                 ┌──────────┐                      │
                 │ OCCUPIED │ ◄────────────────────┘
                 └──────────┘  force_release() / 超时后被清理
```

### 状态转移说明

| 当前状态 | 触发事件 | 下一状态 | 说明 |
|---------|---------|---------|------|
| AVAILABLE | `reserve_seat()` 成功 | RESERVED | 用户成功预留座位 |
| RESERVED | `cancel_reservation()` 成功 | AVAILABLE | 用户主动取消预留 |
| RESERVED | `confirm_occupancy()` 成功 | OCCUPIED | 用户确认占用座位 |
| RESERVED | 预留超时 | AVAILABLE | 超过 `default_reservation_timeout` 未确认，自动释放 |
| OCCUPIED | `force_release_seat()` | AVAILABLE | 管理操作，强制释放已占用座位 |

## 连座分配算法

### 算法描述

连座分配采用**逐行扫描 + 滑动窗口**策略：

1. **逐行扫描**：按行号从小到大依次检查每一行。
2. **滑动窗口**：对每一行，从左到右扫描列号，维护一个连续可用座位的计数器：
   - 遇到可用座位：计数器 +1
   - 遇到不可用座位：计数器重置为 0
   - 当计数器达到请求数量 N 时，即找到从 `start_col` 到 `start_col + N - 1` 的连续块
3. **原子分配**：找到候选连续块后，在持锁状态下逐个预留座位；如果中途发现某座位不可用（理论上不会发生，因已持锁），则回滚已预留的座位并继续搜索。
4. **失败策略**：如果所有行扫描完毕仍找不到 N 个连续可用座位，抛出 `ConsecutiveSeatsNotFoundError`。

### 算法特性

- **确定性**：总是优先返回行号最小、列号最小的满足条件的连续块。
- **时间复杂度**：O(rows × columns)，即座位总数的线性扫描。
- **原子性**：整个连座分配过程在互斥锁保护下完成，不会出现部分分配。

### 示例

假设座位布局（X 表示已被预留/占用，. 表示可用）：

```
Row 0: . X . . . X . . . .
Row 1: . . . X . . . . . X
Row 2: . . . . . . . . . .
```

- 请求 N=3 连座：返回 Row0 columns [2,3,4]（第一行中首个满足的连续块）
- 请求 N=5 连座：跳过 Row0（最大连续 3 个）、Row1（最大连续 5 个在 columns [4,5,6,7,8]），返回 Row1 columns [4,5,6,7,8]
- 请求 N=10 连座：返回 Row2 columns [0,1,2,3,4,5,6,7,8,9]

## 并发安全设计

`SeatReservationManager` 通过以下机制保证并发安全：

1. **全局互斥锁**：所有修改座位状态的操作（预留、取消、确认）均通过 `threading.Lock` 保护，同一时刻只有一个线程能进入临界区。
2. **检查即操作（Check-then-Act 原子化）**：在持锁状态下完成"检查座位状态 → 修改座位状态"的完整流程，避免竞态条件。
3. **超时检测在持锁时执行**：判断预留是否超时和释放过期预留均在持锁时进行，确保不会出现超时判定和状态修改的竞争。

## 使用示例

### 基本预留与确认

```python
from solocoder_py.seat import SeatReservationManager, SeatAlreadyReservedError

manager = SeatReservationManager(rows=5, columns=10)

try:
    manager.reserve_seat(0, 0, "user-123")
    print("预留成功")
except SeatAlreadyReservedError:
    print("座位已被预留")

manager.confirm_occupancy(0, 0, "user-123")
print("确认占用成功")
```

### 连座预留

```python
from solocoder_py.seat import ConsecutiveSeatsNotFoundError

try:
    seats = manager.reserve_consecutive_seats(4, "user-456")
    print(f"成功预留连座: {[str(s) for s in seats]}")
except ConsecutiveSeatsNotFoundError:
    print("没有足够的连续座位")

# 指定行
seats = manager.reserve_consecutive_seats_in_row(3, "user-789", row=2)
```

### 取消预留

```python
from solocoder_py.seat import SeatReservationExpiredError, SeatReservationMismatchError

try:
    manager.cancel_reservation(0, 0, "user-123")
except SeatReservationExpiredError:
    print("预留已超时，座位已自动释放")
except SeatReservationMismatchError:
    print("该座位不是由此用户预留")
```

### 查询可用座位

```python
available = manager.list_available_seats()
print(f"共有 {len(available)} 个可用座位")

seat = manager.get_seat(0, 0)
if seat:
    print(f"座位状态: {seat.state}")
```

### 使用 ManualClock 进行超时测试

```python
from solocoder_py.seat import ManualClock, SeatReservationExpiredError

clock = ManualClock()
manager = SeatReservationManager(
    rows=5, columns=10,
    default_reservation_timeout=60.0,
    clock=clock,
)

manager.reserve_seat(0, 0, "user-1")

clock.advance(59.0)
manager.confirm_occupancy(0, 0, "user-1")  # 成功，未超时

manager.reserve_seat(0, 1, "user-2")
clock.advance(61.0)
try:
    manager.confirm_occupancy(0, 1, "user-2")
except SeatReservationExpiredError:
    print("预留已超时释放")
```

### 管理操作

```python
# 强制释放座位（用于管理员操作）
manager.force_release_seat(0, 0)

# 统计可用座位数
print(f"可用座位: {manager.count_available()}")
print(f"第 2 行可用: {manager.count_available_in_row(2)}")

# 重置所有座位
manager.clear()
```

## 运行测试

```bash
pytest tests/seat/ -v
```
