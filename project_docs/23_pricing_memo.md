# 23 Pricing Memo

## Executive Summary

本项目构建了一个面向电商中小卖家的往返运费险定价框架。

项目重点不是单纯预测退货，而是建立保险定价闭环：

```text
exposure definition
-> synthetic returns and claims layer
-> baseline pricing
-> GLM frequency / severity pricing
-> seller credibility adjustment
-> loss ratio monitoring
-> stress testing
```

当前定价单位保持在 exposure level：

```text
order_id + order_item_id + seller_id + product_id
```

这个粒度表示：

```text
一个卖家在一笔订单中的一个商品明细产生的一次退货运费险风险暴露。
```

第一版产品只模拟：

```text
Coverage A: Return Shipping
买家合规退货产生的回仓运费。
```

暂未模拟：

```text
failed delivery
replacement shipping
fraud
real claim development
```

当前结果基于 Olist public e-commerce data 和 synthetic claims，不代表真实 TikTok Shop 参数。

## 1. Product and Coverage Assumption

保险责任：

```text
当订单已妥投，买家发生合规退货并产生回仓运费时，
保险赔付对应 return shipping cost。
```

不保障：

```text
商品退款本身
退款不退货
未通过审核的退货
非 delivered exposure
欺诈退货
平台规则外售后
```

第一版只对：

```text
order_status == delivered
```

的 exposure 生成 eligible claims。

## 2. Data and Exposure Definition

输入数据来自 Olist public dataset。

Olist 有订单、商品、卖家、买家地区、运费、预计配送时间等字段，但没有真实退货险理赔。

因此项目构造了 synthetic returns + claims layer。

核心 exposure key：

```text
order_id + order_item_id + seller_id + product_id
```

不直接使用 `order_id` 作为唯一 exposure。

原因：

```text
1. 一笔订单可能有多个商品明细。
2. 一笔订单可能涉及多个 seller。
3. freight_value 位于 order item 层。
4. 运费险赔付和保费应在商品明细 / seller 明细层归因。
```

当前 exposure table：

| Metric | Value |
|---|---:|
| total rows | 112,650 |
| eligible exposures | 110,197 |
| ineligible exposures | 2,453 |

## 3. Synthetic Claims Layer

Olist 没有真实 claim data，因此项目生成 synthetic returns + claims layer。

但没有简单生成一个 `return_flag`。

项目拆成两层：

```text
returns layer
claims layer
```

Returns layer：

```text
return_requested
return_approved
refund_without_return
partial_refund
return_reason
request_days_after_delivery
```

Claims layer：

```text
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

核心原则：

```text
退货不等于保险赔付。
```

当前 synthetic claims 结果：

| Metric | Value |
|---|---:|
| eligible exposures | 110,197 |
| return requested count | 9,338 |
| covered claim count | 8,485 |
| covered claim frequency | 7.70% |
| total net loss | 163,112.68 |
| average severity | 19.22 |
| pure premium per eligible exposure | 1.4802 |

## 4. Baseline Pricing

Baseline pricing 是 portfolio average price。

公式：

```text
portfolio_pure_premium =
total_net_loss / eligible_exposures

commercial_premium =
pure_premium / target_loss_ratio
```

当前假设：

```text
target_loss_ratio = 60%
```

结果：

| Metric | Value |
|---|---:|
| portfolio pure premium | 1.4802 |
| portfolio commercial premium | 2.4670 |
| total commercial premium | 271,854.47 |
| expected loss ratio | 60.00% |

Baseline 的作用：

```text
1. 提供最简单 benchmark。
2. 检查 synthetic claims 的赔付水平。
3. 给 GLM 和 credibility pricing 做对照。
```

局限：

```text
所有 eligible exposure 使用同一价格，
不能区分 category、route、freight、seller risk。
```

## 5. GLM Pricing

Phase 2 使用 two-part GLM：

```text
Frequency model:
Binomial GLM with logit link
target = covered_claim_flag

Severity model:
Gamma GLM with log link
target = net_loss
population = covered claims only
```

核心公式：

```text
glm_expected_loss =
glm_frequency * glm_severity

glm_commercial_premium =
glm_expected_loss / 0.60
```

GLM 只使用报价时已知变量：

```text
product_category_name_english
route_state
cross_state_flag
purchase_month
purchase_weekday
price
freight_value_capped
freight_to_price_ratio_capped
product_weight_g_filled
product_volume_cm3_filled
estimated_delivery_days
```

明确不使用：

```text
return_requested
return_reason
covered_claim_probability
claim_type
gross_loss
paid_loss
net_loss
claim_status
return_factor_*
```

GLM validation：

| Metric | Train | Test |
|---|---:|---:|
| frequency AUC | 0.570 | 0.560 |
| actual frequency | 7.68% | 7.80% |
| predicted frequency | 7.68% | 7.66% |
| actual severity | 19.20 | 19.34 |
| predicted severity | 19.30 | 19.43 |
| pure premium A/E | 0.990 | 1.003 |

Interpretation:

```text
Frequency sorting power is moderate.
But test pure premium A/E is close to 1, meaning aggregate expected loss is well calibrated.
```

GLM portfolio pricing:

| Metric | Value |
|---|---:|
| actual total net loss | 163,112.68 |
| GLM expected total loss | 164,831.10 |
| GLM A/E | 0.990 |
| GLM total commercial premium | 274,718.50 |
| GLM expected loss ratio | 60.00% |

## 6. Seller Credibility

GLM does not directly include `seller_id` as a rating factor.

Reason:

```text
seller_id is high-cardinality.
Most sellers have very limited exposure.
Direct seller_id coefficients would be unstable.
```

Seller exposure distribution:

| Metric | Value |
|---|---:|
| sellers with eligible exposure | 2,970 |
| median eligible exposures per seller | 8 |
| sellers with >= 100 exposures | 236 |
| sellers with >= 500 exposures | 29 |

Seller credibility formula:

```text
seller_observed_ae =
seller_actual_net_loss / seller_glm_expected_loss

