这些问题我在上一轮对话中已经全部修复了。让我快速验证一下当前代码状态和测试结果：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; poetry run pytest tests/diff/ -v undefined
          
**68 passed in 0.13s** ✅

所有三个问题在上一轮对话中已经全部修复完成，68 个测试全部通过。让我快速验证一下三个修复点的实际效果：

        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_verify_fixes.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py; python _verify_fixes.py undefined
          
所有修复都已经生效！让我清理临时文件：




        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_verify_fixes.py
          
## 修复状态确认 ✅

所有三个问题均已修复，**`poetry run pytest tests/diff/ -v` 共 68 个测试全部通过**。

### 修复验证结果

| 问题 | 修复状态 | 验证效果 |
|------|----------|----------|
| **1. 组合粒度支持** | ✅ 已修复 | 支持 `(LINE, WORD)` 和 `(LINE, CHAR)` 两种组合，修改行的 `sub_operations` 字段包含细粒度差异操作 |
| **2. 部分 token 上下文** | ✅ 已修复 | EQUAL 操作含 15 个 token 时，上下文行数=3 可以正确截取最后 3 个 token 作为前置上下文，不会整段丢弃 |
| **3. hunk header 索引统一** | ✅ 已修复 | LINE/WORD/CHAR 三种粒度均输出 1-based 起始位置（`@@ -1,2 +1,2 @@`） |

### 核心修改文件

- [models.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/models.py)：添加 `sub_operations` 字段支持组合粒度
- [differ.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/differ.py)：实现 `_refine_modified_lines()` 组合粒度细化逻辑
- [unified_diff.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/unified_diff.py)：实现部分 token 截取和统一 1-based 索引
- [README.md](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/diff/README.md)：完整文档说明

### 测试覆盖

原有 52 个测试 + 新增 16 个测试 = **68 个测试全部通过**，覆盖组合粒度、部分上下文、统一索引及异常处理等场景。