# Decision Log

这个文件记录项目中的关键设计决策。每条决策都要写清楚背景、决定和原因。

## 2026-05-20: Use Exposure-Level Pricing

Decision:

```text
基础风险单位使用 order_id + order_item_id + seller_id + product_id。
```

Reason:

```text
Olist 的 freight_value 位于 order_items 层。
一笔订单可能包含多个商品或多个卖家。
运费险定价需要把商品、商家和物流风险精确归因到明细层。
```

Implication:

```text
模型、理赔模拟和纯保费计算都在 exposure 层完成。
订单级展示、商家级监控和组合级赔付率都从 exposure 层聚合得到。
```

## 2026-05-20: Keep Product Category Translation Table

Decision:

```text
保留 product_category_name 和 product_category_name_english 两个字段。
建模和报告优先使用英文品类字段。
```

Reason:

```text
Olist 原始 product_category_name 是葡萄牙语。
英文品类更适合报告展示和面试讲解。
保留原始字段便于追溯。
```

## 2026-05-21: Use Insurance-Style Synthetic Claim Labels

Decision:

```text
下一步不只生成 return_flag，也不只生成 claim_flag 和 paid_loss。
第一版 synthetic layer 拆成 returns layer 和 claims layer。
```

Core fields:

```text
returns layer:
return_requested, return_reason, return_approved,
refund_without_return, partial_refund, request_days_after_delivery

claims layer:
covered_claim_flag, claim_type, gross_loss,
recovery_from_carrier, paid_loss, net_loss, claim_status
```

Reason:

```text
退货事件不等于保险赔付事件。
项目目标是运费险定价，不是普通退货率预测。
保险化标签能支持 frequency / severity / expected loss 的精算定价闭环。
```

Implication:

```text
Phase 1 第一版先只模拟 Coverage A: Return Shipping。
Coverage B: Failed Delivery / Logistics Exception 和
Coverage C: Replacement / Reshipment Shipping 后续再扩展。
```

## 2026-05-21: Use 60% Target Loss Ratio for Baseline Pricing

Decision:

```text
第一版 baseline commercial premium 使用 target_loss_ratio = 60% 反推。
```

Formula:

```text
commercial_premium = pure_premium / target_loss_ratio
```

Reason:

```text
纯保费只覆盖预期赔款。
商业保费需要覆盖费用、利润、风险边际和资本成本。
60% 目标赔付率是第一版清晰、可解释的商业定价假设。
```

Implication:

```text
当前 synthetic claims 下：
portfolio pure premium = 1.4802
portfolio commercial premium = 2.4670
expected loss ratio = 60.00%
```

## 2026-05-21: Use Two-Part GLM for Phase 2 Pricing

Decision:

```text
Phase 2 使用 two-part GLM：
frequency = Binomial GLM with logit link, target = covered_claim_flag
severity = Gamma GLM with log link, target = net_loss on covered claims only
```

Reason:

```text
运费险 exposure 的 expected loss 应拆成：
P(covered claim) * E(net_loss | covered claim)

covered_claim_flag 是保险赔付频率标签，不是普通退货标签。
net_loss 是进入赔付率和纯保费的最终净赔款。
```

Leakage control:

```text
GLM 只使用报价时已知变量。
return_requested、return_reason、claim_type、paid_loss、net_loss、claim_status
以及 return_probability、covered_claim_probability、return_factor_* 等
synthetic generation fields 都不能作为 feature。
```

Implication:

```text
GLM 输出仍保持 exposure-level pricing：
order_id + order_item_id + seller_id + product_id。

seller_id 暂时只作为 identifier 保留，不直接入模。
seller credibility 和 seller-level dynamic adjustment 留到 Phase 3。
```

## 2026-05-21: Add Seller Credibility as a Post-GLM Adjustment

Decision:

```text
Phase 3 第一版不把 seller_id 直接放进 GLM。
在 GLM expected loss 之上增加 seller credibility relativity。
```

Formula:

```text
seller_observed_ae =
seller_actual_net_loss / seller_glm_expected_loss

Z = n / (n + 500)

seller_credibility_relativity_raw =
Z * seller_observed_ae + (1 - Z) * 1.0
```

Risk controls:

