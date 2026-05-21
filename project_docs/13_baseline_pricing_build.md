# 13 Baseline Pricing Build

本文档记录第一版 baseline pricing 的实现结果。

设计口径见：

```text
project_docs/12_baseline_pricing_design.md
```

脚本：

```text
src/build_baseline_pricing.py
```

输入：

```text
data/processed/exposure_claims_synthetic.csv
```

输出：

```text
data/processed/pricing_baseline.csv
data/processed/pricing_baseline_summary.json
data/processed/pricing_by_category.csv
data/processed/pricing_by_route.csv
data/processed/pricing_by_cross_state.csv
data/processed/pricing_by_seller.csv
```

## 1. Pricing Assumption

第一版使用 portfolio-level baseline price。

目标赔付率：

```text
target_loss_ratio = 60%
```

公式：

```text
portfolio_pure_premium =
total_net_loss / eligible_exposures

portfolio_commercial_premium =
portfolio_pure_premium / target_loss_ratio
```

解释：

```text
纯保费只覆盖预期赔款。
商业保费需要覆盖预期赔款、费用、利润、风险边际和资本成本。
目标赔付率 60% 表示预计赔款占最终保费的 60%。
```

## 2. Portfolio-Level Result

| Metric | Value |
|---|---:|
| rows | 112,650 |
| eligible exposures | 110,197 |
| ineligible exposures | 2,453 |
| covered claim count | 8,485 |
| claim frequency | 7.70% |
| total gross loss | 164,736.00 |
| total recovery from carrier | 1,623.32 |
| total paid loss | 163,112.68 |
| total net loss | 163,112.68 |
| average severity | 19.22 |
| portfolio pure premium | 1.4802 |
| portfolio commercial premium | 2.4670 |
| total commercial premium | 271,854.47 |
| expected loss ratio | 60.00% |

计算关系：

```text
portfolio_pure_premium =
163,112.68 / 110,197
= 1.4802

portfolio_commercial_premium =
1.4802 / 0.60
= 2.4670
```

含义：

```text
在当前 synthetic claims 假设下，每个 eligible exposure 平均预计赔 1.48。
如果目标赔付率是 60%，每个 eligible exposure 平均需要收 2.47。
```

## 3. Exposure-Level Pricing Table

输出：

```text
data/processed/pricing_baseline.csv
```

行数：

```text
112,650
```

新增核心字段：

```text
target_loss_ratio
portfolio_pure_premium
portfolio_commercial_premium
baseline_pure_premium
baseline_commercial_premium
expected_loss
expected_loss_ratio_to_freight
expected_portfolio_loss_ratio
```

第一版规则：

```text
eligible exposure:
baseline_pure_premium = 1.4802
baseline_commercial_premium = 2.4670

ineligible exposure:
baseline_pure_premium = 0
baseline_commercial_premium = 0
```

注意：

```text
这一版没有把 category / route / seller relativity 混入最终 exposure premium。
先用 portfolio average 做稳定 benchmark。
分组 relativity 作为分析输出，给 GLM 前做 sanity check。
```

## 4. Category Pricing Summary

输出：

```text
data/processed/pricing_by_category.csv
```

分组数量：

```text
72 categories
28 categories meet baseline credibility threshold
```

门槛：

```text
category_min_exposure = 500
```

Top credible categories by pure premium:

| Category | Eligible Exposures | Claims | Frequency | Severity | Pure Premium | Relativity | Commercial Premium |
|---|---:|---:|---:|---:|---:|---:|---:|
| office_furniture | 1,668 | 89 | 5.34% | 39.58 | 2.1121 | 1.427 | 3.5202 |
| musical_instruments | 651 | 55 | 8.45% | 22.34 | 1.8877 | 1.275 | 3.1462 |
| small_appliances | 658 | 53 | 8.05% | 22.96 | 1.8491 | 1.249 | 3.0819 |
| luggage_accessories | 1,077 | 82 | 7.61% | 24.10 | 1.8346 | 1.239 | 3.0577 |
| home_construction | 596 | 47 | 7.89% | 23.02 | 1.8150 | 1.226 | 3.0250 |
| electronics | 2,729 | 294 | 10.77% | 16.65 | 1.7941 | 1.212 | 2.9902 |
| health_beauty | 9,465 | 858 | 9.06% | 18.88 | 1.7118 | 1.156 | 2.8529 |
| baby | 2,982 | 247 | 8.28% | 20.37 | 1.6869 | 1.140 | 2.8115 |
| fashion_bags_accessories | 1,985 | 216 | 10.88% | 15.31 | 1.6659 | 1.125 | 2.7764 |
| pet_shop | 1,924 | 165 | 8.58% | 19.11 | 1.6390 | 1.107 | 2.7316 |

Interpretation:

```text
office_furniture 的 frequency 不最高，但 severity 高，所以 pure premium 高。
electronics / fashion_bags_accessories 的 frequency 较高，所以 pure premium 也偏高。
```

## 5. Route Pricing Summary

输出：

```text
data/processed/pricing_by_route.csv
```