Z = n / (n + 500)

seller_credibility_relativity_raw =
Z * seller_observed_ae + (1 - Z) * 1.0
```

Risk controls:

```text
cap raw relativity between 0.50 and 2.00
portfolio normalization to preserve total GLM expected loss
```

Important clarification:

```text
Small sellers are not pulled back to portfolio average price.
They are pulled back toward their own exposure mix's GLM base expected loss.
```

Seller credibility result:

| Metric | Value |
|---|---:|
| credibility expected total loss | 164,831.10 |
| credibility total commercial premium | 274,718.50 |
| portfolio expected loss change vs GLM | 0.00% |
| final seller relativity p05 | 0.955 |
| final seller relativity median | 1.000 |
| final seller relativity p95 | 1.060 |

Interpretation:

```text
Most sellers stay near GLM base price.
Only sellers with enough exposure and clear observed A/E deviation receive material adjustment.
```

## 7. Loss Ratio Backtesting and Monitoring

Backtesting / monitoring compares:

```text
actual_loss
expected_loss
commercial_premium
```

Core metrics:

```text
A/E = actual_loss / expected_loss
Loss Ratio = actual_loss / commercial_premium
```

Portfolio result:

| Pricing Basis | A/E | Loss Ratio |
|---|---:|---:|
| baseline | 1.000 | 60.00% |
| GLM | 0.990 | 59.37% |
| GLM + seller credibility | 0.990 | 59.37% |

Seller tier monitoring:

| Seller Risk Tier | Eligible Exposures | GLM A/E | Credibility A/E | Credibility Loss Ratio |
|---|---:|---:|---:|---:|
| near_glm | 97,083 | 0.968 | 0.972 | 58.31% |
| elevated | 8,179 | 1.555 | 1.359 | 81.53% |
| lower_than_glm | 4,935 | 0.636 | 0.729 | 43.73% |

Interpretation:

```text
Seller credibility improves elevated seller tier A/E,
but elevated sellers remain above target loss ratio and should stay on watchlist.
```

## 8. Stress Testing

Stress testing checks how current prices perform under adverse loss scenarios.

Portfolio stress result under credibility pricing:

| Scenario | Loss Multiplier | Stressed Loss Ratio | Flag |
|---|---:|---:|---|
| base_observed | 1.00 | 59.37% | within_target |
| frequency_plus_10 | 1.10 | 65.31% | above_target |
| frequency_plus_20 | 1.20 | 71.25% | above_target |
| severity_plus_10 | 1.10 | 65.31% | above_target |
| severity_plus_20 | 1.20 | 71.25% | above_target |
| combined_10_10 | 1.21 | 71.84% | above_target |
| combined_20_20 | 1.44 | 85.50% | high_pressure |

Seller tier stress:

| Stressed Tier | Portfolio Stressed Loss Ratio | Flag |
|---|---:|---|
| near_glm | 82.26% | high_pressure |
| elevated | 61.88% | above_target |
| lower_than_glm | 60.11% | above_target |

Interpretation:

```text
The portfolio is sensitive to simultaneous frequency and severity deterioration.
near_glm tier has the largest stress impact because it has the highest exposure volume.
elevated tier remains important for underwriting watchlist because its base adequacy is weak.
```

## 9. Recommended Pricing Position

Current recommended technical pricing basis:

```text
GLM expected loss + seller credibility adjustment
```

Reason:

```text
1. Baseline is useful as benchmark but does not differentiate risk.
2. GLM provides explainable risk segmentation using quote-time-known features.
3. Seller credibility adds controlled seller experience adjustment.
4. Portfolio normalization keeps total GLM expected loss level stable.
```

Commercial premium:

```text
commercial_premium =
credibility_expected_loss / 60%
```

Monitoring actions:

```text
1. Track elevated seller tier separately.
2. Track high loss ratio categories such as health_beauty and garden_tools.
3. Track high loss ratio routes such as SC_to_RJ, PR_to_RS, SP_to_PA.
4. Monitor frequency and severity stress indicators separately.
```

## 10. Limitations

Current limitations:

```text
1. Claims are synthetic, not actual TikTok Shop insurance claims.
2. Olist is Brazilian e-commerce data, not TikTok Shop seller data.
3. No true out-of-time validation yet.
4. Seller credibility uses the same synthetic data used for monitoring.
5. No claim development / IBNR.
6. No expense model beyond target loss ratio.
7. No capital model or reinsurance.
8. XGBoost challenger exists, but only as challenger / risk score rather than final pricing model.
```

These limitations are acceptable for the current project phase because the goal is to demonstrate an actuarial pricing framework, not to assert production-ready rates.

## 11. Next Steps

Recommended next steps:

```text
1. For interview presentation:
   convert the deck outline into final slides or a concise walkthrough.

2. For deeper Phase 4 analytics:
   build dashboard or add pricing action / underwriting rules.

3. For real deployment:
   replace synthetic claims with real seller order / return / claim data.
   create historical training period and future validation period.
   add claim development and expense assumptions.
```

Current project status:

```text
Phase 1: exposure table + synthetic claims + baseline pricing completed
Phase 2: GLM pricing completed
Phase 3: seller credibility + loss ratio monitoring + stress testing completed
Phase 4: XGBoost challenger + interpretability + interview deck outline completed
```
