# Treiber Stack - 无锁并发栈

## 模块功能

Treiber Stack 是一个遵循经典 Treiber 无锁算法的并发栈，提供线程安全的压入（push）和弹出（pop）操作。该实现在 CPython 环境下利用 GIL 的引用赋值原子性、不可变对象以及 CAS 自旋重试循环实现，不使用任何显式互斥锁（`threading.Lock`），适用于高并发场景下需要