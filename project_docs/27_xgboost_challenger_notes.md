# 27 XGBoost Challenger Notes

本文档整理 Phase 4 中关于 XGBoost challenger 的解释，方便面试时用更自然的语言说明。

## 1. What Does Challenger Risk Score Mean?

当前项目里：

```text
GLM = current pricing model / champion
XGBoost = challenger model / risk score candidate
```

这句话的意思是：

```text
XGBoost 当前主要用来比较和排序风险，
不是直接拿它的输出作为正式保费。
```

GLM 的优势：

```text
可解释
稳定
容易讲清楚每个 factor 怎么影响价格
更接近传统保险定价 / 费率表逻辑
```

XGBoost 的优势：

```text
能捕捉非线性
能捕捉变量交互
可能有更强的风险排序能力
```

但 XGBoost 的问题是：

```text
更黑箱
更容易过拟合
校准不一定好
业务上更难解释为什么某个 exposure 涨价
```

所以 Phase 4 先检查：

```text
1. XGBoost 能不能比 GLM 更好地区分高低风险？
2. XGBoost 能不能在 test set 上保持好的 A/E 和 loss ratio？
```

当前真实 XGBoost 结果：

```text
GLM test frequency AUC = 0.560
XGBoost calibrated test frequency AUC = 0.561
GLM test loss ratio = 60.18%
XGBoost calibrated test loss ratio = 60.87%
```

因此当前不建议用 XGBoost 替代 GLM 主定价模型。

更准确地说：

```text
XGBoost frequency ranking 略好，
但 pure premium A/E 和 loss ratio calibration 仍不如 GLM。
```

## 2. Did XGBoost Use All Factors?

没有。

XGBoost 只使用 quote-time-known pricing factors，而且和 GLM 保持基本一致的特征口径，方便公平比较。

当前使用的数值 features：

```text
price
freight_value_capped
freight_to_price_ratio_capped
product_weight_g_filled
product_volume_cm3_filled
estimated_delivery_days
```

当前使用的分类 features：

```text
category_group
route_group
cross_state_flag_cat
purchase_month_cat
purchase_weekday_cat
```

分类变量做 one-hot encoding。数值变量先做 `log1p()` 变换。

## 3. Why Not Use Every Quote-Time-Known Field?

`quote-time-known` 是进入定价模型的最低条件，不是充分条件。

更严谨的定价 feature 条件应该是：

```text
1. quote time 已知
2. 未来生产中稳定可得
3. 与风险有合理业务关系
4. 不直接或间接泄漏结果
5. 不会造成不可解释或不可接受的定价差异
6. 在 out-of-sample 验证中确实提升表现
```

XGBoost 可以自动寻找变量关系，但不能自动决定哪些变量应该进入保险定价模型。

## 4. Why More Features Are Not Always Better

理论上，候选 features 越多，模型可能有更多机会提高训练集精度。

但在保险定价里，字段越多也会增加：

```text
过拟合风险
泄漏风险
解释风险
生产不稳定风险
定价治理风险
```

XGBoost 会优化统计目标，但它不知道：

```text
这个字段生产环境是否稳定
这个字段未来是否一直可用
这个字段是否有代理泄漏
这个字段是否会导致不可解释的差别定价
这个字段是否只是 synthetic generation artifact
```

所以不能把“XGBoost 可以自动选 split”理解成“所有字段都应该丢进去”。

## 5. Examples of Quote-Time-Known but Risky Fields

有些字段可能在报价时已知，但仍不适合直接进入第一版定价模型。

例如：

```text
seller_id
product_id
customer_id
order_id
zip_code_prefix
city
```

原因：

```text
order_id / customer_id 没有可泛化意义
product_id 太稀疏，容易记忆单品
seller_id 应该通过 credibility 处理，而不是直接让模型记住
city / zip 可能过细，噪声大，也更难解释
```

这也是为什么当前项目选择：

```text
GLM / XGBoost:
用 exposure quote-time factors 建基础风险

Seller credibility:
单独做 seller-level 后处理
```

Seller 风险不是完全不管，而是通过 credibility adjustment 处理。

## 6. Why Keep GLM and XGBoost Features Similar?

当前 Phase 4 第一版想回答的是：

```text
同一组核心 pricing factors 下，
GLM vs XGBoost 谁更好？
```

如果 XGBoost 额外塞很多字段，而 GLM 不用，比较会变得不干净：

```text
到底是模型算法更好？
还是多加字段更好？
```

所以第一版 challenger 先保持特征口径接近。

后续可以单独做一个实验：

```text
XGBoost expanded feature set
```

但新增字段需要逐个说明：

```text
为什么 quote time 可用
为什么有业务意义
为什么不是 leakage
为什么在 test set 上确实改善了表现
```

## 7. Why Are Both AUC Values Low?

