# 03 Exposure Definition

## Primary Exposure Unit

本项目的基础风险单位不是 `order_id`，而是：

```text
order_id + order_item_id + seller_id + product_id
```

含义：

```text
一个卖家在一个订单中的一个商品明细，对应一次物流运费险风险暴露。
```

## Why Not Use order_id Alone

不能直接把 `order_id` 当作唯一 exposure，原因：

1. 一笔订单可能包含多个商品。
2. 一笔订单可能涉及多个卖家。
3. `freight_value` 在 `olist_order_items_dataset` 表中，属于订单商品明细层级。
4. 商品品类、重量、体积和价格也需要和具体 `product_id` 对齐。
5. 商家风险必须准确归因到对应 `seller_id`。

## Aggregation Levels

```text
Exposure level:
用于建模、模拟理赔、计算 expected loss 和 premium。

Order level:
同一 order_id 下多个 exposure 的 premium 加总，得到订单总保费。

Seller level:
同一 seller_id 下多个 exposure 汇总，用于赔付率监控和 credibility。

Portfolio level:
全部 exposure 汇总，用于整体赔付率、盈利性和压力测试。
```

## Core Pricing Logic

```text
Expected Loss_i =
P(Claim_i) * E(Paid Loss_i | Claim_i)

Commercial Premium_i =
Expected Loss_i / Target Loss Ratio
+ Expense Load
+ Risk Margin
```

