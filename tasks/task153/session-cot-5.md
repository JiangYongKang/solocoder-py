让我先阅读当前代码，然后修复配置污染问题。

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
现在我理解了问题。第 73 行 `self.config.preserve_case = False` 直接修改了用户传入的 config 对象，造成副作用污染。需要：
1. 创建用户传入 config 的深拷贝
2. 在副本上设置 `preserve_case = False`
3. 用副本传给 `PorterStemmer`
4. `self.config` 指向副本（这样用户后续修改 `stemmer.config.level` 等字段也会同步到 PorterStemmer）
5. 用 `self._preserve_case` 保存用户原始偏好

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
changes: undefined
          
现在让我检查 `stem` 方法中是否使用了 `self._preserve_case`（应该已经使用了），并确认所有引用正确：

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\stemmer\stemmer.py
          
`stem` 方法已经正确使用了 `self._preserve_case`（第 105 行和第 118 行），配置也在内部共享。现在运行测试：


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/stemmer/ -v undefined
          
所有 70 个测试通过。让我再验证一下外部 config 确实没有被污染：


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; python -c "from solocoder_py.stemmer import Stemmer, StemmerConfig; cfg = StemmerConfig(preserve_case=True); print('before:', cfg.preserve_case); s = Stemmer(config=cfg); print('after:', cfg.preserve_case); print('stemmer internal preserve_case:', s._preserve_case); print('shared config with porter:', s.config is s._porter.config)" undefined
          
验证结果完美：
- `before: True` / `after: True`：用户传入的 config 对象没有被污染
- `stemmer internal preserve_case: True`：用户原始偏好被正确保存
- `shared config with porter: True`：Stemmer 和内部 PorterStemmer 仍然共享同一个配置副本




        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
配置污染问题已修复，70 个测试全部通过。

## 修复内容

修改了 [Stemmer.__init__](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/stemmer/stemmer.py#L66-L83) 中的初始化逻辑：

### 修改前（有污染问题）：
```python
self.config = config or StemmerConfig()
self._preserve_case = self.config.preserve_case
self.config.preserve_case = False  # ← 直接修改用户传入的 config，污染外部对象
self._porter = PorterStemmer(self.config)
```

### 修改后（无污染）：
```python
user_config = config or StemmerConfig()
self._preserve_case = user_config.preserve_case   # 先保存用户原始偏好
self.config = copy.deepcopy(user_config)              # 深拷贝，不触碰用户对象
self.config.preserve_case = False                      # 修改副本
self._porter = PorterStemmer(self.config)       # 副本同时传给 PorterStemmer，保持共享
```

### 验证结果：
- **外部 config 不受影响：`cfg.preserve_case` 在创建 Stemmer 前后均为 `True`
- **内部配置共享：`s.config is s._porter.config` → `True`（仍共享同一副本，修改自动同步
- **大小写处理不变**：`stem()` 方法使用 `self._preserve_case` 获取用户原始偏好