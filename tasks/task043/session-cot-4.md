好的，我来修复这个校验逻辑重复的问题。先看一下当前 engine.py 的完整代码：







        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cart\engine.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在开始重构，提取 `_validate_product_available` 作为公共校验方法，然后让 `_validate_and_clip_quantity` 和 add 方法都复用它：





        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cart\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在重构 add 方法复用公共校验，同时更新 update 方法适配 `_validate_and_clip_quantity` 的新返回签名：











        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cart\engine.py
          
changes: undefined
          
现在更新 update 方法适配 `_validate_and_clip_quantity` 的新返回签名：















        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\cart\engine.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在运行测试验证重构是否正确：


















        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/cart/ -q undefined
          
所有 **67 个测试**全部通过！再运行一下诊断检查：

















        
            
toolName: GetDiagnostics
            
status: success
          
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
校验逻辑重复问题已修复并验证通过。以下是修复总结：

## 修复内容

### 提取公共校验方法 `_validate_product_available`
**修改文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L88-L96)

新增私有方法，统一封装商品可用性校验（商品存在 + 在线状态 + 库存非零），返回 Product 对象供后续逻辑使用：
```python
def _validate_product_available(self, product_id: str) -> Product:
    product = self.get_product(product_id)
    if not product.is_online:
        raise ProductOfflineError(f"Product is offline: {product_id}")
    if product.stock == 0:
        raise InsufficientStockError(f"Product {product_id} is out of stock")
    return product
```

### 重构 `_validate_and_clip_quantity` 复用公共校验
**修改文件**：[engine.py](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L98-L113)

- 内部调用 `_validate_product_available` 完成商品可用性校验，不再重复实现
- 返回值扩展为三元组 `(clipped_quantity, trim_notification, product)`，将校验得到的 Product 一并返回，避免调用方重复查询

### 重构 add 方法复用公共校验
**修改文件**：
- [add_to_anonymous_cart](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L115-L131)
- [add_to_user_cart](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L133-L149)

将内联的商品存在检查、在线检查、库存为零检查替换为调用 `_validate_product_available(product_id)`，add 和 update 方法现在走同一条校验代码路径。

### 更新 update 方法适配新返回签名
**修改文件**：
- [update_anonymous_cart_quantity](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L163-L172)
- [update_user_cart_quantity](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/cart/engine.py#L174-L183)

解包时忽略新增的第三个返回值：`clipped_quantity, _, _ = self._validate_and_clip_quantity(...)`

## 校验逻辑架构（修复后）
```
add_to_*_cart ──┐
                ├──▶ _validate_product_available (商品存在/在线/非零库存)
update_*_cart ──┘       │
                        ▼
              _validate_and_clip_quantity (数量上限裁剪)
```

## 测试结果
```
poetry run pytest tests/cart/ -q
...................................................................      [100%]
67 passed in 0.10s
```