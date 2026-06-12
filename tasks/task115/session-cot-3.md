toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\auditlog\validator.py
          
现在一次性修复所有 3 个问题：





        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\auditlog\validator.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/auditlog/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
## 3 个验证逻辑缺陷全部修复完成，`poetry run pytest tests/auditlog/ -q` **44 passed**。

### 问题 1：verify_chain 中 expected_hash 区分失败类型

**修复位置**：[validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/auditlog/validator.py#L89-L128)

引入 `failure_type` 变量追踪每种失败原因，然后通过条件判断决定 `expected_hash`：

```python
failure_type = ""  # "previous_hash" | "content_hash" | "anchor_hash" | "chain_broken"

if failure_type == "anchor_hash":
    result_expected_hash = anchor_hashes[entry.index]  # 仅锚定不匹配用 anchor
else:
    result_expected_hash = expected_hash               # 其余用内容派生哈希
```

**效果**：
- `previous_hash` 不匹配：`expected_hash` = 内容重算哈希（与 actual 对比反映内容完整性）
- 内容哈希不一致：同上
- **锚定哈希不匹配**：`expected_hash` = `anchor_hashes[entry.index]`（反映系统性覆写）
- 链式断裂：内容派生哈希

### 问题 2：anchor_hashes 长度前置校验

**修复位置**：[validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/auditlog/validator.py#L53-L60)

在条目索引一致性校验之后、开始验证之前增加校验：

```python
if anchor_hashes is not None:
    max_entry_index = end - 1
    if max_entry_index >= len(anchor_hashes):
        raise InvalidIndexError(
            f"anchor_hashes length {len(anchor_hashes)} is insufficient "
            f"to cover entry index {max_entry_index}. "
            f"Need at least {max_entry_index + 1} anchor hashes."
        )
```

同时删除了锚定检测分支中的 `entry.index < len(anchor_hashes)` 静默跳过条件，因为现在长度已被前置保证，不需要也不能再跳过。

### 问题 3：verify_entry 锚定哈希语义范围

**修复位置**：[validator.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/auditlog/validator.py#L182-L207)

修改前两个失败分支中的三元表达式：

| 分支 | 修改前 | 修改后 |
|---|---|---|
| previous_hash 不匹配 | `expected_hash if anchor_hash is None else anchor_hash` | `expected_hash` |
| 内容哈希不匹配 | `expected_hash if anchor_hash is None else anchor_hash` | `expected_hash` |
| 锚定哈希不匹配（新增独立分支） | — | `anchor_hash` |

现在只有真正的锚定不匹配（内容+内部哈希自洽但与权威值不一致）才会使用 `anchor_hash` 作为 `expected_hash`。