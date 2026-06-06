# SoloCoder-py

AI 编程模型数据标注项目。通过设计具有挑战性的编程任务，系统化测试 AI 模型在真实工程环境下的代码生成、需求迭代、错误修复和代码重构能力。

## 前置条件

- Python >= 3.13
- [Poetry](https://python-poetry.org/)（依赖管理与虚拟环境）

## 快速开始

```bash
# 安装依赖
poetry install

# 运行单元测试
poetry run pytest

# 运行特定包的测试
poetry run pytest tests/order/

# 运行测试并显示覆盖率（需安装 pytest-cov）
poetry run pytest --cov=src/solocoder_py
```

## 依赖管理

```bash
# 添加依赖
poetry add <package>

# 添加开发依赖
poetry add --group dev <package>

# 更新依赖
poetry update

# 导出 requirements.txt
poetry export -f requirements.txt --output requirements.txt
```
