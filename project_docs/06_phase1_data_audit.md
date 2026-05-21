# 06 Phase 1 Data Audit

本文档记录 Phase 1 开始前的数据体检结果。

目的不是建模，而是确认：

```text
每张表的粒度
关键字段是否唯一
连接键是否可靠
缺失值是否会影响 exposure table
为什么不能用 order_id 作为唯一 exposure
```

## 1. Table Size

| Table | Rows | Columns | Phase 1 Role |
|---|---:|---:|---|
| `olist_order_items_dataset.csv` | 112,650 | 7 | 主表，定义 exposure |
| `olist_orders_dataset.csv` | 99,441 | 8 | 订单时间、状态、customer_id |
| `olist_products_dataset.csv` | 32,951 | 9 | 商品品类、重量、体积 |
| `product_category_name_translation.csv` | 71 | 2 | 品类英文翻译 |
| `olist_customers_dataset.csv` | 99,441 | 5 | 买家地区 |
| `olist_sellers_dataset.csv` | 3,095 | 4 | 卖家地区 |

## 2. Primary Key Checks

| Check | Result | Interpretation |
|---|---:|---|
| `order_items` rows | 112,650 | exposure 主表行数 |
| unique `order_id + order_item_id + seller_id + product_id` | 112,650 | exposure key 在当前数据中唯一 |
| unique `order_id` in order_items | 98,666 | 有些订单没有出现在 order_items，通常不是已成交商品明细 |
| `orders` rows | 99,441 | 订单主表行数 |
| unique `order_id` in orders | 99,441 | `orders.order_id` 唯一 |
| `products` rows | 32,951 | 商品主表行数 |
| unique `product_id` | 32,951 | `products.product_id` 唯一 |
| `customers` rows | 99,441 | 买家表行数 |
| unique `customer_id` | 99,441 | `customers.customer_id` 唯一 |
| `sellers` rows | 3,095 | 卖家表行数 |
| unique `seller_id` | 3,095 | `sellers.seller_id` 唯一 |
| translation rows | 71 | 品类翻译表行数 |
| unique `product_category_name` | 71 | 翻译表品类唯一 |

## 3. Join Key Checks

| Join | Match Rate | Interpretation |
|---|---:|---|
| `order_items.order_id -> orders.order_id` | 100.00% | 每个商品明细都能找到订单主表 |
| `order_items.product_id -> products.product_id` | 100.00% | 每个商品明细都能找到商品信息 |
| `order_items.seller_id -> sellers.seller_id` | 100.00% | 每个商品明细都能找到卖家信息 |
| `orders.customer_id -> customers.customer_id` | 100.00% | 每个订单都能找到买家信息 |
| `products.product_category_name -> translation.product_category_name` | 99.96% | 几乎所有非空品类都有英文翻译 |

结论：

```text
Phase 1 的 6 张核心表连接关系可靠。
可以从 order_items 出发构建 exposure_table。
```

## 4. Missing Value Checks

### olist_order_items_dataset

无缺失值。

### olist_orders_dataset

| Field | Missing Rate | Use in Pricing? | Note |
|---|---:|---|---|
| `order_delivered_customer_date` | 2.98% | No | 实际送达时间是后验信息，不进入报价模型 |
| `order_delivered_carrier_date` | 1.79% | No | 交给承运商时间是后验履约信息 |
| `order_approved_at` | 0.16% | Later | 付款批准时间可后续分析，但 Phase 1 不需要 |

### olist_products_dataset

| Field | Missing Rate | Use in Pricing? | Note |
|---|---:|---|---|
| `product_category_name` | 1.85% | Yes | 缺失品类可标记为 `unknown` |
| `product_name_lenght` | 1.85% | No | Phase 1 不使用 |
| `product_description_lenght` | 1.85% | No | Phase 1 不使用 |
| `product_photos_qty` | 1.85% | Later | 可后续作为商品信息完整度变量 |
| `product_weight_g` | 0.006% | Yes | 极少缺失，可填充或删除 |
| `product_length_cm` | 0.006% | Yes | 极少缺失，可填充或删除 |
| `product_height_cm` | 0.006% | Yes | 极少缺失，可填充或删除 |
| `product_width_cm` | 0.006% | Yes | 极少缺失，可填充或删除 |

### product_category_name_translation

无缺失值。

### olist_customers_dataset

无缺失值。

### olist_sellers_dataset

无缺失值。

## 5. Why Exposure-Level Modeling Is Necessary

数据体检直接证明不能把 `order_id` 当成唯一 exposure：

| Metric | Result |
|---|---:|
| order item rows | 112,650 |
| unique orders in order_items | 98,666 |
| orders with multiple item rows | 9,803 |
| orders with multiple sellers | 1,278 |
| max item rows in one order | 21 |

解释：

```text
同一 order_id 可能包含多个商品明细。
同一 order_id 也可能涉及多个 seller_id。
freight_value 位于 order_items 层。
```

因此基础风险单位应继续使用：

```text
order_id + order_item_id + seller_id + product_id
```

## 6. Phase 1 Decision

基于本次体检，Phase 1 可以安全地从 `olist_order_items_dataset.csv` 出发，依次连接：

```text
1. olist_orders_dataset.csv
2. olist_products_dataset.csv
3. product_category_name_translation.csv
4. olist_customers_dataset.csv
5. olist_sellers_dataset.csv
```

得到：

```text
data/processed/exposure_table.csv
```

下一步：

```text
写 build_exposure_table.py
生成 exposure_table
输出基础 EDA summary
```

