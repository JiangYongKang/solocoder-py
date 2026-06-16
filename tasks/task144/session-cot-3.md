我来修复这两个问题。先读取当前文件：



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
现在同时修复两个问题：










        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
修复问题2：冲突时不计算和存储无意义的 diff：












        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\doc_versioning\store.py
          
changes: undefined
          
现在运行测试验证所有修复：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/doc_versioning/ -q undefined
          
全部 48 个测试通过！





        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
## 修复总结

完成了 2 个遗留问题的修复，48 个测试全部通过。

### 问题 1：静态类型不一致

**文件**：[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/store.py#L121-L124)

在 `get_version_content` 方法中返回 `ver.content` 前添加了断言：

```python
def get_version_content(self, document_id: str, version: int) -> str:
    ver = self.get_version(document_id, version)
    assert ver.content is not None
    return ver.content
```

虽然运行路径保证 `get_version()` 返回时 `content` 已被赋值，但 `DocumentVersion.content` 字段类型声明为 `Optional[str]`，静态类型检查器无法推断该运行时不变量。添加 `assert` 后：
- 静态类型检查器（mypy、pyright 等）能在断言后推断类型收窄为 `str`
- 运行时如果出现预期外的状态（bug 引入），会尽早失败而非传播 `None` 导致更隐蔽的错误

### 问题 2：冲突场景下的无意义 Diff 存储

**文件**：[store.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/doc_versioning/store.py#L200-L243)

修改 `_commit_with_merge` 方法，根据是否有冲突分支处理 diff：

- **无冲突（CLEAN）**：正常计算 `latest_content → merged_text` 的 Diff，`content = None`，版本通过 Diff 链重建
- **有冲突（CONFLICTED）**：`diff = None`，同时将带冲突标记的完整文本存储在 `content` 中

这样做的好处：
1. **消除存储浪费**：冲突版本的 content 已被全量存储，Diff 完全不参与重建，没有存储价值
2. **消除数据误导**：`latest_content → 带冲突标记文本` 的 Diff 语义上不是一个合理的"编辑差异"，存储它可能让后续工具（如审计、可视化）产生误解
3. **架构一致性**：`_reconstruct_content` 中已有处理 `ver.diff is None` 的逻辑（直接返回 `ver.content`），冲突版本自然走该分支