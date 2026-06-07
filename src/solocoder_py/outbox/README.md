# Outbox 事务发件箱

## 模块概述

本模块实现了事务发件箱（Transactional Outbox）模式，用于确保业务操作与消息投递的原子性。
通过将业务记录与待投递消息在同一事务中写入内存数据结构，保证两者要么同时成功，要么同时回滚，
避免出现"业务成功但消息丢失"或"消息投递但业务未完成"的不一致问题。

## 核心功能

1. **原子写入**：业务记录与消息在同一操作中创建，保证一致性
2. **消息状态机**：严格的状态流转校验，防止非法跳转
3. **投递确认与重试**：失败消息支持自动重试，超过上限进入死信
4. **补偿扫描**：后台定时扫描待投递和可重试消息，恢复未完成投递
5. **死信处理**：超过最大重试次数后进入死信队列，便于人工排查
6. **并发安全**：多投递器并发领取消息时保证同一条消息不会被重复领取

## 核心类职责

### BusinessRecord
业务记录模型，表示一次业务操作的持久化记录。

- `id`：业务记录唯一标识
- `business_type`：业务类型（如 order_created、payment_completed 等）
- `payload`：业务数据负载（字典格式）
- `created_at`：创建时间

### OutboxMessage
发件箱消息模型，表示一条待投递消息。

- `id`：消息唯一标识
- `business_record_id`：关联的业务记录 ID
- `message_type`：消息类型
- `payload`：消息负载
- `state`：当前状态（由状态机管理）
- `retry_count`：已重试次数
- `max_retries`：最大重试次数
- `last_error`：最近一次失败原因
- `next_retry_at`：下次可重试时间
- `claimed_by`：当前领取的投递器 ID
- `claimed_at`：领取时间

关键方法：
- `mark_delivering(worker_id)`：标记为投递中，记录领取信息
- `mark_confirmed()`：标记为已确认
- `mark_failed(error, retry_delay_seconds)`：标记为失败，记录错误并计算重试时间
- `mark_dead_letter()`：标记为死信
- `release_claim()`：释放领取标记

### OutboxStateMachine
消息状态机，管理消息状态的合法流转。

状态枚举 `OutboxMessageState`：

| 状态 | 说明 |
|------|------|
| PENDING（待投递） | 消息已写入，等待投递器领取 |
| DELIVERING（投递中） | 已被投递器领取，正在投递 |
| CONFIRMED（已确认） | 投递成功确认 |
| FAILED（投递失败） | 本次投递失败，等待重试或进入死信 |
| DEAD_LETTER（死信） | 超过最大重试次数，不再自动投递 |

### OutboxRepository
发件箱仓库，提供所有核心操作接口。

核心方法：

**写入操作：
- `write_with_message(...)`：原子写入一条业务记录和一条消息
- `write_with_messages(...)`：原子写入一条业务记录和多条消息
- `atomic_write_with_callback(...)`：原子写入并支持在写入消息前执行自定义回调

**领取与投递：**
- `claim_message(message_id, worker_id)`：指定领取某条消息
- `claim_next_messages(worker_id, batch_size)`：批量领取下一批可投递消息
- `confirm_message(message_id)`：确认投递成功
- `fail_message(message_id, error, retry_delay_seconds)`：标记投递失败
- `force_to_dead_letter(message_id)`：强制将消息移入死信

**扫描查询：
- `scan_pending_messages(limit)`：扫描待投递消息（按创建时间排序）
- `scan_retryable_messages(limit, now)`：扫描可重试的失败消息（按重试时间排序）
- `scan_due_messages(limit, now)`：扫描所有到期可投递消息（合并 PENDING + 可重试 FAILED）
- `get_dead_letters(limit)`：查询死信消息

**其他：
- `get_message(message_id)`：获取单条消息
- `get_business_record(record_id)`：获取业务记录
- `get_messages_by_business(record_id)`：获取某业务记录关联的所有消息
- `count_by_state()`：按状态统计消息数量
- `clear()`：清空所有数据

## 消息状态机

状态流转图：

```
PENDING ──→ DELIVERING ──→ CONFIRMED（终态）
              │
              └──→ FAILED ──→ DELIVERING（重试）
                    │
                    └──→ DEAD_LETTER（终态）
```

合法状态转移矩阵：

| 当前状态 | 可转移至 |
|--------|---------|
| PENDING | DELIVERING |
| DELIVERING | CONFIRMED, FAILED |
| CONFIRMED | （终态） |
| FAILED | DELIVERING, DEAD_LETTER |
| DEAD_LETTER | （终态） |

非法状态转移将抛出 `InvalidStateTransitionError`。

## 补偿扫描流程

后台投递器通过 `scan_due_messages` 或 `claim_next_messages` 定期扫描可投递消息：

1. 扫描所有状态为 PENDING 的消息
2. 扫描所有状态为 FAILED 且满足以下条件的消息：
   - 重试次数未达上限（`retry_count < max_retries`）
   - 已达到下次重试时间（`next_retry_at <= now` 或未设置）
3. PENDING 按创建时间升序，FAILED 按重试时间升序
4. 投递器领取（通过 `claim_next_messages` 原子领取消息（状态变为 DELIVERING，记录 worker_id
5. 投递成功：调用 `confirm_message` 进入 CONFIRMED
6. 投递失败：调用 `fail_message` 记录错误
   - 若未达重试上限：计算下次重试时间，回到 FAILED
   - 若超过重试上限：自动进入 DEAD_LETTER

## 并发领取防重

通过 `threading.RLock` 保证所有写操作的原子性：

- `claim_next_messages` 在锁内遍历候选列表 + 状态校验 + 状态变更
- 已被领取（DELIVERING 且非当前 worker 的消息跳过
- 保证同一条消息只会被一个投递器成功领取

## 异常类型

- `AtomicWriteError`：原子写入失败，已自动回滚
- `InvalidStateTransitionError`：非法状态流转
- `MessageNotFoundError`：消息不存在
- `MessageAlreadyClaimedError`：消息已被其他投递器领取

## 使用示例

```python
from solocoder_py.outbox import OutboxRepository

repo = OutboxRepository(default_max_retries=3, default_retry_delay_seconds=5)

record, message = repo.write_with_message(
    business_type="order_created",
    message_type="send_order_email",
    business_payload={"order_id": "ORD-001", "amount": 99.9},
    message_payload={"order_id": "ORD-001", "email": "user@test.com"},
)

claimed = repo.claim_next_messages("worker-1", batch_size=10)
for msg in claimed:
    try:
        send_email(msg.payload)
        repo.confirm_message(msg.id)
    except Exception as e:
        repo.fail_message(msg.id, str(e))
```
