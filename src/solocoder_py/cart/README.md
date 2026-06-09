# Cart Module - 购物车合并域模块

## 模块功能

本模块实现了电商购物车的核心域功能，包括：

1. **购物车基本操作**：添加商品、移除商品、修改商品数量、清空购物车
2. **匿名/登录购物车管理**：支持用户未登录时使用匿名购物车，登录后自动合并
3. **购物车合并与库存裁剪**：登录时合并匿名购物车与用户购物车，自动处理库存上限
4. **商品管理**：商品注册、库存更新、上下架状态管理

## 核心类职责

### Product
商品数据模型，存储商品基本信息：
- `id`: 商品唯一标识
- `name`: 商品名称
- `price`: 商品单价
- `stock`: 商品库存数量
- `is_online`: 商品是否上架

### CartItem
购物车单项数据模型：
- `product_id`: 商品ID
- `quantity`: 商品数量

### Cart
购物车数据模型：
- `id`: 购物车唯一标识
- `user_id`: 用户ID（匿名购物车为 None）
- `items`: 购物车商品项字典（product_id -> CartItem）
- `is_anonymous`: 是否为匿名购物车
- `total_items`: 购物车商品总数量
- `unique_products`: 购物车商品种类数
- 提供 `add_item`、`remove_item`、`update_quantity`、`clear` 等操作方法

### TrimNotification
库存裁剪通知数据模型：
- `product_id`: 被裁剪的商品ID
- `product_name`: 商品名称
- `requested_quantity`: 请求的数量
- `actual_quantity`: 实际保留的数量
- `trimmed_quantity`: 被裁剪掉的数量
- `reason`: 裁剪原因

### MergeResult
购物车合并结果数据模型：
- `cart`: 合并后的购物车
- `trims`: 库存裁剪通知列表
- `removed_offline_products`: 被移除的已下架商品ID列表

### CartEngine
购物车引擎，核心业务逻辑类：
- 商品管理：`register_product`、`get_product`、`update_product_stock`、`set_product_online`
- 匿名购物车管理：`create_anonymous_cart`、`get_anonymous_cart`
- 用户购物车管理：`create_user_cart`、`get_user_cart`、`get_or_create_user_cart`
- 匿名购物车操作：`add_to_anonymous_cart`、`remove_from_anonymous_cart`、`update_anonymous_cart_quantity`、`clear_anonymous_cart`
- 用户购物车操作：`add_to_user_cart`、`remove_from_user_cart`、`update_user_cart_quantity`、`clear_user_cart`
- 购物车合并：`merge_anonymous_to_user_cart`

## 合并裁剪规则

### 数量累加规则
- 匿名购物车与用户购物车中存在相同商品时，数量**累加**而非覆盖
- 例如：用户购物车有商品A 3件，匿名购物车有商品A 2件，合并后为 5 件

### 库存上限裁剪规则
- 合并后每个商品的数量不能超过该商品的库存上限
- 超出部分自动裁剪，并生成 `TrimNotification` 通知用户
- 例如：商品A库存为 10 件，合并后数量为 15 件，则裁剪为 10 件，裁剪掉 5 件

### 已下架商品处理规则
- 匿名购物车中存在已下架（`is_online=False`）或库存为0的商品时，合并时自动移除
- 被移除的商品ID会记录在 `removed_offline_products` 列表中

### 匿名购物车清理规则
- 合并成功后，匿名购物车被清空并从系统中移除

## 使用示例

```python
from decimal import Decimal
from solocoder_py.cart import CartEngine, Product

# 初始化购物车引擎
engine = CartEngine()

# 注册商品
product_a = engine.register_product(Product(
    id="sku-001",
    name="iPhone 15",
    price=Decimal("5999.00"),
    stock=10
))
product_b = engine.register_product(Product(
    id="sku-002",
    name="AirPods Pro",
    price=Decimal("1899.00"),
    stock=20
))

# 用户未登录，使用匿名购物车
anon_cart = engine.create_anonymous_cart()
engine.add_to_anonymous_cart(anon_cart.id, "sku-001", 2)
engine.add_to_anonymous_cart(anon_cart.id, "sku-002", 3)

# 用户登录，合并购物车（假设用户购物车已有商品）
engine.create_user_cart("user-001")
engine.add_to_user_cart("user-001", "sku-001", 1)

# 执行合并
result = engine.merge_anonymous_to_user_cart(anon_cart.id, "user-001")

# 查看合并结果
merged_cart = result.cart
print(f"商品种类数: {merged_cart.unique_products}")
print(f"商品A数量: {merged_cart.get_item('sku-001').quantity}")  # 输出: 3 (1+2)
print(f"商品B数量: {merged_cart.get_item('sku-002').quantity}")  # 输出: 3

# 查看裁剪通知
for trim in result.trims:
    print(f"商品 {trim.product_name} 被裁剪 {trim.trimmed_quantity} 件")
```
