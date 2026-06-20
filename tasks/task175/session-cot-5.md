两个问题都正确：从单一运行时样本反推的严格不等式（`>`、`<`）比必要条件更严格，应改为包含边界值的非严格不等式（`>=`、`<=`）。


        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
先确认当前代码，然后一并修复两处。





        
            
toolName: view_files
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geohash\test_edge_cases.py
          
两处严格不等式都在同一位置，一次性修复：

- `east_bbox.min_lon > 0` → `east_bbox.min_lon >= 0`（逻辑否定原 OR 的 `min_lon < 0`）
- `west_bbox.max_lon < 0` → `west_bbox.max_lon <= 0`（逻辑否定原 OR 的 `max_lon > 0`）







        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geohash\test_edge_cases.py
          
changes: undefined
          

        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: edit_file_search_replace
            
status: success
          
            
filePath: c:\Users\vince\GoletaLab\SoloCoder-3\solocoder-py\tests\geohash\test_edge_cases.py
          
changes: undefined
          
两处都已修复。现在运行测试验证。



        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          

        
            
toolName: run_command
            
status: success
          
command: python -m pytest tests/geohash/ -v --tb=short undefined
          

        
            
toolName: GetDiagnostics
            
status: success
          
          
108 个测试全部通过，无 lint/类型错误。






        
            
toolName: todo_write
            
status: success
          
Todos updated: 3 items
          
---

## ✅ 两处严格不等式断言修复完成，108 个测试全部通过

### 修复 1：[test_east_neighbor_not_at_antimeridian](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geohash/test_edge_cases.py#L225)

| 项目 | 内容 |
|------|------|
| 修复前 | `assert east_bbox.min_lon > 0` |
| 修复后 | `assert east_bbox.min_lon >= 0` |
| 推理依据 | 原 OR 断言中被否定的条件是 `min_lon < 0`（意为"没有跨越到负经度"，其严格逻辑否定是 `min_lon >= 0`，严格 `>` 排除了恰好等于 0 的合法边界取值 |

### 修复 2：[test_west_neighbor_not_at_antimeridian](file:///c:/Users/vince/GoletaLab/SoloCoder-3/solocoder-py/tests/geohash/test_edge_cases.py#L248)

| 项目 | 内容 |
|------|------|
| 修复前 | `assert west_bbox.max_lon < 0` |
| 修复后 | `assert west_bbox.max_lon <= 0` |
| 推理依据 | 原 OR 断言中被否定的条件是 `max_lon > 0`（意为"没有跨越到正经度"），其严格逻辑否定是 `max_lon <= 0`，严格 `<` 排除了恰好等于 0 的合法边界取值 |

### 断言逻辑的推导链

```
测试意图：验证非边界邻胞没有跨越反子午线
├─ 东向邻胞（120°E prec=6）
│   ├─ 原 OR：`max_lon < 180 or min_lon < 0`  ← 一个条件恒真、一个恒假，断言无意义
│   ├─ 实际语义：`¬(跨越反子午线)` = `min_lon >= 0` ∧ `max_lon < 180`
│   └─ 修复后：两个独立断言 `min_lon >= 0` + `max_lon < 180`
└─ 西向邻胞（-120°E prec=6）
    ├─ 原 OR：`min_lon > -180 or max_lon > 0` ← 一个条件恒真、一个恒假，断言无意义
    ├─ 实际语义：`¬(跨越反子午线)` = `min_lon > -180` ∧ `max_lon <= 0`
    └─ 修复后：两个独立断言 `min_lon > -180` + `max_lon <= 0`
```

两处修复都严格遵循了逻辑否定的德摩根定律，避免了从单一运行时样本反推的过度严格断言。