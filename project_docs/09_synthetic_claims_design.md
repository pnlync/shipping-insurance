# 09 Synthetic Claims Design

本文档定义第一版 synthetic returns + claims layer 的口径。

目标不是伪造真实 TikTok Shop 参数，而是在 Olist exposure table 上构造一个可解释、可复现、可用于后续 baseline pricing 和 GLM pricing 的保险化标签层。

## 1. Why This Layer Exists

Olist 公共数据有订单、商品、卖家、买家区域和运费，但没有真实的退货险理赔数据。

因此下一步需要生成：

```text
returns layer
claims layer
```

而不是只生成一个普通的：

```text
return_flag
```

原因：

```text
退货事件不等于保险赔付事件。
发生退货，也可能因为不符合保障责任而不赔。
没有退货，也可能存在物流异常或补发运费风险。
```

Phase 1 先不把所有保障模块一次做完，而是先做最小可解释版本。

## 2. Scope for Version 1

第一版只模拟：

```text
Coverage A: Return Shipping
买家合规退货产生的回仓运费。
```

暂不模拟：

```text
Coverage B: Failed Delivery / Logistics Exception
未妥投、丢件、严重延迟导致的正向物流成本损失。

Coverage C: Replacement / Reshipment Shipping
因物流或履约问题导致补发产生的额外运费。
```

原因：

```text
Phase 1 的目标是跑通 exposure -> claims -> baseline premium。
如果第一版同时模拟多个保障模块，会增加假设复杂度，反而削弱可解释性。
```

## 3. Input Population

输入表：

```text
data/processed/exposure_table.csv
```

第一版 claim simulation population：

```text
order_status == delivered
```

对于非 delivered exposure：

```text
claim_eligible_flag = 0
return_requested = 0
return_approved = 0
covered_claim_flag = 0
paid_loss = 0
net_loss = 0
claim_status = not_eligible
```

原因：

```text
退货运费险的第一版可观察风险应发生在订单完成交付之后。
canceled / shipped / processing / invoiced 等状态不应和 delivered exposure 混合模拟。
```

## 4. Output Table

建议输出：

```text
data/processed/exposure_claims_synthetic.csv
```

该表保留 exposure table 的核心字段，并新增 synthetic returns + claims 字段。

核心 exposure 字段：

```text
order_id
order_item_id
seller_id
product_id
customer_id
order_status
product_category_name_english
price
freight_value
freight_to_price_ratio
product_weight_g
product_volume_cm3
seller_state
customer_state
route_state
cross_state_flag
purchase_month
purchase_weekday
estimated_delivery_days
```

新增 returns layer 字段：

```text
claim_eligible_flag
return_probability
return_requested
return_reason
return_approved
refund_without_return
partial_refund
request_days_after_delivery
```

新增 claims layer 字段：

