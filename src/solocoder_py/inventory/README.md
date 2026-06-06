# 多仓库存预占引擎

## 模块功能

本模块提供一个基于内存数据结构的多仓库库存预占引擎，核心能力包括：

- **多仓库库存管理**：维护多个仓库，每个仓库下有多个 SKU，每个 SKU 维护总库存量与已预占量，自动计算可用库存量
- **库存预占（原子性）**：支持单个预占请求涉及多个 SKU 或多个仓库，保证全部成功或全部回滚
- **库存释放**：支持按预占记录 ID 全额或部分释放预占库存
- **跨仓拆分配额**：当单一仓库库存不足时，自动将预占请求拆分到多个仓库，优先从库存最多的仓库预占
- **TTL 过期回收**：预占记录支持设置存活时间，超时未确认的预占自动释放（惰性检查）
- **超卖防护与并发安全**：严格校验库存充足性，使用线程锁保证并发操作下的数据一致性

## 核心类职责

### 数据模型（models.py）

| 类名 | 职责 |
|------|------|
| `SkuStock` | 单个 SKU 在某仓库的库存数据，维护 `total`（总库存）与 `reserved`（已预占），提供 `available`（可用库存）属性，以及 `reserve` / `release` / `add_stock` / `remove_stock` 等操作 |
| `Warehouse` | 仓库实体，包含 ID、名称，以及 SKU 库存集合；提供 SKU 的获取与创建接口 |
| `ReservationItem` | 预占记录中的明细项，记录在哪个仓库、哪个 SKU、预占了多少数量，以及已释放数量 |
| `Reservation` | 预占记录，包含 ID、明细项列表、创建时间、过期时间、状态；提供 `is_active` / `is_expired` 等判断属性 |
| `ReservationStatus` | 预占状态枚举：`ACTIVE`（有效）、`RELEASED`（已释放）、`EXPIRED`（已过期）、`CONFIRMED`（已确认扣减） |

异常类：
- `InventoryError`：库存模块基类异常
- `InsufficientStockError`：库存不足
- `ReservationNotFoundError`：预占记录不存在
- `InvalidQuantityError`：数量参数非法（非正数等）
- `WarehouseNotFoundError`：仓库不存在

### 引擎（engine.py）

| 类名 | 职责 |
|------|------|
| `ReserveRequestItem` | 预占请求项：指定 SKU、数量，以及可选的优先仓库列表 |
| `InventoryEngine` | 库存预占引擎：核心业务入口，管理仓库集合、预占记录集合，提供预占、释放、确认、库存查询等操作，内部使用 `threading.RLock` 保证线程安全 |

## 预占生命周期

```
                    预占成功
              ┌───────────────────┐
              │     ACTIVE        │
              └───┬──────┬────┬───┘
                  │      │    │
             主动释放   TTL过期  主动确认扣减
                  │      │    │
                  ▼      ▼    ▼
            ┌─────────┐ ┌─────────┐ ┌─────────────┐
            │RELEASED │ │ EXPIRED │ │  CONFIRMED  │
            └─────────┘ └─────────┘ └─────────────┘
```

- **ACTIVE → RELEASED**：调用 `release()` 全额释放，或多次部分释放后预占剩余量归零
- **ACTIVE → EXPIRED**：预占记录设置了 TTL，且超过 `expires_at`，在下一次引擎操作时惰性回收，已预占库存自动恢复为可用
- **ACTIVE → CONFIRMED**：调用 `confirm()` 将预占库存正式扣减出库，总库存与预占库存同时减少对应数量
- `RELEASED`、`EXPIRED`、`CONFIRMED` 均为终态，不可再执行释放或确认操作
- 部分释放与 TTL 过期可以交叉发生：例如先部分释放 10 件，剩余 20 件随后因 TTL 过期被惰性回收

## 跨仓拆分策略

当预占请求指定的 SKU 数量超过单一仓库的可用库存时，引擎自动将请求拆分到多个仓库：

1. **仓库候选集**：如果请求中指定了 `preferred_warehouse_ids`，则仅在这些仓库中分配；否则在所有仓库中分配。若候选仓库中可用库存总量不足，直接抛出 `InsufficientStockError`，不执行任何预占
2. **排序规则**：候选仓库按该 SKU 的可用库存量从大到小排序（优先从库存最多的仓库预占），以最小化拆单仓库数量
3. **分配过程**：依次遍历排序后的仓库，尽可能多地取货（取当前仓库可用量与剩余需求量的较小值），直到需求被满足
4. **总量校验**：分配前先校验所有候选仓库的可用库存总量是否足够；不足则立即抛错，不执行任何预占
5. **原子性**：预占请求涉及多个 SKU 时，逐个处理 SKU；任一 SKU 分配失败，全部已执行的预占操作按逆序回滚，保证整个请求全部成功或全部失败

示例：

```
需要预占 SKU-001 共 100 件：
  仓库 A：可用 60 件 → 取 60 件（剩余需求 40）
  仓库 B：可用 50 件 → 取 40 件（剩余需求 0，完成）
  仓库 C：可用 30 件 → 不涉及

结果：从 A 预占 60 件，从 B 预占 40 件。
```

## 使用示例

```python
from datetime import timedelta
from solocoder_py.inventory import (
    InventoryEngine,
    ReserveRequestItem,
)

engine = InventoryEngine()

# 1. 创建仓库并入库
engine.add_warehouse("wh-a", "华东仓")
engine.add_warehouse("wh-b", "华南仓")
engine.add_stock("wh-a", "SKU-001", 60)
engine.add_stock("wh-b", "SKU-001", 50)
engine.add_stock("wh-a", "SKU-002", 30)

# 2. 跨仓预占（自动拆分），设置 10 分钟 TTL
reservation = engine.reserve([
    ReserveRequestItem(sku_id="SKU-001", quantity=100),
    ReserveRequestItem(sku_id="SKU-002", quantity=10),
], ttl=timedelta(minutes=10))
print(f"预占 ID: {reservation.id}")
for item in reservation.items:
    print(f"  仓库 {item.warehouse_id} / SKU {item.sku_id}: {item.quantity} 件")

# 3. 查询库存
sku_a = engine.get_stock("wh-a", "SKU-001")
print(f"华东仓 SKU-001: 可用={sku_a.available}, 已预占={sku_a.reserved}, 总库存={sku_a.total}")

# 4. 部分释放：释放 20 件，剩余预占量继续保留
engine.release(reservation.id, quantity=20)

# 5. 确认扣减：剩余预占量正式从总库存中出库
engine.confirm(reservation.id)

# 6. 或：全额释放，所有预占库存恢复为可用
# engine.release(reservation.id)
```
