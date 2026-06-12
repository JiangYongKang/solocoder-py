让我先检查当前代码的状态，了解存在的问题。
        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\service.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\models.py
          
现在我理解了当前代码的状态。让我分析问题：

**问题 1**：时序安全比较函数 - 当前实现已经修复了，看起来没有提前返回。让我再仔细看看。

**问题 2**：BcryptSimulatedAlgorithm 的防御性限幅 - 当前代码中只做了 `max(1, iterations)`，没有 `min` 限幅到 `max_iterations=31`。需要加回来。

**问题 3**：`check_rehash_needed` 中的迭代次数比较 - 当前直接比较 `stored_hash.iterations != self.default_iterations`，但如果用户配置了 50，而算法上限是 31，存储的是 31，就会导致永久循环。

让我先运行测试看看当前状态：

        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/crypto_hash/ -q 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在开始修复。首先，**修复算法层的防御性限幅** - 在 `BcryptSimulatedAlgorithm.hash` 中恢复 `min` 限幅，同时其他算法也应该有类似的防御性保护。

然后，**修复 `check_rehash_needed`** - 对于迭代次数的比较，需要将当前默认迭代次数先对算法上限取 min，再和存储值比较。


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\algorithms.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复 `check_rehash_needed`，让它感知算法上限。核心思路是：
- 如果当前默认算法和存储哈希的算法相同，那么比较迭代次数时，需要将当前默认迭代次数对算法上限取 min 后再比较
- 如果算法不同（要升级），那么直接看目标算法的有效迭代次数（min(default_iterations, target_algo.max_iterations)）和存储的不同



        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\crypto_hash\service.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行所有测试验证修复。


        
            
toolName: run_command
            
status: success
          
command: cd c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py ; poetry run pytest tests/crypto_hash/ -q 2>&1 undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
所有 **67 个测试全部通过**！修复完成。

## 修复总结

### 修复 1：算法层恢复防御性限幅
在 [algorithms.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/crypto_hash/algorithms.py#L27-L58) 中，所有三个算法（`SHA256Algorithm`、`SHA512Algorithm`、`BcryptSimulatedAlgorithm`）的 `hash` 方法都恢复了 `min(max(1, iterations), self.max_iterations)` 的防御性限幅。这样即使有代码绕过服务层直接调用算法，也不会执行远超设计上限的轮数。

### 修复 2：check_rehash_needed 感知算法上限
在 [service.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/crypto_hash/service.py#L168-L200) 的 `check_rehash_needed` 方法中：
- 先计算当前默认算法的**有效迭代次数** = `min(default_iterations, default_algo.max_iterations)`
- 如果存储哈希和当前默认算法相同：比较存储的迭代次数与有效默认迭代次数
- 如果算法不同：分别对存储算法和目标算法取上限后比较有效迭代次数

这样避免了当用户配置 `iterations=50` 超过 `BCRYPT_V3` 上限 31 时，存储值为 31 但每次比较都与 50 不等导致的**永久重哈希循环**。