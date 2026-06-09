toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
重写整个测试，让扫描端强制遍历全部交易（去掉 early break），并以精确值和严格的倍率对比来断言：
















        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: /Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py
          
changes: undefined
          
现在运行测试验证：

















        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/test_ledger.py::TestEntryIndex -v 2>&1 undefined
          
全部 TestEntryIndex 4 个测试通过，再跑全量：


















        
            
toolName: run_command
            
status: success
          
command: cd /Users/vincent/GoletaLab/solocoder-py && poetry run pytest tests/ledger/ -q 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
全部 72 个测试通过。以下是本轮修复的详细总结：

---

## 修复内容汇总

### 测试：`test_indexed_lookup_constant_ops_vs_scan_linear_ops`（[test_ledger.py#L797-L877](file:///Users/vincent/GoletaLab/solocoder-py/tests/ledger/test_ledger.py#L797-L877)）

**问题 1：扫描端 early break 导致复杂度不严谨**

原实现用了 `if any(...): break`，加上 Python dict 按插入顺序保持的特性，每条分录找到所属交易后立即退出内层循环。由于分录与其所属交易的创建顺序高度相关，匹配几乎都在循环早期命中，扫描次数近似 O(M²) 而非 O(M×N)，与提示词要求的"严格体现线性扫描最坏情况复杂度"不符。

**修复**：去掉 `break`，强制每条分录完整遍历所有交易，将每次比较都计入操作次数：

```python
# 修复前（有 early break，近似 O(M²)）
for entry in entry_list:
    for txn_id, txn in txn_items:
        counter += 1
        if any(e.entry_id == entry.entry_id for e in txn.entries):
            break

# 修复后（强制遍历全部交易，严格 O(M×N) 最坏情况）
for entry in entry_list:
    for txn_id, txn in txn_items:
        counter += 1
        _ = any(e.entry_id == entry.entry_id for e in txn.entries)
```

**问题 2：断言系数 0.8 过于宽松**

原断言 `large_scan_ops >= small_scan_ops * (ratio) * 0.8` 只要求大数据量扫描次数达到理论值的 80%，边界过于模糊，无法严格区分"确有 O(N) 增长特征"与"恰好统计波动"。

**修复**：以**精确值断言**取代宽松阈值，同时验证增长倍率的严格分离：

| 维度 | 小规模（10 对转账） | 大规模（500 对转账） | 理论增长倍率 |
|------|---------------------|---------------------|-------------|
| 分录数 M | 20 | 1000 | ×50 |
| 交易数 N | 20 | 1000 | ×50 |
| 索引查找操作次数 | 2 × M = 40 | 2 × M = 2000 | ×50（仅与 M 线性相关） |
| 线性扫描操作次数 | M × N = 400 | M × N = 1,000,000 | ×2500（与 M×N 成比例） |

具体断言层级：

```python
# 第 1 层：绝对精确值验证
assert small_indexed_ops == 2 * SMALL_ENTRIES           # 40 == 40
assert large_indexed_ops == 2 * LARGE_ENTRIES           # 2000 == 2000
assert small_scan_ops == SMALL_ENTRIES * SMALL_TXNS     # 400 == 400
assert large_scan_ops == LARGE_ENTRIES * LARGE_TXNS     # 1000000 == 1000000

# 第 2 层：增长倍率与理论复杂度一致
assert indexed_scale == entries_scale                   # ×50 == ×50（仅随分录数增长，O(M)）
assert scan_scale == entries_scale * txns_scale         # ×2500 == ×50 × ×50（随 M×N 增长，O(M×N)）

# 第 3 层：扫描增长倍率显著大于索引增长倍率（差值为交易数增长倍数 ×50）
assert scan_scale > indexed_scale * (LARGE_TXNS / SMALL_TXNS) * 0.99  # ×2500 > ×50 × ×50 × 99%
```

三层断言形成递进：**精确值匹配 → 增长倍率符合各自复杂度阶 → 两者增长倍率间存在数量级差距**，清晰证明 O(1) 索引与 O(N) 扫描的真实差异。

### 最终验证

```bash
$ poetry run pytest tests/ledger/ -q
........................................................................ [100%]
72 passed in 0.94s
```