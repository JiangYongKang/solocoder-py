toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\service.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\crypto_hash\test_crypto_hash.py
          
两个问题都很准确。让我逐一分析并修复：

1. **时序安全比较**：`len(a) != len(b)` 时立即返回，泄露了长度信息
2. **bcrypt 限幅**：算法内部静默限幅 `min(max(1, iterations), 31)`，但存储的是未限幅的原始值
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          
changes: undefined
          
现在修复第二个问题——bcrypt 静默限幅。先在 `HashAlgorithm` 基类添加 `max_iterations` 属性，然后修改 `BcryptSimulatedAlgorithm` 和 `CryptoHashService`。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          
changes: undefined
          
现在修改 `CryptoHashService`，在 `hash()` 中限幅迭代次数后再存储，在 `verify()` 中也做限幅以确保与存储行为一致。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\service.py
          
changes: undefined
          
同样在 `verify()` 中对 `stored_hash.iterations` 做限幅，确保旧存储的未限幅值在验算时与实际执行轮数一致。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\service.py
          
changes: undefined
          
现在需要更新测试——`test_custom_parameters_in_hash` 中 `iterations=100` 使用默认的 BCRYPT_V3 会被限幅到 31。
        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\crypto_hash\test_crypto_hash.py
          
changes: undefined
          
现在运行测试验证修复。
        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/crypto_hash/ -q undefined
          
全部 67 个测试通过。以下是两个修复的总结：

---

### 修复 1：时序安全比较——消除长度泄露

**问题**：[constant_time_compare](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/crypto_hash/algorithms.py#L76-L82) 在 `len(a) != len(b)` 时立即 `return False`，攻击者可通过测量响应时间推断期望哈希的长度。

**修复**：不再提前返回。用 `len(a) ^ len(b)` 将长度差异编入累积结果，然后始终遍历 `max(len(a), len(b))` 个字节。较短的一方用 0 填充参与异或。无论长度是否匹配，比较耗时始终与较长输入的长度成正比。

```python
def constant_time_compare(a: bytes, b: bytes) -> bool:
    result = len(a) ^ len(b)
    for i in range(max(len(a), len(b))):
        val_a = a[i] if i < len(a) else 0
        val_b = b[i] if i < len(b) else 0
        result |= val_a ^ val_b
    return result == 0
```

### 修复 2：bcrypt 限幅一致性——存储值与实际执行轮数对齐

**问题**：[BcryptSimulatedAlgorithm.hash()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/crypto_hash/algorithms.py#L50-L56) 内部 `min(max(1, iterations), 31)` 将迭代限幅到 31，但 [CryptoHashService.hash()](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/crypto_hash/service.py#L91-L101) 存储的是未限幅的原始值，导致 `check_rehash_needed()` 对从未达到过的安全级别误判。

**修复**：
- `HashAlgorithm` 基类新增 `max_iterations` 属性（默认 `2**31`，即无实际限制）
- `BcryptSimulatedAlgorithm` 声明 `max_iterations = 31`
- 移除算法内部的 `min(..., 31)` 限幅
- 服务层在 `hash()` 中调用算法前先 `min(effective_iterations, algorithm.max_iterations)` 限幅，并将限幅后的值存入 `HashResult`
- 服务层在 `verify()` 中同样对 `stored_hash.iterations` 做限幅后传给算法，保证旧存储的未限幅值也能正确还原出相同的哈希