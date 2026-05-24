# 18 Seller Credibility Build

本文档记录 Phase 3 第一部分 seller credibility pricing 的实现结果。

设计口径见：

```text
project_docs/17_seller_credibility_design.md
```

脚本：

```text
src/build_seller_credibility.py
```

输入：

```text
data/processed/pricing_glm.csv
```

输出：

```text
data/processed/pricing_glm_credibility.csv
data/processed/seller_credibility_summary.csv
data/processed/seller_credibility_summary.json
```

## 1. Credibility Formula

每个 seller 先计算：

```text
seller_observed_ae =
seller_actual_net_loss / seller_glm_expected_loss
```

credibility weight：

```text
Z = n / (n + k)
```

当前参数：

```text
n = seller_eligible_exposures
k = 500
```

raw credibility relativity：

```text
seller_credibility_relativity_raw =
Z * seller_observed_ae + (1 - Z) * 1.0
```

cap：

```text
min relativity = 0.50
max relativity = 2.00
```

portfolio normalization：

```text
normalization_factor =
total_glm_expected_loss / total_pre_normalized_credibility_expected_loss
```

最终：

```text
credibility_expected_loss =
glm_expected_loss * seller_credibility_relativity

credibility_commercial_premium =
credibility_expected_loss / 0.60
```

## 2. Output Validation

| Check | Result |
|---|---:|
| pricing rows | 112,650 |
| unique exposure keys | 112,650 |
| sellers with eligible exposure | 2,970 |
| ineligible credibility expected loss nonzero rows | 0 |
| ineligible credibility premium nonzero rows | 0 |
| portfolio expected loss preserved | yes |

结论：

```text
输出保持 exposure-level pricing 口径：
order_id + order_item_id + seller_id + product_id
```

## 3. Portfolio Result

| Metric | Value |
|---|---:|
| actual total net loss | 163,112.68 |
| GLM expected total loss | 164,831.10 |
| credibility expected total loss | 164,831.10 |
| GLM A/E | 0.990 |
| credibility A/E | 0.990 |
| credibility total commercial premium | 274,718.50 |
| credibility expected loss ratio | 60.00% |
| portfolio expected loss change vs GLM | 0.00% |

说明：

```text
第一版 seller credibility 使用 portfolio normalization。
因此它不改变整体 GLM rate level，而是在 seller 之间重新分配 expected loss。
```

Portfolio normalization 做的事情：

```text
让 seller credibility 只重新分配不同 seller 之间的 expected loss，
暂时不改变整个组合的总 expected loss。
```

如果没有 normalization，seller-level relativity 的上调和下调不一定刚好抵消。

例如：

```text
total_glm_expected_loss = 100,000
total_pre_normalized_credibility_expected_loss = 103,000
```

这会让 seller credibility 同时产生两个效果：

```text
1. 重新分配 seller 之间的风险。
2. 把整体 expected loss 提高 3%。
```

第一版只想保留第 1 个效果，所以使用：

```text
normalization_factor =
total_glm_expected_loss / total_pre_normalized_credibility_expected_loss
```

然后：

```text
seller_credibility_relativity =
seller_credibility_relativity_capped * normalization_factor
```

本次实际结果：

```text
GLM expected total loss = 164,831.10
credibility expected total loss = 164,831.10
portfolio expected loss change vs GLM = 0.00%
```

这说明：

```text
seller credibility 没有改变整体 rate level。
它只改变了不同 seller 的相对价格。
```

Important clarification:

```text
seller credibility shrinkage 不是把小 seller 拉回全组合平均价。
```

更准确地说：

```text
小 seller 的 seller_credibility_relativity 会更接近 1.0，
所以它的 credibility_expected_loss 会更接近自己的 glm_expected_loss。
```

而 `glm_expected_loss` 已经反映了该 exposure 的风险结构：

```text
category
route
cross_state
freight_value
freight_to_price_ratio
weight
volume
estimated_delivery_days
purchase timing
```

因此：

```text
高风险 exposure 的小 seller 仍然会有较高 GLM base price。
低风险 exposure 的小 seller 仍然会有较低 GLM base price。
```

credibility 只是控制：

```text
是否在 GLM base price 之外，
再根据 seller 自身历史 A/E 做额外上调或下调。
```

## 4. Seller Relativity Distribution

最终 seller credibility relativity 分布：

| Metric | Value |
|---|---:|
| count | 2,970 |
| mean | 1.003 |
| std | 0.033 |
| min | 0.845 |
| p01 | 0.914 |
| p05 | 0.955 |
| p25 | 0.992 |
| median | 1.000 |
| p75 | 1.013 |
| p95 | 1.060 |
| p99 | 1.120 |
| max | 1.226 |

Interpretation:

```text
大多数 seller 的 credibility relativity 接近 1。
这是合理的，因为大多数 seller exposure 很少，credibility weight 很低。
只有 exposure 较多且 observed A/E 明显偏离 GLM 的 seller 会获得更明显调整。
```

这里的 relativity 接近 1 表示：

```text
接近 GLM base expected loss。
```

不表示：

```text
接近 portfolio average pure premium。
```

## 5. Seller Risk Tiers

第一版风险层：

| Tier | Sellers |
|---|---:|
| lower_than_glm | 18 |
| near_glm | 2,905 |
| elevated | 47 |
| high | 0 |

解释：

```text
near_glm seller 占绝大多数，说明 credibility shrinkage 起到了稳定作用。
少数 seller 被识别为 lower_than_glm 或 elevated，可用于后续 seller monitoring。
```

## 6. Output Table

核心输出：

```text
data/processed/pricing_glm_credibility.csv
```

新增核心字段：

```text
seller_eligible_exposures
seller_claim_count
seller_actual_net_loss
seller_glm_expected_loss
seller_observed_ae
seller_credibility_weight
seller_credibility_relativity_raw
seller_credibility_relativity_capped
seller_credibility_normalization_factor
seller_credibility_relativity
seller_risk_tier
credibility_expected_loss
credibility_commercial_premium
credibility_expected_loss_ratio_to_glm
credibility_premium_ratio_to_glm
credibility_expected_loss_ratio_to_freight
```

## 7. Why This Matters

Phase 2 GLM 解决的是：

```text
同一个 seller 下，不同品类、路线、运费、商品尺寸的 exposure 应该如何定价？
```

Phase 3 seller credibility 补充的是：

```text
在控制 GLM risk factors 后，某个 seller 的历史损失经验是否持续高于或低于模型预期？
```

这更接近真实运费险定价：

```text
base GLM price + seller experience adjustment
```

## 8. Important Limitation

当前 seller credibility 使用同一批 synthetic claims 做 observed A/E。

因此它是第一版 actuarial mechanism demonstration，不应被解释为真实生产参数。

后续更严谨的做法：

```text
1. 用历史 period 计算 seller relativity。
2. 用 future period 做 backtesting。
3. 测试 k = 250 / 500 / 1000 的敏感性。
4. 对 seller relativity 做稳定性监控。
```
