# 19 Loss Ratio Backtesting Design

本文档定义 Phase 3 第二部分：loss ratio backtesting / monitoring。

目标不是重新训练模型，而是检查现有三套价格口径在不同 segment 上是否合理。

当前可比较的价格口径：

```text
1. baseline pricing
2. GLM pricing
3. GLM + seller credibility pricing
```

## 1. What Loss Ratio Backtesting Means

保险定价里，模型输出的不是最终答案。

定价后必须持续问：

```text
我们预计会赔多少？
实际赔了多少？
收的保费是否足够？
哪些 segment 被低估或高估？
```

这就是 loss ratio backtesting / monitoring。

在本项目中：

```text
backtesting = 用已经生成的 synthetic actual losses 检查不同 pricing basis 的表现。
monitoring = 按月份、品类、路线、seller tier、seller 持续观察 A/E 和 loss ratio。
```

严格说，当前版本还不是真实生产意义上的 out-of-time backtest。

原因：

```text
1. claims 是 synthetic。
2. seller credibility 使用同一批 data 计算 observed A/E。
3. 没有真实历史期 / 未来期切分。
```

所以当前 Phase 3 的定位是：

```text
建立 backtesting / monitoring 框架和输出口径。
```

后续如果有真实数据，应升级为：

```text
用历史 period 建模和定价，
用未来 period 检查实际 loss ratio。
```

## 2. Actual Loss, Expected Loss, Premium

Actual loss 是真实或 synthetic 观察到的赔款：

```text
actual_loss = sum(net_loss)
```

Expected loss 是某套定价方法预计会赔的钱：

```text
baseline_expected_loss = sum(baseline_pure_premium)
glm_expected_loss = sum(glm_expected_loss)
credibility_expected_loss = sum(credibility_expected_loss)
```

Commercial premium 是实际应收保费：

```text
baseline_commercial_premium = sum(baseline_commercial_premium)
glm_commercial_premium = sum(glm_commercial_premium)
credibility_commercial_premium = sum(credibility_commercial_premium)
```

当前目标赔付率：

```text
target_loss_ratio = 60%
```

因此：

```text
commercial_premium = expected_loss / 0.60
```

## 3. A/E Ratio

A/E 是：

```text
Actual / Expected
```

公式：

```text
ae_ratio = actual_loss / expected_loss
```

解释：

|     A/E | Meaning |
|--------:|---|
|    1.00 | 实际赔款和预计赔款一致 |
| \> 1.00 | 实际赔款高于预计，模型低估风险 |
|  < 1.00 | 实际赔款低于预计，模型高估风险 |

例如：

```text
expected_loss = 10,000
actual_loss = 12,000
A/E = 1.20
```

含义：

```text
这个 segment 实际赔款比模型预期高 20%，可能被低估。
```

## 4. Loss Ratio

Loss ratio 是：

```text
Actual Loss / Commercial Premium
```

公式：

```text
loss_ratio = actual_loss / commercial_premium
```

它回答的是：

```text
收进来的保费中，有多少比例被赔款吃掉？
```

如果目标赔付率是 60%，则：

```text
loss_ratio < 60%: 赔付表现好于目标
loss_ratio = 60%: 符合目标
loss_ratio > 60%: 赔付高于目标，可能保费不足
```

因为当前：

```text
commercial_premium = expected_loss / 0.60
```

所以：

```text
loss_ratio = actual_loss / commercial_premium
           = actual_loss / (expected_loss / 0.60)
           = A/E * 0.60
```

例如：

```text
A/E = 1.20
loss_ratio = 1.20 * 60% = 72%
```

含义：

```text
这个 segment 的实际赔付率是 72%，高于 60% 目标。
```

## 5. Why Compare Baseline, GLM, and Credibility

Baseline pricing：

```text
所有 eligible exposure 使用同一个 portfolio average pure premium。
```

它回答：

```text
如果不做风险区分，表现怎么样？
```

GLM pricing：

```text
按 category、route、freight、weight、volume 等报价时已知变量区分风险。
```

它回答：

```text
风险因子是否改善 segment-level adequacy？
```

GLM + seller credibility：

```text
在 GLM base expected loss 上，再加入 seller-level observed A/E 的 credibility adjustment。
```

它回答：

```text
seller 历史经验调整是否改善 seller-level adequacy？
```

理想情况：

```text
1. 组合层 A/E 接近 1。
2. 重要 segment 的 A/E 不应系统性偏高或偏低。
3. 高风险 segment 的 commercial premium 应相应更高。
4. seller credibility 应减少 seller-level A/E 的极端偏离，但不能过度反应小样本。
```

## 6. Monitoring Dimensions

第一版输出这些维度：

```text
purchase_month
product_category_name_english
route_state
seller_risk_tier
seller_id
```

原因：

| Dimension | Why It Matters |
|---|---|
| purchase_month | 检查季节性和时间稳定性 |
| product_category_name_english | 检查品类 rate adequacy |
| route_state | 检查路线 rate adequacy |
| seller_risk_tier | 检查 credibility 分层是否合理 |
| seller_id | 支持 seller-level monitoring 和后续风控 |

## 7. Expected Outputs

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

每个输出都应包含：

```text
eligible_exposures
covered_claim_count
actual_loss
baseline_expected_loss
glm_expected_loss
credibility_expected_loss
baseline_commercial_premium
glm_commercial_premium
credibility_commercial_premium
baseline_ae
glm_ae
credibility_ae
baseline_loss_ratio
glm_loss_ratio
credibility_loss_ratio
```

## 8. Done Criteria

完成标准：

```text
1. 所有 backtest 只使用 eligible exposure。
2. portfolio-level actual loss 与 pricing_glm_credibility.csv 对齐。
3. baseline / GLM / credibility 三套 A/E 和 loss ratio 都输出。
4. 各 segment 输出有 exposure count，避免误读小样本。
5. summary JSON 记录最差 A/E、最高 loss ratio、整体组合表现。
```