```text
covered_claim_probability
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

建议同时输出 summary：

```text
data/processed/synthetic_claims_summary.json
```

## 5. Label Meaning

### return_requested

含义：

```text
买家是否发起退货请求。
```

注意：

```text
这是售后行为标签，不是保险赔付标签。
```

### return_approved

含义：

```text
退货请求是否被平台或卖家认可。
```

第一版可简化为：

```text
return_requested == 1 的大多数 case 会被 approved。
高风险/异常 case 可设为不通过。
```

### covered_claim_flag

含义：

```text
是否触发本项目定义的保险责任。
```

第一版 Coverage A 下：

```text
covered_claim_flag = 1
当且仅当：
claim_eligible_flag = 1
return_requested = 1
return_approved = 1
refund_without_return = 0
claim_type = return_shipping
```

### claim_type

第一版允许值：

```text
none
return_shipping
```

后续版本可扩展：

```text
failed_delivery
replacement_shipping
```

### gross_loss

含义：

```text
赔付前的总损失金额。
```

第一版：

```text
gross_loss 基于 freight_value 模拟。
```

### recovery_from_carrier

含义：

```text
可从物流商、平台或其他渠道追回的金额。
```

第一版可以设置为：

```text
大多数 return_shipping claim 为 0。
少量 case 给一个较小 recovery。
```

### paid_loss

含义：

```text
保险产品实际支付的赔款。
```

第一版：

```text
paid_loss = max(gross_loss - recovery_from_carrier, 0)
```

### net_loss

含义：

```text
计入赔付率和纯保费的最终净赔款。
```

第一版：

```text
net_loss = paid_loss
```

后续如加入 deductible、coinsurance、salvage 或 external recovery，可再区分。

## 6. Frequency Assumptions

第一版可以使用规则型概率，而不是训练模型。

基础结构：

```text
return_probability =
base_return_rate
* category_factor
* route_factor
* freight_ratio_factor
* size_factor
* month_factor
```

然后限制在合理范围：

```text
return_probability = clip(return_probability, min_probability, max_probability)
```

建议第一版使用可解释假设：

```text
base_return_rate: 8%
min_probability: 1%
max_probability: 25%
```

风险因子方向：

| Factor | Direction | Reason |
|---|---|---|
| category_factor | varies by category | 不同品类退货倾向不同 |
| route_factor | cross-state slightly higher | 长路线和跨州物流体验更不确定 |
| freight_ratio_factor | high ratio higher | 运费相对商品价格高时售后摩擦更明显 |
| size_factor | very bulky items slightly lower return frequency | 大件退货门槛更高，但 severity 更高 |
| month_factor | mild seasonality | 大促或季节性可影响退货行为 |

注意：

```text
这些是 synthetic assumptions，不代表真实 TikTok Shop 参数。
文档和 README 必须明确这一点。
```

## 7. Severity Assumptions

第一版 Coverage A 的赔付金额基于回仓运费。

由于 Olist 只有原订单 `freight_value`，没有真实 return shipping fee，因此用：

```text
gross_loss =
freight_value_capped
* return_shipping_multiplier
* random_noise
```

建议：

```text
freight_value_capped = min(freight_value, freight_value_p99)
freight_value_p99 = 84.52
return_shipping_multiplier around 1.0
random_noise around 0.8 to 1.2
```

解释：

```text
第一版假设退货回仓运费与原发货运费同量级。
P99 cap 防止极端运费把 synthetic paid_loss 拉得不合理。
```

## 8. Feature Eligibility and Leakage Control

用于生成 synthetic labels 的字段分两类。

可作为报价时已知风险因子：

```text
price
freight_value
freight_to_price_ratio
product_category_name_english
product_weight_g
product_volume_cm3
seller_state
customer_state
route_state
cross_state_flag
purchase_month
purchase_weekday
estimated_delivery_days
```

后验标签字段，不能作为报价模型输入：

```text
return_requested
return_reason
return_approved
refund_without_return
partial_refund
request_days_after_delivery
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

核心原则：

```text
可以用报价时已知字段生成 synthetic labels。
但训练 pricing model 时，不能把 synthetic outcome 或真实后验 outcome 当作 feature。
```

## 9. Treatment of EDA Issues

来自 `08_exposure_level_eda.md` 的处理口径：

```text
delivered only
```

用于 eligibility。

```text
freight_value P99 cap = 84.52
```

用于 severity 生成。

```text
freight_to_price_ratio P99 cap = 1.549
```

用于 frequency factor 或分箱。

```text
product size missing rows = 18
```

第一版建议：

```text
用 product_category_name_english 的中位数填充。
如果该品类无法计算中位数，fallback 到全局中位数。
```

```text
product_weight_g = 0 rows = 8
```

第一版建议：

```text
视为异常尺寸值，同样走品类中位数填充。
```

## 10. Reproducibility

synthetic claims 必须可复现。

代码中需要固定：

```text
random_seed
```

建议：

```text
random_seed = 20260521
```

summary 中必须记录：

```text
random_seed
base_return_rate
min_probability
max_probability
freight_value_cap
freight_to_price_ratio_cap
claim count
claim frequency
total gross_loss
total recovery_from_carrier
total paid_loss
total net_loss
average paid_loss among claims
pure premium per eligible exposure
```

## 11. First Implementation Target

下一步代码文件：

```text
src/build_synthetic_claims.py
```

建议输出：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/synthetic_claims_summary.json
```

Done criteria：

```text
1. 输出表行数等于 exposure_table 行数。
2. 非 delivered exposure 的 claim_eligible_flag = 0 且 paid_loss = 0。
3. delivered exposure 中有合理比例的 return_requested 和 covered_claim_flag。
4. paid_loss 只在 covered_claim_flag = 1 时为正。
5. summary 能解释 claim frequency、severity、pure premium。
6. 所有随机结果可通过 random_seed 复现。
```
