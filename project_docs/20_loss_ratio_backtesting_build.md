# 20 Loss Ratio Backtesting Build

本文档记录 Phase 3 第二部分 loss ratio backtesting / monitoring 的实现结果。

设计口径见：

```text
project_docs/19_loss_ratio_backtesting_design.md
```

脚本：

```text
src/build_loss_ratio_backtesting.py
```

输入：

```text
data/processed/pricing_glm_credibility.csv
```

输出：

```text
data/processed/loss_ratio_backtesting_summary.json
data/processed/backtest_by_month.csv
data/processed/backtest_by_category.csv
data/processed/backtest_by_route.csv
data/processed/backtest_by_seller_tier.csv
data/processed/backtest_by_seller.csv
```

## 1. Concept Recap

Loss ratio backtesting / monitoring 回答的问题是：

```text
实际赔款和模型预计赔款是否接近？
实际赔款占商业保费的比例是否接近目标赔付率？
哪些 segment 被低估或高估？
```

核心指标：

```text
A/E = actual_loss / expected_loss
Loss Ratio = actual_loss / commercial_premium
```

解释：

| Metric | Good / Bad Signal |
|---|---|
| A/E close to 1 | 实际赔款接近预计赔款 |
| A/E above 1 | 实际赔款高于预计，可能低估风险 |
| A/E below 1 | 实际赔款低于预计，可能高估风险 |
| loss ratio close to 60% | 符合当前目标赔付率 |
| loss ratio above 60% | 赔付高于目标，可能保费不足 |
| loss ratio below 60% | 赔付低于目标，可能价格偏保守 |

当前版本仍是 synthetic-data monitoring framework，不是真实 out-of-time production backtest。

## 2. Pricing Bases Compared

本次同时比较三套口径：

```text
baseline
GLM
GLM + seller credibility
```

每套口径输出：

```text
expected_loss
commercial_premium
A/E
loss_ratio
loss_ratio_vs_target
```

当前 target loss ratio：

```text
60%
```

因此：

```text
loss_ratio = A/E * 60%
```

## 3. Portfolio Result

组合层结果：

| Metric | Baseline | GLM | Credibility |
|---|---:|---:|---:|
| actual loss | 163,112.68 | 163,112.68 | 163,112.68 |
| expected loss | 163,112.68 | 164,831.10 | 164,831.10 |
| A/E | 1.000 | 0.990 | 0.990 |
| loss ratio | 60.00% | 59.37% | 59.37% |

Interpretation:

```text
Baseline 的组合层 A/E 天然等于 1，因为 baseline pure premium 直接来自总赔款 / eligible exposures。
GLM 和 credibility 的组合层 A/E 为 0.990，说明整体 expected loss 略高于 actual loss。
Credibility 使用 portfolio normalization，因此组合层 expected loss 与 GLM 一致。
```

## 4. Output Shapes

| Output | Rows | Meaning |
|---|---:|---|
| backtest_by_month.csv | 12 | 按 purchase_month 监控 |
| backtest_by_category.csv | 72 | 按 product_category_name_english 监控 |
| backtest_by_route.csv | 412 | 按 eligible route_state 监控 |
| backtest_by_seller_tier.csv | 3 | 按 seller_risk_tier 监控 |
| backtest_by_seller.csv | 2,970 | 按 seller_id 监控 |

所有 backtest 输出只使用：

```text
claim_eligible_flag == 1
```

## 5. Seller Tier Monitoring

| Seller Risk Tier | Eligible Exposures | Actual Loss | GLM A/E | Credibility A/E | GLM Loss Ratio | Credibility Loss Ratio |
|---|---:|---:|---:|---:|---:|---:|
| near_glm | 97,083 | 142,863.48 | 0.968 | 0.972 | 58.10% | 58.31% |
| elevated | 8,179 | 15,639.22 | 1.555 | 1.359 | 93.32% | 81.53% |
| lower_than_glm | 4,935 | 4,609.98 | 0.636 | 0.729 | 38.18% | 43.73% |

Interpretation:

```text
elevated seller tier 在 GLM 下 A/E 很高，说明这组 seller 实际赔款明显高于 GLM 预期。
加入 seller credibility 后，A/E 从 1.555 降到 1.359，loss ratio 从 93.32% 降到 81.53%。
这说明 seller credibility 对 elevated seller 的风险识别有改善，但仍未完全校准到 1。
```

对于 lower_than_glm：

```text
GLM A/E = 0.636，说明 GLM 对该 tier 偏保守。
credibility 后 A/E = 0.729，更接近 1，但仍偏保守。
```

这是合理的，因为 seller credibility 使用 shrinkage，不会让 seller-level adjustment 过度跟随 observed experience。

## 6. Highest Loss Ratio Segments

按 credibility loss ratio 看，credible category 中较高的 segment：

| Category | Eligible Exposures | Credibility A/E | Credibility Loss Ratio |
|---|---:|---:|---:|
| consoles_games | 1,089 | 1.090 | 65.37% |
| construction_tools_construction | 916 | 1.075 | 64.53% |
| books_general_interest | 537 | 1.045 | 62.70% |
| garden_tools | 4,268 | 1.027 | 61.62% |
| health_beauty | 9,465 | 1.025 | 61.48% |

按 credibility loss ratio 看，credible route 中较高的 segment：

| Route | Eligible Exposures | Credibility A/E | Credibility Loss Ratio |
|---|---:|---:|---:|
| SC_to_RJ | 531 | 1.097 | 65.81% |
| PR_to_RS | 685 | 1.086 | 65.19% |
| SP_to_PA | 765 | 1.081 | 64.87% |
| RS_to_SP | 749 | 1.074 | 64.41% |
| PR_to_PR | 805 | 1.055 | 63.28% |

Interpretation:

```text
这些 segment 的 loss ratio 高于 60% 目标，说明当前 credibility pricing 对它们仍可能略低。
下一步可以在 stress testing 或 pricing memo 中标记为 monitoring watchlist。
```

## 7. Seller-Level Monitoring

`backtest_by_seller.csv` 用于 seller-level monitoring。

输出包括：

```text
seller_id
eligible_exposures
actual_loss
baseline_ae
glm_ae
credibility_ae
baseline_loss_ratio
glm_loss_ratio
credibility_loss_ratio
credibility_expected_loss_change_vs_glm
```

注意：

```text
seller-level 表中小样本 seller 很多。
解读时必须同时看 eligible_exposures。
```

第一版 summary 中 top seller high loss ratio 使用：

```text
min_exposures = 100
```

原因：

```text
避免把只有几单的小 seller 误读为稳定高风险。
```

## 8. Validation

关键验证：

```text
portfolio_actual_loss = 163,112.68
portfolio_baseline_expected_loss = 163,112.68
portfolio_glm_expected_loss = 164,831.10
portfolio_credibility_expected_loss = 164,831.10
credibility_expected_loss_matches_glm = true
credibility_loss_ratio_equals_target_times_ae = true
```

说明：

```text
输出与 pricing_glm_credibility.csv 对齐。
loss ratio 和 A/E 的关系符合公式：
loss_ratio = A/E * target_loss_ratio
```

## 9. Next Step

下一步建议：

```text
stress testing
```

原因：

```text
backtesting 已经识别出高 loss ratio 的 category / route / seller tier。
stress testing 可以检查当 claim frequency 或 severity 上升时，当前保费是否还能承受。
```
