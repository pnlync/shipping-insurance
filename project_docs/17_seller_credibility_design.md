# 17 Seller Credibility Design

本文档定义 Phase 3 第一部分：seller credibility pricing。

目标不是重做 GLM，而是在 Phase 2 的 exposure-level GLM expected loss 之上，加入一层商家经验调整。

暂不做：

```text
XGBoost
SHAP
dashboard
presentation
stress testing
pricing memo
```

## 1. Why Seller Credibility Comes After GLM

Phase 2 GLM 没有把 `seller_id` 直接作为 rating factor。

原因：

```text
seller_id 是高基数字段。
很多 seller 的 exposure 很少，直接入 GLM 会产生不稳定系数。
```

当前数据分布：

| Metric | Value |
|---|---:|
| sellers with eligible exposures | 2,970 |
| eligible exposures | 110,197 |
| median eligible exposures per seller | 8 |
| 75th percentile | 26 |
| 90th percentile | 83 |
| sellers with >= 100 exposures | 236 |
| sellers with >= 500 exposures | 29 |
| max eligible exposures for one seller | 1,996 |

结论：

```text
大多数 seller 自身经验不足。
如果直接按 seller observed loss experience 定价，会过度反应随机波动。
```

因此 seller risk 不应直接塞进 GLM，而应作为 GLM 之后的 credibility adjustment。

## 2. Base Model and Adjustment Layer

Phase 2 给每个 exposure 输出：

```text
glm_expected_loss
glm_commercial_premium
```

Phase 3 seller credibility 输出：

```text
credibility_expected_loss
credibility_commercial_premium
```

关系：

```text
credibility_expected_loss =
glm_expected_loss * seller_credibility_relativity
```

也就是说：

```text
GLM 负责基础风险分类：
category, route, freight ratio, weight, volume, estimated delivery days

seller credibility 负责商家历史经验调整：
seller actual loss vs seller GLM expected loss
```

Important clarification:

```text
小 seller 并不是被拉回全组合统一平均价。
小 seller 是被拉回它自身 exposure mix 对应的 GLM base expected loss。
```

例如：

```text
如果一个小 seller 的订单集中在高风险品类、跨州路线和高运费 exposure，
那么即使 credibility weight 很低，它的价格仍然会接近这些 exposure 的高 GLM base price。

它不会被拉回 portfolio average pure premium。
```

因此这里的 shrinkage target 是：

```text
glm_expected_loss_i
```

不是：

```text
portfolio_pure_premium
```

## 3. Seller Observed Relativity

对每个 seller 计算：

```text
seller_actual_loss = sum(net_loss)
seller_glm_expected_loss = sum(glm_expected_loss)
seller_eligible_exposures = count(claim_eligible_flag == 1)
```

seller observed A/E：

```text
seller_observed_ae =
seller_actual_loss / seller_glm_expected_loss
```

解释：

| seller_observed_ae | Meaning |
|---:|---|
| 1.00 | seller 实际赔款和 GLM 预期接近 |
| > 1.00 | seller 实际赔款高于 GLM 预期，历史经验偏差 |
| < 1.00 | seller 实际赔款低于 GLM 预期，历史经验较好 |

但 observed A/E 不能直接用于定价。

原因：

```text
小 seller 的 observed A/E 很容易被少数 claim 扭曲。
```

## 4. Credibility Weight

第一版使用简单 Bühlmann-style credibility weight：

```text
Z = n / (n + k)
```

其中：

```text
n = seller_eligible_exposures
k = 500
```

解释：

```text
seller exposure 越多，Z 越接近 1，越相信 seller 自己的经验。
seller exposure 越少，Z 越接近 0，越依赖该 seller 具体 exposure mix 下的 GLM base expected loss。
```

例子：

| n | Z = n / (n + 500) | Meaning |
|---:|---:|---|
| 10 | 1.96% | 几乎不相信 seller own experience |
| 100 | 16.67% | 少量参考 seller own experience |
| 500 | 50.00% | seller own experience 和 GLM base 各占一半 |
| 1,000 | 66.67% | 较多相信 seller own experience |
| 2,000 | 80.00% | 大卖家经验有较强权重 |

`k = 500` 是第一版经验参数。

原因：

```text
1. 与 Phase 2 category / route stability threshold 保持一致。
2. 500 exposure 在当前 7.70% claim frequency 下，约对应 38.5 个 expected claims。
3. 只有 29 个 seller 达到 500 exposure，说明该参数不会让大多数 seller 过度跟随自身波动。
```

后续可以对 `k` 做 sensitivity testing：

```text
k = 250
k = 500
k = 1000
```

## 5. Credibility Relativity

Raw credibility relativity：

```text
seller_credibility_relativity_raw =
Z * seller_observed_ae + (1 - Z) * 1.0
```

解释：

```text
1.0 表示不对 GLM base expected loss 做 seller-level 上调或下调。
seller_observed_ae 是 seller 自身历史经验。
Z 决定相信 seller 历史经验的程度。
```

换句话说：

```text
seller_credibility_relativity 接近 1.0
不表示价格接近全组合平均价。

它表示：
credibility_expected_loss 接近 glm_expected_loss。
```

例如：

```text
seller_observed_ae = 1.50
n = 100
Z = 100 / 600 = 16.67%

seller_credibility_relativity_raw =
16.67% * 1.50 + 83.33% * 1.00
= 1.083
```

虽然 observed A/E 是 1.50，但由于 seller exposure 只有 100，最终只上调约 8.3%。

## 6. Capping and Normalization

