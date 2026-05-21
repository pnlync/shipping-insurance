# 02 Olist Data Understanding

## Dataset

数据集：

```text
Olist Brazilian E-Commerce Public Dataset
```

项目中使用它来模拟电商订单、商家、商品、买家区域和物流运费结构。它不是 TikTok Shop 数据，也没有真实运费险理赔标签。

## Relationship Diagram

![Olist dataset relationship diagram](assets/olist_dataset_relationship_diagram.png)

这张图展示了 Olist 各张表之间的主要连接键。注意：图中没有画出 `product_category_name_translation.csv`，但项目中需要用它把葡萄牙语品类名转换成英文品类名。

## CSV Files

Olist 数据集通常包含 9 张表：

```text
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

## Core Tables for Phase 1

Phase 1 先使用 6 张表：

```text
olist_order_items_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
product_category_name_translation.csv
olist_customers_dataset.csv
olist_sellers_dataset.csv
```

暂时不使用：

```text
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_geolocation_dataset.csv
```

## Table Roles

```text
olist_order_items_dataset:
主表。提供 order_id, order_item_id, product_id, seller_id, price, freight_value。

olist_orders_dataset:
提供 customer_id, order_purchase_timestamp, order_estimated_delivery_date 等订单时间信息。

olist_products_dataset:
提供 product_category_name, product_weight_g, product_length_cm, product_height_cm, product_width_cm。

product_category_name_translation:
把葡萄牙语品类名映射为英文品类名。

olist_customers_dataset:
提供 customer_state, customer_city, customer_zip_code_prefix。

olist_sellers_dataset:
提供 seller_state, seller_city, seller_zip_code_prefix。
```

详细字段说明见：

```text
05_phase1_field_dictionary.md
```

## Important Limitation

Olist 没有真实退货险理赔字段，所以后续需要模拟 returns layer 和 claims layer：

```text
return_requested
return_approved
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
commercial_premium
```
