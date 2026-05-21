# 16 GLM Pricing Explanation

本文档解释 Phase 2 GLM pricing 中容易混淆的概念：

```text
为什么用 Binomial GLM with logit link
为什么同时读取 claims 和 baseline pricing
为什么低 exposure 类别合并为 Other
validation 在验证什么
calibration 在检查什么
AUC、Brier、MAE、RMSE、A/E 是什么意思
```

## 1. Why Binomial GLM with Logit Link for Frequency

Frequency model 的目标变量是：

```text
covered_claim_flag
```

它只有两个值：

```text
0 = 没有 covered claim
1 = 有 covered claim
```

因此这是一个二元结果，不是连续金额，也不是每行多个 claim count。

Binomial GLM 适合建模这种 0/1 事件：

```text
covered_claim_flag ~ Binomial(probability = p)
```

模型输出的是：

```text
p = P(covered_claim_flag = 1)
```

也就是每个 exposure 的赔付发生概率。

Logit link 的作用是把任意线性打分转换成 0 到 1 之间的概率：

```text
logit(p) = log(p / (1 - p))
p = 1 / (1 + exp(-linear_score))
```

这样模型不会预测出负概率或大于 100% 的概率。

选择它的原因：

```text
1. covered_claim_flag 是 0/1 target。
2. 输出可以直接解释为 claim probability。
3. 系数可以转成 odds relativity，适合解释 rating factors。
4. 这是保险 frequency modeling 的标准透明基准之一。
5. 比 XGBoost 更适合作为第一版可解释费率模型。
```

后续是否需要换：

```text
短期不需要换。
```

原因：

```text
Phase 2 的目标是建立可解释、可复现、可审计的 GLM pricing baseline。
Binomial-logit 正好对应当前 exposure-level 0/1 covered claim 标签。
```

未来可能比较的替代模型：

| Alternative | When It May Be Useful |
|---|---|
| Poisson GLM with log link | 如果数据聚合到 group level，用 claim count / exposure 建模 |
| Complementary log-log GLM | 如果事件非常稀有，并且更像 hazard / time-to-event |
| Tweedie GLM | 如果直接建 pure premium，允许大量 0 和右尾正赔款 |
| XGBoost / LightGBM | Phase 4 challenger，用于排序能力和非线性提升 |

当前不切换的原因：

```text
现在每行 exposure 最多一个 covered claim flag。
Binomial-logit 的业务含义最直接。
```

## 2. Why Read Both Claims and Baseline Pricing

GLM 脚本读取：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/pricing_baseline.csv
```

两张表的用途不同。

`exposure_claims_synthetic.csv` 是模型训练主表：

```text
features:
product_category_name_english
route_state
cross_state_flag
price
freight_value_capped
...

