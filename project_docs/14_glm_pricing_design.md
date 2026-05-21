# 14 GLM Pricing Design

本文档定义 Phase 2 的 GLM pricing 设计。

目标是在 Phase 1 的 exposure table、synthetic claims layer 和 baseline pricing 之上，建立一个可解释的 exposure-level GLM 定价模型。

暂不做：

```text
XGBoost
SHAP
dashboard
presentation
Phase 3/4 credibility, backtesting, stress testing
```

## 1. Readiness Check

当前已有输入：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/pricing_baseline.csv
data/processed/pricing_baseline_summary.json
```

关键检查结果：

| Check | Result |
|---|---:|
| total rows | 112,650 |
| unique exposure keys | 112,650 |
| eligible exposures | 110,197 |
| covered claims | 8,485 |
| claim frequency among eligible | 7.70% |
| average net severity among covered claims | 19.22 |
| paid_loss equals net_loss in current version | yes |
| selected GLM feature missing values | 0 |

结论：

```text
数据足以进入 Phase 2 GLM pricing。
```

原因：

```text
1. exposure key 唯一，仍保持 order_id + order_item_id + seller_id + product_id 粒度。
2. frequency target covered_claim_flag 已存在。
3. severity target paid_loss / net_loss 已存在，且 covered claims 上为正。
4. 可报价特征无缺失，可以直接进入第一版 GLM。
```

## 2. Pricing Unit

GLM pricing 继续保持 exposure-level 口径：

```text
order_id + order_item_id + seller_id + product_id
```

每一行代表：

```text
一个卖家在一笔订单中的一个商品明细产生的一次退货运费险风险暴露。
```

`seller_id` 和 `product_id` 在 Phase 2 中作为 exposure identifier 保留，不直接作为高基数 rating factor。

原因：

```text
seller_id 直接入模会产生稀疏、不稳定、近似经验费率的问题。
商家历史赔付率和 credibility 调整放到 Phase 3。
```

## 3. Modeling Population

频率模型样本：

```text
claim_eligible_flag == 1
```

目标变量：

```text
covered_claim_flag
```

含义：

```text
该 exposure 是否触发 Coverage A: Return Shipping 的保险赔付。
```

严重度模型样本：

```text
claim_eligible_flag == 1
and covered_claim_flag == 1
and net_loss > 0
```

第一版严重度目标使用：

```text
net_loss
```

原因：

```text
net_loss 是计入赔付率和纯保费的最终净赔款。
当前版本 paid_loss == net_loss，因此两者结果一致。
后续如果引入 recovery、deductible 或 coinsurance，net_loss 更适合作为 pricing target。
```

非 eligible exposure：

```text
不参与模型训练。
输出 pricing_glm.csv 时保留这些行，但 glm_expected_loss 和 glm_premium 设为 0。
```

## 4. Leakage Control

Phase 2 只能使用报价时已知或可合理估计的变量。

### Allowed Pricing Features

第一版 GLM 使用这些变量：

```text
product_category_name_english
route_state
cross_state_flag
purchase_month
purchase_weekday
price
freight_value_capped
freight_to_price_ratio_capped
product_weight_g_filled
product_volume_cm3_filled
estimated_delivery_days
```

变量解释：

| Feature | Reason |
|---|---|
| product_category_name_english | 品类影响退货倾向和回仓运费 |
| route_state | 发货州到目的州路线，baseline 显示风险差异明显 |
| cross_state_flag | 跨州风险的稳定低维表达 |
| purchase_month | 季节性和大促代理变量 |
| purchase_weekday | 下单日行为差异 |
| price | 商品价值和退货行为相关 |
| freight_value_capped | 原发货运费，回仓运费的核心代理变量 |
| freight_to_price_ratio_capped | 运费相对商品价值的摩擦成本 |
| product_weight_g_filled | 重量影响物流成本和退货意愿 |
| product_volume_cm3_filled | 体积影响物流成本和退货意愿 |
| estimated_delivery_days | 报价时可见的预计配送窗口 |

### Excluded Fields

这些 outcome / 后验字段不能作为 feature：

```text
return_requested
return_approved
refund_without_return
partial_refund
request_days_after_delivery
return_reason
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
```

这些 synthetic generation fields 也不能作为 feature：

```text
return_probability
covered_claim_probability
return_factor_category
return_factor_route
return_factor_freight_ratio
return_factor_size
return_factor_month
```

原因：

```text
它们是生成 synthetic labels 的中间变量。
真实报价时不会存在，入模会让 GLM 过度贴合 synthetic mechanism。
```

这些 ID 字段保留但不入模：

```text
order_id
order_item_id
seller_id
product_id
customer_id
```

原因：

```text
ID 本身不是可泛化的费率因子。
seller_id 相关经验风险将在 Phase 3 用 credibility 单独处理。
```

## 5. Feature Transformations

数值变量右尾较长，第一版使用 log transform：

```text
log_price = log1p(price)
log_freight_value_capped = log1p(freight_value_capped)
log_freight_to_price_ratio_capped = log1p(freight_to_price_ratio_capped)
log_product_weight_g_filled = log1p(product_weight_g_filled)
log_product_volume_cm3_filled = log1p(product_volume_cm3_filled)
log_estimated_delivery_days = log1p(estimated_delivery_days)
```

分类变量处理：

```text
product_category_name_english: exposure count < 500 的类别合并为 Other
route_state: exposure count < 500 的路线合并为 Other
purchase_month: categorical
purchase_weekday: categorical
cross_state_flag: categorical/binary
```

原因：

```text
低 exposure 类别直接入 GLM 会产生不稳定系数。
500 门槛与 baseline pricing 的 category / route credibility threshold 保持一致。
```

## 6. Model Forms

### Frequency Model

第一版主模型：

```text
Binomial GLM with logit link
target = covered_claim_flag
population = eligible exposures
```

公式结构：

```text
covered_claim_flag ~
  category_group
  + route_group
  + cross_state_flag
  + purchase_month
  + purchase_weekday
  + log_price
  + log_freight_value_capped
  + log_freight_to_price_ratio_capped
  + log_product_weight_g_filled
  + log_product_volume_cm3_filled
  + log_estimated_delivery_days
