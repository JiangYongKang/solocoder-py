让我先阅读当前代码，然后逐一修复问题。
        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\porter.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
首先，我需要验证哪些被删除的词条是 Porter 规则无法正确还原的。让我运行一个快速测试：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "
from solocoder_py.stemmer.porter import PorterStemmer, StemmerConfig
stemmer = PorterStemmer(StemmerConfig(preserve_case=False))

previously_deleted = {
    'runs': 'run', 'running': 'run',
    'mouse': 'mouse', 'man': 'man', 'woman': 'woman', 'child': 'child',
    'tooth': 'tooth', 'foot': 'foot', 'goose': 'goose',
    'be': 'be', 'being': 'be',
    'have': 'have', 'having': 'have',
    'do': 'do', 'doing': 'do',
    'go': 'go', 'goes': 'go', 'gone': 'go', 'going': 'go',
    'say': 'say', 'says': 'say', 'saying': 'say',
    'get': 'get', 'gets': 'get', 'gotten': 'get', 'getting': 'get',
    'make': 'make', 'makes': 'make', 'making': 'make',
    'know': 'know', 'knows': 'know', 'known': 'know', 'knowing': 'know',
    'think': 'think', 'thinks': 'think', 'thinking': 'think',
    'see': 'see', 'sees': 'see', 'seen': 'see', 'seeing': 'see',
    'come': 'come', 'comes': 'come', 'coming': 'come',
    'take': 'take', 'taken': 'take', 'taking': 'take',
}

print('Words Porter CANNOT correctly handle (need exception dict):')
for word, expected in sorted(previously_deleted.items()):
    result = stemmer.stem(word)
    if result != expected:
        print(f'  {word} -> porter:{result} != expected:{expected}')

print()
print('Words Porter CAN correctly handle (no exception needed):')
for word, expected in sorted(previously_deleted.items()):
    result = stemmer.stem(word)
    if result == expected:
        print(f'  {word} -> porter:{result} == expected:{expected}')
"
 undefined
          
让我改用一个脚本文件来运行：
        
            
toolName: Write
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_check_exceptions.py
          
changes: undefined
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python _check_exceptions.py undefined
          
现在我清楚了哪些词需要恢复。Porter 无法正确处理的有 11 个词：`goes`、`gone`、`goose`、`gotten`、`known`、`mouse`、`say`、`saying`、`says`、`seen`、`taken`。

让我清理临时文件并开始修复：
        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\_check_exceptions.py
          
现在修复两个问题。先恢复被误删的不规则词条，然后重构配置共享机制：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
现在修复问题 2：让 Stemmer 和内部 _porter 共享同一个配置对象。关键是：Stemmer 自己负责大小写处理，所以需要把用户配置的 `preserve_case` 单独保存在 Stemmer 上，然后强制共享配置对象的 `preserve_case=False`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
现在移除 `_sync_porter_config` 方法，因为已经不需要了——共享同一个对象，修改自动传播：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
现在更新 `stem` 方法，移除 `_sync_porter_config` 调用，并使用 `self._preserve_case` 替代 `self.config.preserve_case`：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
最后更新 `aggressiveness` setter，移除 `_sync_porter_config` 调用（现在共享同一对象，不需要同步）：
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
现在让我运行测试验证：
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/stemmer/ -v undefined
          
所有 70 个测试全部通过。让我再快速验证一下 `gotten` 等被恢复的词确实能被正确提取：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "from solocoder_py.stemmer import Stemmer; s=Stemmer(); print('gotten:', s.stem('gotten')); print('gone:', s.stem('gone')); print('goes:', s.stem('goes')); print('known:', s.stem('known')); print('seen:', s.stem('seen')); print('taken:', s.stem('taken')); print('says:', s.stem('says')); print('mouse:', s.stem('mouse'))" undefined
          
所有被恢复的不规则词都能正确提取了。让我也验证配置共享是否生效：
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "from solocoder_py.stemmer import Stemmer, StemmerConfig, AggressivenessLevel; s=Stemmer(); print('shared:', s.config is s._porter.config); s.config.min_stem_length=5; print('sync min_stem_length:', s.config.min_stem_length == s._porter.config.min_stem_length); s.config.level=AggressivenessLevel.CONSERVATIVE; print('sync level:', s._porter.config.level)" undefined
          
配置对象完全共享（`is` 检查为 True），任何字段修改都会自动传播。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
两个问题均已修复，70 个测试全部通过。以下是修复总结：

## 修复内容

### 1. 恢复被误删的不规则词条

通过实际运行 Porter 算法验证了所有被删除的词条，恢复了 **11 个** Porter 规则无法正确处理的不规则变化词：

| 词条 | Porter 错误输出 | 正确词干 |
|------|----------------|---------|
| `gotten` | `gotten` | `get` |
| `gone` | `gone` | `go` |
| `goes` | `goe` | `go` |
| `goose` | `goos` | `goose` |
| `mouse` | `mous` | `mouse` |
| `known` | `known` | `know` |
| `seen` | `seen` | `see` |
| `taken` | `taken` | `take` |
| `say` | `sai` | `say` |
| `says` | `sai` | `say` |
| `saying` | `sai` | `say` |

保留了能被 Porter 正确处理的词条（如 `running`→`run`、`being`→`be`、`coming`→`come` 等 24 个），它们走规则路径时会受到最小词干长度保护。

修改位置：[stemmer.py#L15-L58](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stemmer/stemmer.py#L15-L58)

### 2. 配置对象共享，消除手动同步

重构了 `Stemmer` 与内部 `PorterStemmer` 的配置关系：

- **之前**：维护两份独立配置（`self.config` 和 `self._porter_config`），通过 `_sync_porter_config()` 逐字段同步，新增字段时容易遗漏
- **现在**：`Stemmer` 和 `_porter` 共享同一个 `StemmerConfig` 对象（`s.config is s._porter.config` → `True`）。修改任意字段自动传播，未来新增字段无需改动同步逻辑
- `preserve_case` 的处理：用户设置保存在 `self._preserve_case` 中，共享配置对象的 `preserve_case` 固定为 `False`（大小写统一由 `Stemmer.stem()` 处理，`PorterStemmer` 不做大小写转换）
- 移除了 `_sync_porter_config()` 方法和所有对它的调用

修改位置：[stemmer.py#L65-L74](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stemmer/stemmer.py#L65-L74)