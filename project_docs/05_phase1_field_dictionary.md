# 05 Phase 1 Field Dictionary

本文档记录 Phase 1 构建 `exposure_table` 时会用到的原始表和字段。

Phase 1 目标不是建模，而是理解并整理数据：

```text
raw Olist CSVs -> exposure_table
```

基础 exposure 粒度：

```text
order_id + order_item_id + seller_id + product_id
```

## 1. olist_order_items_dataset.csv

这是 Phase 1 的主表。每一行代表一笔订单中的一个商品明细。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `order_id` | Yes | 订单 ID | 用来连接 `olist_orders_dataset`，也用于后续聚合到订单级。 |
| `order_item_id` | Yes | 同一订单内的商品明细序号 | 和 `order_id` 一起区分同一订单中的多个商品明细。 |
| `product_id` | Yes | 商品 ID | 用来连接商品品类、重量和体积信息。 |
| `seller_id` | Yes | 卖家 ID | 用来连接卖家地区，也用于商家风险和 credibility。 |
| `shipping_limit_date` | Later | 卖家最晚发货时限 | 可用于履约压力或后验分析；Phase 1 先保留但不作为核心报价变量。 |
| `price` | Yes | 商品成交价格 | 用于商品价值、价格分层、`freight_value / price` 运费占比。 |
| `freight_value` | Yes | 该商品明细对应的运费 | 运费险定价核心字段；可作为赔付金额模拟和保费上限基础。 |

Phase 1 核心保留字段：

```text
order_id, order_item_id, product_id, seller_id, price, freight_value
```

派生字段：

```text
freight_to_price_ratio = freight_value / price
```

注意：

```text
不要直接用 order_id 当唯一样本。
同一 order_id 可能有多个 order_item_id，也可能涉及多个 seller_id。
```

## 2. olist_orders_dataset.csv

这是订单主表。每一行代表一个订单。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `order_id` | Yes | 订单 ID | 用来连接 `order_items`。 |
| `customer_id` | Yes | 买家 ID | 用来连接 `olist_customers_dataset`，获取买家地区。 |
| `order_status` | Yes | 订单状态 | Phase 1 可用于过滤或标记订单状态，例如 delivered/canceled。 |
| `order_purchase_timestamp` | Yes | 下单时间 | 可派生月份、星期、季节性变量；报价时已知。 |
| `order_approved_at` | Later | 付款批准时间 | 可用于付款处理时长；Phase 1 可先不建特征。 |
| `order_delivered_carrier_date` | No for pricing | 交给承运商时间 | 履约后才知道，不能作为报价特征；可用于后验分析。 |
| `order_delivered_customer_date` | No for pricing | 实际送达时间 | 履约后才知道，不能作为报价特征；可用于模拟物流异常或监控。 |
| `order_estimated_delivery_date` | Yes | 预计送达时间 | 可用于预计配送窗口，通常在交易时或发货前可获得。 |

Phase 1 核心保留字段：

```text
order_id, customer_id, order_status,
order_purchase_timestamp, order_estimated_delivery_date
```

派生字段：

```text
purchase_month
purchase_weekday
estimated_delivery_days =
order_estimated_delivery_date - order_purchase_timestamp
```

注意：

```text
order_delivered_customer_date 可以帮助理解实际物流表现，
但它是结果变量/后验信息，不应进入报价模型。
```

## 3. olist_products_dataset.csv

这是商品属性表。每一行代表一个商品。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `product_id` | Yes | 商品 ID | 用来连接 `order_items`。 |
| `product_category_name` | Yes | 葡萄牙语商品品类 | 用来连接英文翻译表；品类是退货和物流风险的重要变量。 |
| `product_name_lenght` | No | 商品标题长度 | Phase 1 不使用。注意原字段拼写是 `lenght`。 |
| `product_description_lenght` | No | 商品描述长度 | Phase 1 不使用。注意原字段拼写是 `lenght`。 |
| `product_photos_qty` | Later | 商品图片数量 | 可作为商品信息完整度代理变量；Phase 1 先不使用。 |
| `product_weight_g` | Yes | 商品重量，单位克 | 物流成本和退货运费的重要变量。 |
| `product_length_cm` | Yes | 商品长度，厘米 | 用于计算体积。 |
| `product_height_cm` | Yes | 商品高度，厘米 | 用于计算体积。 |
| `product_width_cm` | Yes | 商品宽度，厘米 | 用于计算体积。 |

Phase 1 核心保留字段：

```text
product_id, product_category_name,
product_weight_g, product_length_cm, product_height_cm, product_width_cm
```

派生字段：

```text
product_volume_cm3 =
product_length_cm * product_height_cm * product_width_cm
```

注意：

```text
品类字段原始语言是葡萄牙语。
报告和展示时建议使用英文翻译字段。
```

