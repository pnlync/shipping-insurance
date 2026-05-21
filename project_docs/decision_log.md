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

## 2026-05-21: Use Insurance-Style Synthetic Claim Labels

Decision:

```text
下一步不只生成 return_flag，也不只生成 claim_flag 和 paid_loss。
第一版 synthetic layer 拆成 returns layer 和 claims layer。
```

Core fields:

```text
returns layer:
return_requested, return_reason, return_approved,
refund_without_return, partial_refund, request_days_after_delivery

claims layer:
covered_claim_flag, claim_type, gross_loss,
recovery_from_carrier, paid_loss, net_loss, claim_status
```

Reason:

```text
退货事件不等于保险赔付事件。
项目目标是运费险定价，不是普通退货率预测。
保险化标签能支持 frequency / severity / expected loss 的精算定价闭环。
```

Implication:

```text
Phase 1 第一版先只模拟 Coverage A: Return Shipping。
Coverage B: Failed Delivery / Logistics Exception 和
Coverage C: Replacement / Reshipment Shipping 后续再扩展。
```

## 2026-05-21: Use 60% Target Loss Ratio for Baseline Pricing

Decision:

```text
第一版 baseline commercial premium 使用 target_loss_ratio = 60% 反推。
```

Formula:

```text
commercial_premium = pure_premium / target_loss_ratio
```

Reason:

```text
纯保费只覆盖预期赔款。
商业保费需要覆盖费用、利润、风险边际和资本成本。
60% 目标赔付率是第一版清晰、可解释的商业定价假设。
```

Implication:

```text
当前 synthetic claims 下：
portfolio pure premium = 1.4802
portfolio commercial premium = 2.4670
expected loss ratio = 60.00%
```

## 2026-05-21: Use Two-Part GLM for Phase 2 Pricing

Decision:

```text
Phase 2 使用 two-part GLM：
frequency = Binomial GLM with logit link, target = covered_claim_flag
severity = Gamma GLM with log link, target = net_loss on covered claims only
```

Reason:

```text
运费险 exposure 的 expected loss 应拆成：
P(covered claim) * E(net_loss | covered claim)

covered_claim_flag 是保险赔付频率标签，不是普通退货标签。
net_loss 是进入赔付率和纯保费的最终净赔款。
```

Leakage control:

```text
GLM 只使用报价时已知变量。
return_requested、return_reason、claim_type、paid_loss、net_loss、claim_status
以及 return_probability、covered_claim_probability、return_factor_* 等
synthetic generation fields 都不能作为 feature。
```

Implication:

```text
GLM 输出仍保持 exposure-level pricing：
order_id + order_item_id + seller_id + product_id。

seller_id 暂时只作为 identifier 保留，不直接入模。
seller credibility 和 seller-level dynamic adjustment 留到 Phase 3。
```