targets:
covered_claim_flag
net_loss
```

它用于：

```text
1. 训练 frequency model。
2. 训练 severity model。
3. 生成 GLM expected loss。
```

`pricing_baseline.csv` 是对照基准：

```text
baseline_pure_premium
baseline_commercial_premium
```

它用于：

```text
1. 在 pricing_glm.csv 中保留 baseline price。
2. 对比 GLM expected loss 和 baseline expected loss。
3. 计算 glm_expected_loss_ratio_to_baseline。
4. 让面试展示能说明：GLM 不是孤立结果，而是在 baseline 之上重新分配风险。
```

重要：

```text
baseline_pure_premium 没有作为 GLM feature 输入模型。
```

代码是在 GLM prediction 完成之后才 merge baseline pricing。

这不会造成 feature leakage。

## 3. Why Merge Low-Exposure Categories and Routes into Other

当前规则：

```text
product_category_name_english exposure count < 500 -> Other
route_state exposure count < 500 -> Other
```

目的：

```text
避免 GLM 给样本很少的 category / route 估出不稳定系数。
```

例如某条 route 只有 20 个 exposure：

```text
0 claims -> observed frequency = 0%
2 claims -> observed frequency = 10%
```

这两个结果差异很大，但可能只是随机波动。

如果直接让模型学习这条 route 的独立系数，模型会把噪声误当成风险规律。

500 这个数不是行业铁律。

它来自本项目第一版的工程判断：

```text
1. 与 baseline pricing 中 category / route credibility threshold 保持一致。
2. 当前总 eligible exposure 是 110,197，500 约等于 0.45% 的组合规模。
3. 当前 claim frequency 约 7.70%，500 exposure 预期约 38.5 个 claims。
4. 这个量级足够让一个分组的 frequency 不至于完全由几个 claim 随机决定。
```

可以说它是：

```text
经验型稳定性门槛，不是理论最优值。
```

后续可以改进：

```text
1. 做 sensitivity test：100、250、500、1000 分别比较。
2. 改成 minimum expected claims threshold，例如至少 30 claims。
3. 用 credibility smoothing，而不是硬合并。
4. 用正则化 GLM 或 hierarchical model 处理稀疏类别。
```

当前保留 500 的原因：

```text
Phase 2 需要一个稳定、透明、容易解释的第一版 GLM。
更细的 credibility 和 smoothing 留到 Phase 3。
```

## 4. What the Validation Plan Is Doing

Validation 的核心问题是：

```text
模型是不是只记住了训练数据？
它能不能在没见过的数据上也给出合理预测？
```

做法：

```text
1. 把 order_id 分成 train 和 test。
2. 用 train 训练模型。
3. 在 test 上预测。
4. 比较 test 的实际赔款和预测赔款。
```

为什么按 `order_id` split，而不是随机按行 split：

```text
同一 order_id 可能有多个 order_item_id。
如果同一个订单的一部分 item 在 train，另一部分在 test，
test 就不再是真正没见过的数据。
```

所以我们用 order-level split。

本项目当前：

```text
train: 80% orders
test: 20% orders
random_seed = 20260521
```

Validation 分三层：

| Layer | Question |
|---|---|
| Frequency validation | claim probability 预测得怎么样？ |
| Severity validation | 有赔款时，赔款金额预测得怎么样？ |
| Pure premium validation | frequency * severity 后，总 expected loss 是否合理？ |

这三层对应保险定价公式：

```text
Expected Loss = Frequency * Severity
```

## 5. What Calibration Means

Calibration 不是问：

```text
模型有没有把每一单预测对？
```

在保险定价里，每一单是否赔付有很强随机性，不可能逐单完全预测。

Calibration 问的是：

```text
模型说一组 exposure 平均会赔多少，实际是否接近？
```

例子：

```text
模型给 1,000 个 exposure 平均预测 claim probability = 8%。
如果实际大约有 80 个 claim，模型是 calibrated。
如果实际有 150 个 claim，模型低估风险。
如果实际只有 30 个 claim，模型高估风险。
```

当前三个 calibration CSV 都按预测值从低到高分成 10 组：

```text
prediction_decile = 1 最低风险组
prediction_decile = 10 最高风险组
```

### glm_frequency_calibration.csv

用途：

```text
检查 claim probability 是否校准。
```

主要字段：

| Field | Meaning |
|---|---|
| prediction_decile | 按 predicted frequency 分成的十分位 |
| exposures | 该组 exposure 数 |
| actual_claims | 该组实际 covered claims 数 |
| actual_frequency | actual_claims / exposures |
| predicted_frequency | 模型平均预测赔付概率 |

怎么看：

```text
actual_frequency 和 predicted_frequency 越接近越好。
decile 越高，actual_frequency 通常也应该越高。
```

### glm_severity_calibration.csv

用途：

```text
检查 covered claims 上的赔款金额预测是否校准。
```

主要字段：

| Field | Meaning |
|---|---|
| prediction_decile | 按 predicted severity 分成的十分位 |
| claims | 该组 covered claims 数 |
| actual_total_loss | 该组实际总 net_loss |
| predicted_total_loss | 该组预测总 severity |
| actual_severity | 实际平均赔款 |
| predicted_severity | 预测平均赔款 |
| actual_to_expected | actual_total_loss / predicted_total_loss |

怎么看：

```text
actual_to_expected 接近 1 表示该赔款金额分组校准较好。
```

### glm_pure_premium_calibration.csv

用途：

```text
检查最终 expected loss 是否校准。
```

它把 frequency 和 severity 合在一起：

```text
predicted_total_loss = sum(pred_frequency * pred_severity)
actual_total_loss = sum(net_loss)
```

主要字段：

| Field | Meaning |
|---|---|
| exposures | 该组 exposure 数 |
| actual_claims | 实际 claims 数 |
| actual_total_loss | 实际总净赔款 |
| predicted_total_loss | 模型预测总赔款 |
| actual_pure_premium | actual_total_loss / exposures |
| predicted_pure_premium | predicted_total_loss / exposures |
| actual_to_expected | actual_total_loss / predicted_total_loss |

这是 pricing 最重要的 calibration 表。

原因：

```text
保险定价最终关心的是 expected loss，而不是单独的概率或金额。
```

## 6. What AUC, Brier, MAE, RMSE Mean

### Frequency AUC

AUC 衡量排序能力。

它问的是：

```text
随机拿一个实际有 claim 的 exposure 和一个实际没有 claim 的 exposure，
模型有多大概率把有 claim 的 exposure 排得更高？
```

范围：

```text
0.5 = 和随机排序差不多
1.0 = 完美排序
```

当前 test AUC：

```text
0.560
```

解释：

```text
排序能力温和，不强。
但 Phase 2 的 GLM 主要是可解释定价基准，不是最终黑箱排序模型。
```

注意：

```text
AUC 高不代表价格校准好。
一个模型可以排序很强，但整体赔款预测偏高或偏低。
```

### Frequency Brier Score

Brier score 衡量概率预测误差。

公式直觉：

```text
mean((actual_flag - predicted_probability)^2)
```

例如：

```text
actual = 1, predicted = 0.80 -> error = (1 - 0.80)^2 = 0.04
actual = 0, predicted = 0.80 -> error = (0 - 0.80)^2 = 0.64
```

越低越好。

当前 test Brier score：

```text
0.0717
```

它说明模型的概率预测误差处于当前低频 claim 场景下的可用范围。

### Severity MAE

MAE 是平均绝对误差：

```text
mean(abs(actual_loss - predicted_loss))
```

当前 test MAE：

```text
2.45
```

解释：

```text
在 covered claims 上，模型预测的单笔 severity 平均绝对误差约为 2.45。
```

### Severity RMSE

RMSE 是均方根误差：

```text
sqrt(mean((actual_loss - predicted_loss)^2))
```

RMSE 会更重罚大误差。

当前 test RMSE：

```text
3.88
```

解释：

```text
如果 RMSE 明显高于 MAE，说明存在一些较大的赔款预测误差。
```

在本项目中：

```text
MAE = 2.45
RMSE = 3.88
```

这和赔款金额右尾分布是匹配的。

## 7. What Pure Premium Metrics Mean

Pure premium 是每个 exposure 的预期赔款：

```text
Pure Premium = Expected Loss = Frequency * Severity
```

在模型里：

```text
predicted_pure_premium_i =
pred_frequency_i * pred_severity_i
```

一个组合的总预测赔款是：

```text
predicted_total_loss = sum(predicted_pure_premium_i)
```

实际总赔款是：

```text
actual_total_loss = sum(net_loss_i)
```

A/E 是：

```text
Actual / Expected = actual_total_loss / predicted_total_loss
```

解释：

| A/E | Meaning |
|---:|---|
| 1.00 | 实际赔款和预测赔款基本一致 |
| > 1.00 | 实际赔款高于预测，模型低估风险 |
| < 1.00 | 实际赔款低于预测，模型高估风险 |

当前 test result：

```text
actual_total_loss = 33,160.78
predicted_total_loss = 33,062.58
A/E = 1.003
```

意思是：

```text
在测试集这批模型没见过的订单上，
实际赔款比模型预测赔款高约 0.3%。
```

所以说：

```text
测试集 A/E 接近 1，说明 GLM expected loss 在组合层校准合理。
```

这句话的准确含义是：

```text
模型不一定能准确判断每一单是否会赔，
但把一批 exposure 聚合起来看，总预测赔款和总实际赔款接近。
```

这对保险定价很重要。

原因：

```text
保险公司不是靠每一单都预测准赚钱，
而是靠一组风险的总保费足以覆盖这组风险的总预期赔款和费用。
```

## 8. How to Read the Current Result

当前 GLM 结果可以这样解释：

```text
1. Frequency GLM 的排序能力温和：test AUC = 0.560。
2. Frequency GLM 的平均概率校准还可以：test actual frequency 7.80%，predicted 7.66%。
3. Severity GLM 能跟踪平均赔款：test actual severity 19.34，predicted 19.43。
4. Pure premium 最终组合校准较好：test A/E = 1.003。
5. GLM 的作用不是替代 baseline，而是在 exposure 层重新分配 expected loss。
```

Baseline：

```text
所有 eligible exposure 使用同一个 pure premium。
```

GLM：

```text
不同 category、route、freight ratio、weight、volume、estimated delivery days
会有不同 expected loss。
```

这就是 GLM pricing 的业务价值。

## 9. What to Improve Later

后续不是简单“换掉 GLM”，而是按问题改进：

```text
如果排序能力太弱：Phase 4 加 XGBoost challenger。
如果小商家/小路线不稳定：Phase 3 做 credibility。
如果 A/E 分组偏离明显：做 calibration adjustment 或 factor review。
如果真实数据有赔付发展：加入 IBNR / development。
如果需要监管/保险公司解释：继续保留 GLM 作为主费率解释模型。
```

当前 Phase 2 结论：

```text
Binomial frequency GLM + Gamma severity GLM 是合理的第一版可解释 pricing model。
```