## 4. product_category_name_translation.csv

这是品类翻译表。每一行把一个葡萄牙语品类映射成英文品类。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `product_category_name` | Yes | 葡萄牙语品类名 | 用来连接 `olist_products_dataset`。 |
| `product_category_name_english` | Yes | 英文品类名 | 用于建模展示、报告和面试讲解。 |

Phase 1 核心保留字段：

```text
product_category_name, product_category_name_english
```

注意：

```text
如果某些 product_category_name 找不到英文翻译，
可以保留原始品类或标记为 unknown。
```

## 5. olist_customers_dataset.csv

这是买家信息表。每一行代表一个 customer_id。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `customer_id` | Yes | 订单层买家 ID | 用来连接 `olist_orders_dataset`。 |
| `customer_unique_id` | Later | 去重后的买家 ID | 可用于复购或客户历史；Phase 1 不使用。 |
| `customer_zip_code_prefix` | Later | 买家邮编前缀 | 后续可连接 geolocation 或估算距离；Phase 1 先不使用。 |
| `customer_city` | Later | 买家城市 | 可用于更细区域分析；Phase 1 先保留但不作为核心。 |
| `customer_state` | Yes | 买家州 | 用于目的地区域、路线风险和跨州标记。 |

Phase 1 核心保留字段：

```text
customer_id, customer_state
```

可保留但先不建模：

```text
customer_city, customer_zip_code_prefix
```

派生字段：

```text
customer_region = customer_state
```

## 6. olist_sellers_dataset.csv

这是卖家信息表。每一行代表一个 seller_id。

| Field | Use? | Meaning | Why It Matters |
|---|---:|---|---|
| `seller_id` | Yes | 卖家 ID | 用来连接 `order_items`，也是商家风险监控的核心 ID。 |
| `seller_zip_code_prefix` | Later | 卖家邮编前缀 | 后续可连接 geolocation 或估算距离；Phase 1 先不使用。 |
| `seller_city` | Later | 卖家城市 | 可用于更细区域分析；Phase 1 先保留但不作为核心。 |
| `seller_state` | Yes | 卖家州 | 用于发货地区域、路线风险和跨州标记。 |

Phase 1 核心保留字段：

```text
seller_id, seller_state
```

可保留但先不建模：

```text
seller_city, seller_zip_code_prefix
```

派生字段：

```text
seller_region = seller_state
```

## 7. Exposure Table Target Fields

Phase 1 最终生成的 `exposure_table` 建议包含：

| Field | Source | Meaning |
|---|---|---|
| `order_id` | order_items | 订单 ID |
| `order_item_id` | order_items | 订单内商品明细序号 |
| `seller_id` | order_items | 卖家 ID |
| `product_id` | order_items | 商品 ID |
| `customer_id` | orders | 买家 ID |
| `order_status` | orders | 订单状态 |
| `order_purchase_timestamp` | orders | 下单时间 |
| `order_estimated_delivery_date` | orders | 预计送达时间 |
| `product_category_name` | products | 原始葡萄牙语品类 |
| `product_category_name_english` | translation | 英文品类 |
| `price` | order_items | 商品价格 |
| `freight_value` | order_items | 运费 |
| `freight_to_price_ratio` | derived | 运费占商品价格比例 |
| `product_weight_g` | products | 商品重量 |
| `product_volume_cm3` | derived | 商品体积 |
| `seller_state` | sellers | 卖家州 |
| `customer_state` | customers | 买家州 |
| `route_state` | derived | 卖家州到买家州路线，例如 `SP_to_RJ` |
| `cross_state_flag` | derived | 是否跨州 |
| `purchase_month` | derived | 下单月份 |
| `purchase_weekday` | derived | 下单星期 |
| `estimated_delivery_days` | derived | 预计配送天数 |

## 8. Fields Not Used in Phase 1

这些表和字段不是没用，而是暂时不进入 Phase 1：

```text
olist_order_payments_dataset:
后续可加入 payment_type, payment_installments, payment_value。

olist_order_reviews_dataset:
后续用于后验体验分析，不应直接作为报价变量。

olist_geolocation_dataset:
后续用于估算距离，但 zip prefix 不是唯一经纬度映射，处理更复杂。
```

## 9. Pricing Feature Eligibility

报价模型只能使用报价时已知或可合理估计的字段。

可以用于报价：

```text
price
freight_value
product_category_name_english
product_weight_g
product_volume_cm3
seller_state
customer_state
route_state
order_purchase_timestamp
order_estimated_delivery_date
```

不能用于报价，但可用于后验分析：

```text
order_delivered_carrier_date
order_delivered_customer_date
review_score
review_comment_message
actual_delivery_delay
final_return_reason
claim_status
```

