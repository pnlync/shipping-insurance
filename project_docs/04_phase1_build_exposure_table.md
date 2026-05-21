# 04 Phase 1 Build Exposure Table

## Objective

生成第一版 exposure 级建模表：

```text
data/processed/exposure_table.csv
```

每一行代表：

```text
order_id + order_item_id + seller_id + product_id
```

## Required Raw Files

把 Kaggle 下载并解压后的 CSV 放到：

```text
data/raw/
```

Phase 1 需要：

```text
data/raw/olist_order_items_dataset.csv
data/raw/olist_orders_dataset.csv
data/raw/olist_products_dataset.csv
data/raw/product_category_name_translation.csv
data/raw/olist_customers_dataset.csv
data/raw/olist_sellers_dataset.csv
```

## Target Columns

第一版 exposure table 至少包含：

```text
order_id
order_item_id
seller_id
product_id
customer_id
product_category_name
product_category_name_english
price
freight_value
product_weight_g
product_volume_cm3
seller_state
customer_state
route_state
order_purchase_timestamp
order_estimated_delivery_date
```

每个字段的来源和使用原因见：

```text
05_phase1_field_dictionary.md
```

## Basic Checks

生成表后必须检查：

```text
row count
unique order_id count
unique seller_id count
unique product_id count
missing rate by column
average exposures per order
orders with multiple sellers
freight_value distribution
top categories
top seller_state -> customer_state routes
```

## Done Criteria

Phase 1 的第一步完成标准：

```text
exposure_table.csv 可以稳定生成
基础字段没有明显 join 错误
exposure 粒度解释清楚
关键 EDA 数字记录到文档或 README
```

数据体检结果见：

```text
06_phase1_data_audit.md
```

## Build Result

脚本：

```text
src/build_exposure_table.py
```

输出：

```text
data/processed/exposure_table.csv
data/processed/exposure_table_summary.json
```

当前生成结果：

| Metric | Value |
|---|---:|
| rows | 112,650 |
| columns | 29 |
| unique exposure key | 112,650 |
| unique order_id | 98,666 |
| unique seller_id | 3,095 |
| unique product_id | 32,951 |
| orders with multiple exposures | 9,803 |
| orders with multiple sellers | 1,278 |
| max exposures per order | 21 |

缺失值：

```text
product_weight_g: 0.016%
product_length_cm: 0.016%
product_height_cm: 0.016%
product_width_cm: 0.016%
product_volume_cm3: 0.016%
```

这些缺失率极低，Phase 1 后续可以选择删除这些行，或用品类中位数填充。

运费分布：

```text
freight_value min: 0.00
freight_value median: 16.26
freight_value mean: 19.99
freight_value max: 409.68
```

运费占比：

```text
freight_to_price_ratio min: 0.00
freight_to_price_ratio median: 0.231
freight_to_price_ratio mean: 0.321
freight_to_price_ratio max: 26.235
```

注意：

```text
freight_to_price_ratio 最大值很高，说明存在低商品价格但高运费的明细。
后续建模前需要 winsorize、cap，或用 log/分箱处理。
```

Top categories:

```text
bed_bath_table: 11,115
health_beauty: 9,670
sports_leisure: 8,641
furniture_decor: 8,334
computers_accessories: 7,827
```

Top routes:

```text
SP_to_SP: 36,192
SP_to_RJ: 9,688
SP_to_MG: 8,703
SP_to_RS: 4,194
SP_to_PR: 3,667
```

结论：

```text
exposure_table 已成功生成。
行数和唯一键符合预期。
下一步可以做 exposure-level EDA，然后再模拟 claim_flag 和 paid_loss。
```