```text
raw relativity cap: 0.50 to 2.00
portfolio normalization: preserve total GLM expected loss
```

Reason:

```text
当前 2,970 个 seller 中，中位数只有 8 个 eligible exposure。
直接按 seller 自身经验或把 seller_id 直接入模会过度反应随机波动。
credibility adjustment 能让大 seller 的历史经验有更多权重，
同时让小 seller 的价格主要依赖它自身 exposure mix 对应的 GLM base expected loss。
```

Implication:

```text
第一版 seller credibility 不改变整体 GLM rate level。
它主要在 seller 之间重新分配 expected loss 和 commercial premium。

这里的 shrinkage target 不是 portfolio average pure premium。
seller_credibility_relativity 接近 1.0 表示接近 GLM base expected loss，
而不是接近全组合统一平均价。
```

## 2026-05-21: Add Loss Ratio Backtesting and Monitoring

Decision:

```text
Phase 3 在 stress testing 前先增加 loss ratio backtesting / monitoring。
同时比较 baseline、GLM、GLM + seller credibility 三套 pricing basis。
```

Core metrics:

```text
A/E = actual_loss / expected_loss
Loss Ratio = actual_loss / commercial_premium
```

Monitoring dimensions:

```text
purchase_month
product_category_name_english
route_state
seller_risk_tier
seller_id
```

Reason:

```text
定价模型完成后，需要检查不同 segment 的 rate adequacy。
组合层 A/E 接近 1 不代表所有品类、路线或 seller 分层都合理。
loss ratio monitoring 能识别被低估或高估的 segment，
为后续 stress testing 和 pricing memo 提供依据。
```

Implication:

```text
当前版本是 synthetic-data monitoring framework。
真实生产 backtest 应使用历史期定价、未来期验证。
```

## 2026-05-21: Add Deterministic Stress Testing Before Phase 4

Decision:

```text
Phase 3 在 pricing memo 前增加 deterministic stress testing。
不重新训练模型，直接测试当前 baseline / GLM / credibility commercial premium
在不利 loss scenarios 下的 stressed loss ratio。
```

Stress scenarios:

```text
portfolio frequency +10% / +20%
portfolio severity +10% / +20%
portfolio frequency and severity combined +10% / +20%
elevated seller tier combined stress
watchlist category / route combined stress
```

Reason:

```text
loss ratio backtesting 只能说明当前 observed loss 下表现如何。
stress testing 用来检查未来 frequency 或 severity 恶化时，当前保费是否还有缓冲。
```

Implication:

```text
当前 base credibility loss ratio 为 59.37%。
combined +20% frequency and +20% severity 会把 credibility loss ratio 推到 85.50%，
属于 high_pressure。
```

## 2026-05-21: Add Challenger Model as Phase 4 Comparison Layer

Decision:

```text
Phase 4 先实现 challenger model 和 GLM vs challenger comparison，
暂不进入 SHAP、dashboard 或 interview deck。
```

Model structure:

```text
frequency target = covered_claim_flag
severity target = net_loss on covered claims only
expected loss = frequency * severity
```

Feature controls:

```text
只使用报价时已知变量。
不使用 return_probability、covered_claim_probability、return_factor_*、
return_requested、return_reason、claim_type、gross_loss、paid_loss、net_loss、
claim_status 等 outcome / post-bind / synthetic generation fields 作为 features。
```

Package setup:

```text
先用 Homebrew 安装 libomp。
再用当前项目 Python 安装 xgboost 3.2.0。
本次 Phase 4 输出使用真实 xgboost model family。
```

Reason:

```text
项目需要展示 champion-challenger 思路，但不能把复杂模型默认当成最终定价模型。
比较必须同时看 AUC、calibration、A/E、pure premium 和 loss ratio。
```

Result:

```text
GLM test frequency AUC = 0.560
XGBoost challenger calibrated test frequency AUC = 0.561
GLM test loss ratio = 60.18%
XGBoost challenger calibrated test loss ratio = 60.87%
```

Implication:

```text
当前不建议用 XGBoost challenger 替代 GLM 主定价模型。
challenger 可以保留为风险排序实验和面试说明材料：
更复杂模型可以略微改善 ranking，但不一定带来更好的 pricing calibration。
```
