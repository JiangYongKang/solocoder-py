让我先检查一下 `session.py` 文件是否存在，以及其他相关问题：
        
            
toolName: view_folder
            
status: success
          
c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5\session.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5\relay.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          

        
            
toolName: delete_file
            
status: success
          
deleteFilesSingular
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5\session.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 4 items
          
现在修复 `UdpRelay.send_from_client`，当 DNS 解析失败时抛出明确的错误：

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5\relay.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\src\solocoder_py\socks5\relay.py
          
changes: undefined
          
现在需要确保 `Socks5ResolutionError` 在 `__init__.py` 中被导出，并添加 IPv6 正向 CONNECT 测试。让我先检查一下：



        
            
toolName: search_by_regex
            
status: success
          
query: Socks5ResolutionError
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\test_normal_flows.py
          
让我也查看一下测试的 conftest.py 和错误分支测试：


        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\conftest.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\test_error_branches.py
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在添加 IPv6 正向 CONNECT 测试到 `test_normal_flows.py`：


        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\test_normal_flows.py
          
changes: undefined
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\test_normal_flows.py
          
changes: undefined
          
现在添加 UDP 中继域名解析失败的错误测试到 `test_error_branches.py`：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\socks5\test_error_branches.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
现在运行测试验证所有修复：




        
            
toolName: run_command
            
status: success
          
command: & "c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\.venv\Scripts\python.exe" -m pytest tests/socks5/ -v undefined
          
所有 48 个测试全部通过！让我完成最后的更新：





        
            
toolName: todo_write
            
status: success
          
Todos updated: 5 items
          
## 修复完成

已成功修复所有问题，**48 个测试全部通过**。以下是修复详情：

### 1. 删除孤立死代码 `session.py`
- 删除了 [session.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/socks5/session.py)，该文件引用了不存在的 `SimulatedConnection`、`DnsResolver`、`Socks5Request`、`parse_greeting` 等类和方法，与 [server.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/socks5/server.py) 中的实际实现完全不兼容。

### 2. 修复 `UdpRelay.send_from_client` DNS 解析失败静默问题
- 之前：DNS 解析返回 `None` 时，静默地将未解析的域名字符串作为转发目标写入队列
- 现在：当目标地址是域名时，若没有 DNS 解析器或解析失败，抛出 `Socks5ResolutionError`，调用方可以明确感知错误
- 修复位置：[relay.py:49-66](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/src/solocoder_py/socks5/relay.py#L49-L66)

### 3. 添加 IPv6 正向 CONNECT 成功测试
- 在 [test_normal_flows.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/socks5/test_normal_flows.py) 的 `TestConnectCommand` 类中新增 `test_connect_ipv6` 测试用例，验证 IPv6 地址 `2001:db8::1` 可以成功建立 CONNECT 连接并进入中继状态

### 4. 新增 UDP 中继域名解析失败测试
- 在 [test_error_branches.py](file:///C:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/socks5/test_error_branches.py) 的 `TestDomainResolutionFailure` 类中新增 `test_udp_relay_unresolvable_domain_raises_error` 测试，验证 UDP 中继场景下域名解析失败会抛出 `Socks5ResolutionError`