```

输出：

```text
glm_frequency = P(covered_claim_flag = 1)
```

### Severity Model

第一版主模型：

```text
Gamma GLM with log link
target = net_loss
population = covered claims only
```

公式结构使用同一套报价时已知变量。

输出：

```text
glm_severity = E(net_loss | covered_claim_flag = 1)
```

## 7. Pricing Formula

Exposure-level expected loss：

```text
glm_expected_loss_i =
glm_frequency_i * glm_severity_i
```

Commercial premium：

```text
glm_commercial_premium_i =
glm_expected_loss_i / target_loss_ratio
```

第一版沿用 baseline pricing 假设：

```text
target_loss_ratio = 60%
```

非 eligible exposure：

```text
glm_frequency = 0
glm_expected_loss = 0
glm_commercial_premium = 0
```

## 8. Validation Plan

使用 order-level split，避免同一订单的多个 item 同时进入 train 和 test：

```text
train: 80% order_id
test: 20% order_id
random_seed = 20260521
```

Frequency validation：

```text
AUC
Brier score
train/test observed frequency
train/test predicted frequency
frequency calibration by decile
```

Severity validation：

```text
MAE on covered claims
RMSE on covered claims
train/test observed severity
train/test predicted severity
severity calibration by decile
```

Pure premium validation：

```text
total actual net loss
total expected loss
actual / expected ratio
mean expected loss
comparison to baseline pure premium
expected loss decile lift
```

## 9. Expected Outputs

脚本：

```text
src/build_glm_pricing.py
```

主要输出：

```text
data/processed/pricing_glm.csv
data/processed/glm_pricing_summary.json
data/processed/glm_frequency_coefficients.csv
data/processed/glm_severity_coefficients.csv
data/processed/glm_frequency_calibration.csv
data/processed/glm_severity_calibration.csv
data/processed/glm_pure_premium_calibration.csv
```

`pricing_glm.csv` 应保留 exposure-level 主键和核心 pricing 字段：

```text
order_id
order_item_id
seller_id
product_id
claim_eligible_flag
covered_claim_flag
net_loss
glm_frequency
glm_severity
glm_expected_loss
glm_commercial_premium
target_loss_ratio
baseline_pure_premium
baseline_commercial_premium
```

## 10. Done Criteria

Phase 2 GLM pricing 第一版完成标准：

```text
1. pricing_glm.csv 行数等于 exposure_claims_synthetic.csv 行数。
2. exposure key 仍唯一。
3. 非 eligible exposure 的 GLM expected loss 和 premium 为 0。
4. 模型没有使用 outcome、post-bind 或 synthetic generation fields。
5. frequency model 和 severity model 都能成功拟合。
6. summary 记录 train/test metrics、A/E ratio、baseline comparison。
7. GLM expected loss 能聚合到 portfolio、order、seller 和 route 层。
```