当前 GLM 和 XGBoost 的 frequency AUC 都不高：

```text
GLM test frequency AUC = 0.560
XGBoost calibrated test frequency AUC = 0.561
```

这不等于模型完全没用，但说明：

```text
在当前 quote-time-known features 下，
模型只能有限地区分 claim exposure 和 non-claim exposure。
```

主要原因有几个。

### Reason 1: Synthetic Claims Include Randomness

当前项目使用 Olist public data，没有真实退货险理赔数据。

所以 Phase 1 构造了 synthetic returns + claims layer。

这个 synthetic layer 不是由一个强规则完全决定的，而是由：

```text
品类
路线
运费比例
商品尺寸
月份
随机扰动
```

共同生成。

因此模型能学到一部分结构，但不能把所有 covered claims 准确排到最前面。

### Reason 2: Pricing Features Are Intentionally Restricted

定价模型只能使用报价时已知变量。

很多对 claim outcome 有强解释力的字段不能用，例如：

```text
return_requested
return_reason
claim_type
paid_loss
net_loss
covered_claim_probability
return_factor_*
```

如果把这些字段放进模型，AUC 很可能会明显升高。

但那不是更好的定价模型，而是 leakage。

### Reason 3: Claim Frequency Is Low and Noisy

当前 covered claim frequency 约为：

```text
7.7%
```

这类低频事件本身就有较强随机波动。

即使高风险组和低风险组有差异，也会出现很多：

```text
高风险但没赔
低风险但赔了
```

这种噪声会压低 AUC。

### Reason 4: Seller ID Is Not Directly Used

当前模型没有直接使用：

```text
seller_id
```

这是有意的。

Seller experience 放在 Phase 3 的 credibility adjustment 里，而不是让 GLM 或 XGBoost 直接记住 seller。

这样做更稳健、更符合精算 credibility 思路，但也会牺牲一部分 frequency sorting power。

### Reason 5: Quote-Time Variables May Explain Price Level Better Than Exact Claim Occurrence

保险定价不一定要求模型精准判断某一单是否一定会赔。

更重要的是：

```text
在 portfolio / segment / decile 层面，
expected loss 是否接近 actual loss。
```

所以 AUC 低说明 claim ranking power 有限，但还要结合：

```text
calibration
pure premium A/E
loss ratio
segment monitoring
```

一起判断模型是否可用于定价。

当前 GLM 的 test AUC 不高，但 test pure premium A/E 接近 1：

```text
GLM test pure premium A/E = 1.003
GLM test loss ratio = 60.18%
```

这说明它排序能力一般，但整体 expected loss level 比较准。

## 8. AUC, Severity, Pure Premium A/E, and Loss Ratio

当前 AUC 只衡量 frequency model。

也就是：

```text
target = covered_claim_flag
prediction = predicted claim probability
```

AUC 衡量的是模型能不能把发生 covered claim 的 exposure 排在不发生 covered claim 的 exposure 前面。

它不衡量：

```text
发生赔付后赔多少钱
```

Severity 在 covered claims only 上评估：

```text
target = net_loss
prediction = predicted severity
```

主要 severity 指标：

```text
actual severity vs predicted severity
MAE
RMSE
severity A/E
```

Pure premium 是 frequency 和 severity 的合并结果：

```text
predicted pure premium = predicted frequency * predicted severity
```

Pure Premium A/E：

```text
actual total net loss / predicted expected loss
```

解释：

```text
A/E = 1.00  预测总赔款刚好
A/E > 1.00  实际赔款高于预测，模型低估风险
A/E < 1.00  实际赔款低于预测，模型高估风险
```

Loss Ratio：

```text
actual loss / commercial premium
```

本项目中：

```text
commercial premium = expected loss / target_loss_ratio
target_loss_ratio = 60%
```

所以：

```text
loss ratio = pure premium A/E * 60%
```

例子：

```text
XGBoost calibrated test pure premium A/E = 1.014
target loss ratio = 60%
XGBoost calibrated test loss ratio = 60.87%
```

含义：

```text
模型低估 expected loss 约 1.4%。
按 60% target loss ratio 收费后，实际 loss ratio 变成约 60.87%。
```

## 9. Interview Summary

可以这样表述：

```text
我没有把 XGBoost 默认当成最终定价模型。
我把 GLM 作为可解释的 champion pricing model，
把 XGBoost 作为 challenger risk score。

XGBoost 使用同一组 quote-time-known pricing factors，
不使用 outcome、post-bind 或 synthetic generation fields。

这次真实 XGBoost 在 test AUC 上略高于 GLM，
但没有在 pure premium A/E 和 loss ratio calibration 上超过 GLM，
所以结论是保留 GLM 作为主定价模型，
XGBoost 作为 challenger experiment 和后续 feature-importance / governance 分析基础。
```
