你说得对！这两个测试调用了 `_resolve_conflicts` 私有方法，完全绕过了 `evaluate` 中的显式拒绝双重检查过滤逻辑。我来修复它们，通过完整的 `evaluate` 流程端到端验证。

由于 models.py 已经在构造时校验了语义约束，我需要用 `object.__setattr__` 方式模拟数据异常场景，从而测试 engine.py 的防御性双重检查。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\abac\test_abac.py
          
changes: undefined
          
现在运行测试验证：




        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          

        
            
toolName: run_command
            
status: success
          
command: poetry run pytest tests/abac/ -q undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 2 items
          
修复完成！**88 个测试全部通过**。

## 修复说明

重写了两个测试用例，从直接调用 `_resolve_conflicts` 私有方法改为通过完整的 `evaluate` 公有方法端到端验证，真正覆盖 `engine.py` 中的显式拒绝双重检查过滤逻辑：

### 1. `test_permit_with_explicit_deny_flag_does_not_trigger_override_via_evaluate`
- 使用 `object.__setattr__` 模拟一个数据异常的 PERMIT 策略（`is_explicit_deny=True` 但 `effect=PERMIT`）
- 通过完整 `evaluate()` 流程验证：**即使 flag 被错误设置为 True，因为 effect 不是 DENY，也不会触发显式拒绝优先**
- 最终决策走正常的 `PERMIT_OVERRIDES` 冲突裁决 → 结果为 PERMIT
- 断言 `resolved_by == "PERMIT_OVERRIDES"` 而非 `"EXPLICIT_DENY_OVERRIDE"`

### 2. `test_real_explicit_deny_triggers_override_via_full_evaluate`
- 正向验证：合法的显式拒绝策略（`effect=DENY, is_explicit_deny=True`）
- 通过完整 `evaluate()` 流程验证：**正确触发显式拒绝优先**
- 即使 PERMIT 策略优先级为 999 远高于 DENY 的 1，最终决策仍为 DENY
- 断言 `resolved_by == "EXPLICIT_DENY_OVERRIDE"`

这两个测试现在完全覆盖了 `engine.py` 中 `evaluate` 方法里的双重检查代码路径（`if h.is_explicit_deny and h.effect == PolicyEffect.DENY`）。