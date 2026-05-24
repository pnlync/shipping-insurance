# 21 Stress Testing Design

本文档定义 Phase 3 第三部分：stress testing。

目标不是重新训练模型，而是测试当前价格在不利赔付情景下是否还能承受。

## 1. What Stress Testing Means

Backtesting / monitoring 问的是：

```text
在当前观察到的 actual loss 下，价格是否合理？
```

Stress testing 问的是：

```text
如果未来赔付频率或赔款金额恶化，当前价格还能不能承受？
```

两者区别：

| Item | Backtesting / Monitoring | Stress Testing |
|---|---|---|
| Core question | 当前表现如何？ | 不利情景下会怎样？ |
| Loss basis | observed actual loss | stressed actual loss |
| Purpose | 找出低估/高估 segment | 测试资本、费率和风控缓冲 |
| Output | A/E, loss ratio | stressed loss ratio, premium adequacy |

在保险定价中，只看当前 loss ratio 不够。

原因：

```text
未来退货率可能上升。
物流成本可能上涨。
高风险 seller 或路线可能恶化。
大促、平台规则、物流 SLA 变化都可能改变赔付水平。
```

Stress testing 用来回答：

```text
如果这些不利变化发生，当前商业保费是否仍然能覆盖赔款和目标赔付率？
```

## 2. Base Loss and Stressed Loss

Base actual loss：

```text
base_actual_loss = sum(net_loss)
```

Frequency stress：

```text
stressed_loss = base_actual_loss * (1 + frequency_stress)
```

Severity stress：

```text
stressed_loss = base_actual_loss * (1 + severity_stress)
```

Combined stress：

```text
stressed_loss =
base_actual_loss
* (1 + frequency_stress)
* (1 + severity_stress)
```

解释：

```text
frequency stress 表示赔付件数变多。
severity stress 表示每笔赔款金额变高。
combined stress 表示赔付件数和单笔赔款同时变坏。
```

## 3. Pricing Bases Tested

本次同时测试三套商业保费：

```text
baseline_commercial_premium
glm_commercial_premium
credibility_commercial_premium
```

stress loss ratio：

```text
stressed_loss_ratio =
stressed_actual_loss / commercial_premium
```

目标赔付率：

```text
target_loss_ratio = 60%
```

判断：

| Stressed Loss Ratio | Interpretation |
|---:|---|
| <= 60% | 仍符合目标赔付率 |
| 60% - 80% | 超过目标，但仍有一定费用/利润缓冲 |
| 80% - 100% | 压力较高，费用和利润空间明显被压缩 |
| > 100% | 赔款已超过商业保费，风险不可接受 |

## 4. Portfolio Scenarios

第一版 portfolio stress scenarios：

| Scenario | Frequency Multiplier | Severity Multiplier | Meaning |
|---|---:|---:|---|
| base_observed | 1.00 | 1.00 | 当前 observed actual loss |
| frequency_plus_10 | 1.10 | 1.00 | claim frequency 上升 10% |
| frequency_plus_20 | 1.20 | 1.00 | claim frequency 上升 20% |
| severity_plus_10 | 1.00 | 1.10 | severity 上升 10% |
| severity_plus_20 | 1.00 | 1.20 | severity 上升 20% |
| combined_10_10 | 1.10 | 1.10 | frequency 和 severity 同时上升 10% |
| combined_20_20 | 1.20 | 1.20 | frequency 和 severity 同时上升 20% |

## 5. Adverse Segment Scenarios

Backtesting 已经识别出一些高 loss ratio segment。

因此 stress testing 还应测试局部恶化：

```text
elevated seller tier stress
top high loss ratio categories stress
top high loss ratio routes stress
```

局部 stress 的含义：

```text
不是整个组合都变坏，
而是某些高风险 segment 进一步恶化。
```

第一版 segment stress：

```text
elevated seller tier: frequency +20%, severity +20%
top 5 high loss ratio categories: frequency +15%, severity +15%
top 5 high loss ratio routes: frequency +15%, severity +15%
```

这些 segment 来自：

```text
data/processed/backtest_by_seller_tier.csv
data/processed/backtest_by_category.csv
data/processed/backtest_by_route.csv
```

## 6. Expected Outputs

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
```

输出：

```text
data/processed/stress_testing_summary.json
data/processed/stress_test_portfolio.csv
data/processed/stress_test_by_seller_tier.csv
data/processed/stress_test_watchlist_segments.csv
```

核心字段：

```text
scenario
frequency_multiplier
severity_multiplier
portfolio_base_actual_loss
segment_base_actual_loss
segment_stressed_actual_loss
portfolio_stressed_actual_loss
baseline_stressed_loss_ratio
glm_stressed_loss_ratio
credibility_stressed_loss_ratio
credibility_loss_ratio_vs_target
premium_adequacy_flag
```

字段说明：

```text
portfolio_stressed_actual_loss 用于计算组合层 stressed loss ratio。
segment_stressed_actual_loss 只描述被 stress 的局部 segment 损失。
```

对于 portfolio scenarios：

```text
segment_base_actual_loss = portfolio_base_actual_loss
segment_stressed_actual_loss = portfolio_stressed_actual_loss
```

对于 seller tier / category / route 局部 stress：

```text
segment_* 字段描述被 stress 的 segment。
portfolio_* 字段描述局部 stress 后的组合整体损失。
```

## 7. Done Criteria

完成标准：

```text
1. stress testing 只使用 eligible exposure。
2. base_observed scenario 与 loss ratio backtesting 的 portfolio result 对齐。
3. portfolio 和 selected segment scenarios 都输出。
4. summary 识别最不利 scenario 和是否超过 target loss ratio。
5. 文档解释 stress testing 和 backtesting 的区别。
```
