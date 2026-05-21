# 10 Synthetic Claims Build

本文档记录第一版 synthetic returns + claims layer 的实现结果。

设计口径见：

```text
project_docs/09_synthetic_claims_design.md
```

脚本：

```text
src/build_synthetic_claims.py
```

输入：

```text
data/processed/exposure_table.csv
```

输出：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/synthetic_claims_summary.json
```

## 1. Scope

第一版只实现：

```text
Coverage A: Return Shipping
买家合规退货产生的回仓运费。
```

暂不实现：

```text
Coverage B: Failed Delivery / Logistics Exception
Coverage C: Replacement / Reshipment Shipping
```

## 2. Added Fields

新增 EDA / feature treatment 字段：

```text
freight_value_capped
freight_to_price_ratio_capped
product_weight_g_filled
product_weight_g_imputed_flag
product_volume_cm3_filled
product_volume_cm3_imputed_flag
```

新增 return frequency factor 字段：

```text
return_factor_category
return_factor_route
return_factor_freight_ratio
return_factor_size
return_factor_month
```

新增 returns layer 字段：

```text
claim_eligible_flag
return_probability
return_requested
return_approved
refund_without_return
partial_refund
request_days_after_delivery
return_reason
```

新增 claims layer 字段：

```text
covered_claim_probability
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

## 3. Key Assumptions

Random seed:

```text
20260521
```

Frequency assumptions:

```text
base_return_rate: 8%
min_return_probability: 1%
max_return_probability: 25%
```

Severity assumptions:

```text
gross_loss = freight_value_capped * random_noise * partial_refund_multiplier
random_noise: 0.8 to 1.2
partial_refund_multiplier: 0.5 if partial_refund else 1.0
```

Recovery:

```text
5% of covered claims receive carrier recovery.
recovery_from_carrier = gross_loss * random multiplier between 10% and 30%.
```

## 4. EDA Issue Handling

| EDA Issue | Treatment in Script |
|---|---|
| Non-delivered exposure | `claim_eligible_flag = 0`, return and claim fields set to no loss |
| `freight_value` right tail | `freight_value_capped = min(freight_value, 84.52)` |
| `freight_to_price_ratio` right tail | `freight_to_price_ratio_capped = min(ratio, 1.54945)` |
| product size missing rows | category median fill, fallback to global median |
| `product_weight_g = 0` | treated as invalid and category median filled |
| `freight_value = 0` | cannot become a covered return shipping claim |

## 5. Output Summary

| Metric | Value |
|---|---:|
| rows | 112,650 |
| eligible exposures | 110,197 |
| ineligible exposures | 2,453 |
| return requested count | 9,338 |
| return requested rate among eligible | 8.47% |
| return approved count | 8,709 |
| refund without return count | 203 |
| partial refund count | 379 |
| covered claim count | 8,485 |
| covered claim frequency among eligible | 7.70% |
| total gross loss | 164,736.00 |
| total recovery from carrier | 1,623.32 |
| total paid loss | 163,112.68 |
| total net loss | 163,112.68 |
| average paid loss among claims | 19.22 |
| pure premium per eligible exposure | 1.48 |

## 6. Validation Checks

The implementation passed these checks:

```text
rows == 112,650
ineligible_paid_loss_nonzero == 0
ineligible_return_nonzero == 0
paid_loss_positive_without_covered == 0
covered_without_positive_paid_loss == 0
freight_zero_covered == 0
ratio_above_cap_after == 0
freight_above_cap_after == 0
weight_filled_missing == 0
volume_filled_missing == 0
weight_filled_nonpositive == 0
volume_filled_nonpositive == 0
```

## 7. Next Step

下一步进入 baseline pricing：

```text
用 exposure_claims_synthetic.csv 计算：
1. pure premium
2. commercial premium
3. portfolio loss ratio target
4. category / route simple relativities
```
