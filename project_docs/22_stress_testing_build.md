# 22 Stress Testing Build

本文档记录 Phase 3 第三部分 stress testing 的实现结果。

设计口径见：

```text
project_docs/21_stress_testing_design.md
```

脚本：

```text
src/build_stress_testing.py
```

输入：

```text
data/processed/pricing_glm_credibility.csv
data/processed/backtest_by_category.csv
data/processed/backtest_by_route.csv
data/processed/backtest_by_seller_tier.csv
data/processed/loss_ratio_backtesting_summary.json
```

输出：

```text
data/processed/stress_testing_summary.json
data/processed/stress_test_portfolio.csv
data/processed/stress_test_by_seller_tier.csv
data/processed/stress_test_watchlist_segments.csv
```

## 1. Concept Recap

Backtesting 回答：

```text
当前 observed actual loss 下，价格表现如何？
```

Stress testing 回答：

```text
如果未来 claim frequency 或 severity 恶化，当前商业保费还能否承受？
```

当前 stress testing 不重新训练模型。

它使用现有商业保费作为 denominator：

```text
baseline_commercial_premium
glm_commercial_premium
credibility_commercial_premium
```

并将 actual loss 按情景放大：

```text
stressed_actual_loss =
actual_loss * frequency_multiplier * severity_multiplier
```

核心指标：

```text
stressed_loss_ratio =
stressed_actual_loss / commercial_premium
```

输出字段中需要区分两个层次：

```text
segment_base_actual_loss / segment_stressed_actual_loss:
被 stress 的局部 segment 损失。

portfolio_base_actual_loss / portfolio_stressed_actual_loss:
局部 stress 传导后的组合整体损失。
```

stressed loss ratio 使用：

```text
portfolio_stressed_actual_loss / commercial_premium
```

原因：

```text
stress testing 的主要问题是：
局部或整体不利情景发生后，整个组合的商业保费是否还能承受。
```

## 2. Adequacy Flags

第一版使用这些解释标签：

| Stressed Loss Ratio | Flag | Meaning |
|---:|---|---|
| <= 60% | within_target | 仍符合目标赔付率 |
| 60% - 80% | above_target | 超过目标，但仍有一定缓冲 |
| 80% - 100% | high_pressure | 压力较高，费用和利润空间被明显压缩 |
| > 100% | premium_inadequate | 赔款超过商业保费 |

当前 target loss ratio：

```text
60%
```

## 3. Portfolio Stress Result

使用 credibility pricing 口径看组合层压力：

| Scenario | Loss Multiplier | Credibility Stressed Loss Ratio | Flag |
|---|---:|---:|---|
| base_observed | 1.00 | 59.37% | within_target |
| frequency_plus_10 | 1.10 | 65.31% | above_target |
| frequency_plus_20 | 1.20 | 71.25% | above_target |
| severity_plus_10 | 1.10 | 65.31% | above_target |
| severity_plus_20 | 1.20 | 71.25% | above_target |
| combined_10_10 | 1.21 | 71.84% | above_target |
| combined_20_20 | 1.44 | 85.50% | high_pressure |

Interpretation:

```text
当前 base observed loss ratio 为 59.37%，略低于 60% 目标。
单独 frequency +10% 或 severity +10% 会把 loss ratio 推到 65.31%，超过目标。
frequency 和 severity 同时 +20% 时，loss ratio 达到 85.50%，进入 high_pressure。
```

这说明：

```text
当前保费对温和压力仍有一定承受力，
但对 frequency 和 severity 同时恶化比较敏感。
```

## 4. Seller Tier Stress

局部 stress：

```text
only one seller_risk_tier receives frequency +20% and severity +20%
```

结果：

| Stressed Tier | Portfolio Stressed Loss Ratio | Flag |
|---|---:|---|
| near_glm | 82.26% | high_pressure |
| elevated | 61.88% | above_target |
| lower_than_glm | 60.11% | above_target |

Interpretation:

```text
near_glm tier 不是单位风险最高的 tier，但它 exposure volume 最大。
因此只 stress near_glm 时，对组合层 loss ratio 的影响最大。
```

这点很重要：

```text
压力测试不能只看高风险 segment。
还要看高体量 segment。
```

elevated tier 的 base loss ratio 高，但体量较小。

因此：

```text
elevated tier 是 rate adequacy / underwriting watchlist。
near_glm tier 是 portfolio volume stress 的关键来源。
```

## 5. Watchlist Segment Stress

watchlist 来自 loss ratio backtesting：

```text
top 5 high loss ratio categories with eligible_exposures >= 500
top 5 high loss ratio routes with eligible_exposures >= 500
```

局部 stress：

```text
only selected category or route receives frequency +15% and severity +15%
```

最高的 watchlist stress scenarios：

| Segment | Value | Portfolio Stressed Loss Ratio | Flag |
|---|---|---:|---|
| category | health_beauty | 61.28% | above_target |
| category | garden_tools | 60.13% | above_target |
| route | SP_to_PA | 59.65% | within_target |
| category | consoles_games | 59.56% | within_target |
| route | RS_to_SP | 59.56% | within_target |

Interpretation:

```text
watchlist category / route stress 对组合层影响相对温和。
health_beauty 和 garden_tools 由于 exposure 规模较大，局部恶化能把组合 loss ratio 推过 60%。
```

## 6. Validation

关键验证：

```text
base credibility loss ratio = 59.3745%
backtesting credibility loss ratio = 59.3745%
base scenario matches backtesting = true
combined_20_20 multiplier = 1.44
```

说明：

```text
stress testing 的 base_observed scenario 与 loss ratio backtesting 对齐。
combined_20_20 正确使用 1.20 * 1.20 = 1.44 的 total loss multiplier。
```

## 7. Limitations

当前 stress testing 是第一版 deterministic scenario testing。

限制：

```text
1. 使用 synthetic claims，不是真实赔付。
2. frequency / severity stress 是固定比例，不是随机模拟。
3. 没有考虑 claim correlation、极端尾部事件或物流成本通胀分布。
4. 没有单独模拟 expense ratio、capital cost 或 reinsurance。
```

后续可扩展：

```text
1. Monte Carlo stress testing。
2. 对 high-risk routes 设置更高 severity shock。
3. 对 peak season month 设置 frequency shock。
4. 将 stress result 转化为 underwriting rule 或 rate action。
```