分组数量：

```text
412 routes
30 routes meet baseline credibility threshold
```

门槛：

```text
route_min_exposure = 500
```

Top credible routes by pure premium:

| Route | Eligible Exposures | Claims | Frequency | Severity | Pure Premium | Relativity | Commercial Premium |
|---|---:|---:|---:|---:|---:|---:|---:|
| SP_to_MA | 549 | 62 | 11.29% | 36.88 | 4.1655 | 2.814 | 6.9425 |
| SP_to_PA | 765 | 74 | 9.67% | 31.62 | 3.0587 | 2.066 | 5.0978 |
| SP_to_PE | 1,246 | 123 | 9.87% | 27.82 | 2.7465 | 1.856 | 4.5775 |
| SP_to_BA | 2,626 | 277 | 10.55% | 23.36 | 2.4636 | 1.664 | 4.1060 |
| SC_to_RJ | 531 | 52 | 9.79% | 24.79 | 2.4279 | 1.640 | 4.0466 |
| SP_to_MT | 761 | 78 | 10.25% | 23.64 | 2.4226 | 1.637 | 4.0376 |
| SP_to_CE | 1,091 | 96 | 8.80% | 26.54 | 2.3352 | 1.578 | 3.8920 |
| MG_to_RJ | 1,275 | 129 | 10.12% | 22.12 | 2.2380 | 1.512 | 3.7300 |
| RS_to_SP | 749 | 64 | 8.54% | 24.35 | 2.0804 | 1.405 | 3.4673 |
| PR_to_MG | 925 | 77 | 8.32% | 21.84 | 1.8179 | 1.228 | 3.0299 |

Interpretation:

```text
Route relativity 比 category 更分散。
SP_to_MA 的 pure premium 是 portfolio average 的 2.81 倍。
这说明路线是后续 GLM pricing 的强候选 rating factor。
```

## 6. Cross-State Pricing Summary

输出：

```text
data/processed/pricing_by_cross_state.csv
```

| Segment | Eligible Exposures | Claims | Frequency | Severity | Pure Premium | Relativity | Commercial Premium |
|---|---:|---:|---:|---:|---:|---:|---:|
| cross_state = 1 | 70,331 | 5,916 | 8.41% | 22.16 | 1.8644 | 1.260 | 3.1073 |
| cross_state = 0 | 39,866 | 2,569 | 6.44% | 12.45 | 0.8024 | 0.542 | 1.3373 |

Interpretation:

```text
跨州 exposure 的 frequency 和 severity 都高于同州 exposure。
跨州 pure premium 是 portfolio average 的 1.26 倍。
同州 pure premium 是 portfolio average 的 0.54 倍。
```

## 7. Seller Pricing Summary

输出：

```text
data/processed/pricing_by_seller.csv
```

分组数量：

```text
2,970 sellers
236 sellers meet baseline credibility threshold
```

门槛：

```text
seller_min_exposure = 100
```

Top credible sellers by pure premium:

| Seller ID | Eligible Exposures | Claims | Frequency | Severity | Pure Premium | Relativity | Commercial Premium |
|---|---:|---:|---:|---:|---:|---:|---:|
| ca3bd7cd9f149df75950150d010fe4a2 | 135 | 16 | 11.85% | 28.15 | 3.3363 | 2.254 | 5.5606 |
| 59b22a78efb79a4797979612b885db36 | 133 | 12 | 9.02% | 35.19 | 3.1746 | 2.145 | 5.2910 |
| 729f06993dac8e860d4f02d7088ca48a | 113 | 8 | 7.08% | 42.50 | 3.0087 | 2.033 | 5.0145 |
| a1043bafd471dff536d0c462352beb48 | 752 | 57 | 7.58% | 39.09 | 2.9626 | 2.002 | 4.9377 |
| 001cca7ae9ae17fb1caed9dfb1094831 | 234 | 19 | 8.12% | 35.79 | 2.9062 | 1.963 | 4.8437 |

Important caveat:

```text
seller-level relativities are still unstable in baseline pricing.
Even with 100+ exposures, seller experience can be noisy.
Formal seller credibility will be handled in Phase 3.
```

## 8. Validation Checks

The implementation passed these checks:

```text
pricing_baseline rows: 112,650
eligible rows: 110,197
ineligible baseline pure premium nonzero: 0
ineligible baseline commercial premium nonzero: 0
sum expected loss: 163,112.68
sum commercial premium: 271,854.47
expected loss ratio: 60.00%
portfolio pure premium matches pricing table: true
```

## 9. Conclusion

Baseline pricing is complete.

第一版全组合价格：

```text
pure premium: 1.4802
commercial premium: 2.4670
```

关键风险观察：

```text
1. route_state 的 relativity 分散度很高，是后续 GLM 的强候选 rating factor。
2. cross_state_flag 有明显区分度。
3. category 也有风险差异，但一部分差异来自 severity。
4. seller-level 需要 credibility，不能直接用 baseline relativity 上线。
```

下一步：

```text
进入 Phase 2: GLM frequency / severity pricing。
```