第一版增加两个风险控制。

### Capping

Raw relativity 先限制在：

```text
min = 0.50
max = 2.00
```

原因：

```text
避免少数极端 seller 历史结果导致过大降价或涨价。
```

### Portfolio Normalization

Capping 后再做 portfolio normalization。

目标：

```text
保持 seller credibility adjustment 主要用于重新分配风险，
不在第一版中改变整体 GLM rate level。
```

换句话说：

```text
整体价格水平不变，只改变不同 seller 之间谁贵一点、谁便宜一点。
```

如果没有 normalization，seller credibility relativity 可能会改变整体 expected loss。

例如：

```text
total_glm_expected_loss = 100,000
total_pre_normalized_credibility_expected_loss = 103,000
```

这表示 seller credibility 不只是在重新分配风险，还把整体 expected loss 提高了 3%。

第一版暂时不希望这样做。

原因：

```text
Phase 2 GLM 已经给出了整体 expected loss level。
Phase 3 seller credibility 第一版只想回答：
在总 expected loss 不变的前提下，哪些 seller 应该相对 GLM 上调或下调？
```

计算：

```text
normalization_factor =
total_glm_expected_loss / total_pre_normalized_credibility_expected_loss
```

如果：

```text
total_glm_expected_loss = 100,000
total_pre_normalized_credibility_expected_loss = 103,000
```

则：

```text
normalization_factor = 100,000 / 103,000 = 0.971
```

最终每个 seller 的 capped relativity 都乘以这个 factor：

```text
seller_credibility_relativity =
seller_credibility_relativity_capped * 0.971
```

最终 seller relativity：

```text
seller_credibility_relativity =
seller_credibility_relativity_capped * normalization_factor
```

最终 expected loss：

```text
credibility_expected_loss =
glm_expected_loss * seller_credibility_relativity
```

这样做的含义：

```text
整体 expected loss 与 GLM 保持一致。
不同 seller 之间的价格被重新分配。
```

简单例子：

| Seller | GLM Expected Loss | Raw/Capped Relativity | Pre-Normalized Expected Loss |
|---|---:|---:|---:|
| A | 50,000 | 1.10 | 55,000 |
| B | 30,000 | 1.00 | 30,000 |
| C | 20,000 | 0.90 | 18,000 |
| Total | 100,000 |  | 103,000 |

normalization factor：

```text
100,000 / 103,000 = 0.971
```

最终：

| Seller | GLM Expected Loss | Final Relativity | Final Expected Loss |
|---|---:|---:|---:|
| A | 50,000 | 1.068 | 53,398 |
| B | 30,000 | 0.971 | 29,126 |
| C | 20,000 | 0.874 | 17,476 |
| Total | 100,000 |  | 100,000 |

注意：

```text
A 仍然比 GLM base price 贵。
C 仍然比 GLM base price 便宜。
但总 expected loss 回到了 GLM 的 100,000。
```

这不是把 seller 拉回 portfolio average。

Portfolio normalization 只约束总和：

```text
sum(credibility_expected_loss) = sum(glm_expected_loss)
```

每个 exposure 仍然是：

```text
credibility_expected_loss_i =
glm_expected_loss_i * seller_credibility_relativity
```

因此基础价格仍然来自 GLM base expected loss，而不是全组合平均价。

为什么在 capping 后做 normalization：

```text
raw relativity -> cap -> portfolio normalization
```

原因：

```text
capping 会改变上调和下调的总量。
比如 raw relativity = 3.50 被 cap 到 2.00，
或者 raw relativity = 0.20 被 cap 到 0.50。

cap 之后，总 expected loss 更不可能自然等于 GLM total。
所以要在 cap 之后再做 normalization。
```

什么时候可以不做 normalization：

```text
如果未来认为 seller credibility 发现了 GLM 整体 rate level 的系统性偏差，
可以不做 normalization，或者只做 partial normalization。
```

当前第一版选择 normalization 的原因：

```text
1. claims 是 synthetic，不是真实理赔。
2. seller observed A/E 和 GLM 使用的是同一批数据。
3. 当前目标是展示 seller credibility mechanism，而不是重新设定整体 rate level。
```

## 7. Premium Formula

沿用 Phase 1 / Phase 2 的目标赔付率：

```text
target_loss_ratio = 60%
```

商业保费：

```text
credibility_commercial_premium =
credibility_expected_loss / target_loss_ratio
```

非 eligible exposure：

```text
credibility_expected_loss = 0
credibility_commercial_premium = 0
```

## 8. Expected Outputs

脚本：

```text
src/build_seller_credibility.py
```

输出：

```text
data/processed/pricing_glm_credibility.csv
data/processed/seller_credibility_summary.csv
data/processed/seller_credibility_summary.json
```

`pricing_glm_credibility.csv` 保留 exposure-level 主键：

```text
order_id
order_item_id
seller_id
product_id
```

新增字段：

```text
seller_eligible_exposures
seller_observed_ae
seller_credibility_weight
seller_credibility_relativity_raw
seller_credibility_relativity_capped
seller_credibility_relativity
credibility_expected_loss
credibility_commercial_premium
```

## 9. Done Criteria

完成标准：

```text
1. pricing_glm_credibility.csv 行数等于 pricing_glm.csv。
2. exposure key 仍唯一。
3. 非 eligible exposure 的 credibility expected loss 和 premium 为 0。
4. seller summary 每个 seller 一行。
5. portfolio expected loss 与 GLM expected loss 保持一致。
6. summary 记录 k、cap、normalization factor、seller relativity 分布。
```
