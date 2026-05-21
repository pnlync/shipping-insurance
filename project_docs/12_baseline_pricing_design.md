# 12 Baseline Pricing Design

本文档定义第一版 baseline pricing 的计算口径。

Baseline pricing 的目标不是建立最终模型，而是在 GLM 之前先建立一个清晰、可解释、可复现的定价基准。

## 1. Why Baseline Pricing Comes Next

当前项目已经完成：

```text
exposure table
synthetic returns layer
synthetic claims layer
```

现在每个 exposure 已经有：

```text
covered_claim_flag
paid_loss
net_loss
claim_eligible_flag
```

因此可以先做最基础的精算定价：

```text
总净赔款 / eligible exposures = portfolio pure premium
portfolio pure premium / target loss ratio = portfolio commercial premium
```

这一步的意义：

```text
1. 给项目一个最简单的价格基准。
2. 检查 synthetic claims 的赔付水平是否合理。
3. 给后续 GLM pricing 提供 benchmark。
4. 先用分组汇总观察 category、route、seller 的风险差异。
```

## 2. Input

输入表：

```text
data/processed/exposure_claims_synthetic.csv
```

核心字段：

```text
claim_eligible_flag
covered_claim_flag
net_loss
paid_loss
product_category_name_english
route_state
cross_state_flag
seller_id
freight_value
freight_value_capped
```

## 3. Pricing Population

第一版定价只以 eligible exposures 计算平均成本：

```text
claim_eligible_flag == 1
```

非 eligible exposure：

```text
不参与 pure premium 分母。
不参与 claim frequency 分母。
exposure-level baseline premium 可以设为 0。
```

原因：

```text
非 delivered exposure 不属于第一版可完整观察的退货运费险风险暴露。
```

## 4. Portfolio-Level Metrics

Portfolio-level 是全组合基准。

计算：

```text
eligible_exposures = count(claim_eligible_flag == 1)
covered_claim_count = sum(covered_claim_flag)
total_net_loss = sum(net_loss)
```

频率：

```text
claim_frequency =
covered_claim_count / eligible_exposures
```

严重度：

```text
average_severity =
total_net_loss / covered_claim_count
```

纯保费：

```text
portfolio_pure_premium =
total_net_loss / eligible_exposures
```

当前 synthetic claims 已经给出大致结果：

```text
eligible exposures: 110,197
covered claim count: 8,485
claim frequency among eligible: 7.70%
total net loss: 163,112.68
average paid loss among claims: 19.22
pure premium per eligible exposure: 1.48
```

## 5. Pure Premium vs Commercial Premium

纯保费只覆盖预期赔款：

```text
pure premium = expected claim cost
```

它不覆盖：

```text
运营费用
获客成本
理赔处理成本
平台服务费
利润
风险边际
资本成本
税费
```

商业保费是实际收费，需要高于纯保费。

第一版使用目标赔付率反推：

```text
target_loss_ratio = expected_loss / commercial_premium
```

所以：

```text
commercial_premium = expected_loss / target_loss_ratio
```

在 exposure level：

```text
expected_loss = pure_premium
```

因此：

```text
commercial_premium = pure_premium / target_loss_ratio
```

第一版假设：

```text
target_loss_ratio = 60%
```

如果：

```text
pure premium = 1.48
```

则：

```text
commercial premium = 1.48 / 0.60 = 2.47
```

含义：

```text
每收 2.47，预计赔 1.48。
预计赔付率约为 60%。
剩余 40% 用于费用、利润、风险边际等。
```

## 6. Why Not Add 40%

不要写成：

```text
commercial_premium = pure_premium * 1.4
```

因为如果：

```text
1.48 * 1.4 = 2.07
```

则：

```text
loss_ratio = 1.48 / 2.07 = 71.5%
```

这不是 60% 目标赔付率。

目标赔付率法是反推最终保费：

```text
commercial_premium = pure_premium / 0.60
```

## 7. Group-Level Relativities

除了 portfolio average，还需要看不同风险组的差异。

第一版输出这些分组：

```text
category
route_state
cross_state_flag
seller_id
```

每个分组计算：

```text
eligible_exposures
covered_claim_count
claim_frequency
total_net_loss
average_severity
pure_premium
relativity
commercial_premium
```

其中：

```text
relativity =
group_pure_premium / portfolio_pure_premium
```

例子：

```text
portfolio_pure_premium = 1.48
category_pure_premium = 2.22

category_relativity = 2.22 / 1.48 = 1.50
```

含义：

```text
这个 category 的风险成本约为组合平均的 1.5 倍。
```

## 8. Small Sample Treatment

分组 relativity 容易被小样本扭曲。

第一版使用最低 exposure 门槛：

```text
category_min_exposure = 500
route_min_exposure = 500
seller_min_exposure = 100
```

低于门槛的分组：

```text
credibility_flag = insufficient
不建议直接作为定价因子。
仅用于观察。
```

达到门槛的分组：

```text
credibility_flag = credible_for_baseline
可以作为 baseline relativity 观察。
```

注意：

```text
这里还不是正式 credibility model。
正式 seller credibility 会在 Phase 3 做。
```

## 9. Exposure-Level Baseline Pricing Table

建议输出：

```text
data/processed/pricing_baseline.csv
```

该表仍然保持 exposure level。

新增字段：

```text
portfolio_pure_premium
portfolio_commercial_premium
baseline_pure_premium
baseline_commercial_premium
target_loss_ratio
expected_loss
expected_loss_ratio_to_freight
```

第一版 exposure-level price 使用 portfolio average：

```text
baseline_pure_premium = portfolio_pure_premium
baseline_commercial_premium = portfolio_commercial_premium
```

非 eligible exposure：

```text
baseline_pure_premium = 0
baseline_commercial_premium = 0
```

原因：

```text
本阶段先建立稳定 benchmark。
category / route / seller relativities 先输出为分析表，不直接混合进最终商业保费。
```

## 10. Outputs

建议新增脚本：

```text
src/build_baseline_pricing.py
```

建议输出：

```text
data/processed/pricing_baseline.csv
data/processed/pricing_baseline_summary.json
data/processed/pricing_by_category.csv
data/processed/pricing_by_route.csv
data/processed/pricing_by_cross_state.csv
data/processed/pricing_by_seller.csv
```

## 11. Done Criteria

Baseline pricing 完成标准：

```text
1. portfolio pure premium 和 synthetic claims summary 一致。
2. commercial premium 按 target_loss_ratio 正确反推。
3. exposure-level pricing table 行数等于 exposure_claims_synthetic.csv。
4. 非 eligible exposure 的 baseline premium 为 0。
5. 分组表包含 frequency、severity、pure premium、relativity、commercial premium。
6. 小样本分组有 credibility_flag。
7. 输出 summary 记录 target_loss_ratio、总保费、预期赔付率。
```
