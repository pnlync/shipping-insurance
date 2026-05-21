# Decision Log

这个文件记录项目中的关键设计决策。每条决策都要写清楚背景、决定和原因。

## 2026-05-20: Use Exposure-Level Pricing

Decision:

```text
基础风险单位使用 order_id + order_item_id + seller_id + product_id。
```

Reason:

```text
Olist 的 freight_value 位于 order_items 层。
一笔订单可能包含多个商品或多个卖家。
运费险定价需要把商品、商家和物流风险精确归因到明细层。
```

Implication:

```text
模型、理赔模拟和纯保费计算都在 exposure 层完成。
订单级展示、商家级监控和组合级赔付率都从 exposure 层聚合得到。
```

## 2026-05-20: Keep Product Category Translation Table

Decision:

```text
保留 product_category_name 和 product_category_name_english 两个字段。
建模和报告优先使用英文品类字段。
```

Reason:

```text
Olist 原始 product_category_name 是葡萄牙语。
英文品类更适合报告展示和面试讲解。
保留原始字段便于追溯。
```

