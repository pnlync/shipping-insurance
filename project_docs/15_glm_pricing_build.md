# 15 GLM Pricing Build

本文档记录 Phase 2 第一版 GLM pricing 的实现结果。

设计口径见：

```text
project_docs/14_glm_pricing_design.md
```

脚本：

```text
src/build_glm_pricing.py
```

输入：

```text
data/processed/exposure_claims_synthetic.csv
data/processed/pricing_baseline.csv
```

输出：

```text
data/processed/pricing_glm.csv
data/processed/glm_pricing_summary.json
data/processed/glm_frequency_coefficients.csv
data/processed/glm_severity_coefficients.csv
data/processed/glm_frequency_calibration.csv
data/processed/glm_severity_calibration.csv
data/processed/glm_pure_premium_calibration.csv
```

## 1. Model Structure

Frequency model：

```text
Binomial GLM with logit link
target = covered_claim_flag
population = claim_eligible_flag == 1
```

Severity model：

```text
Gamma GLM with log link
target = net_loss
population = covered claims only
```

Pricing formula：

```text
glm_expected_loss = glm_frequency * glm_severity
glm_commercial_premium = glm_expected_loss / 0.60
```

第一版只使用报价时已知变量。

明确没有使用：

```text
return_requested
return_approved
return_reason
covered_claim_probability
covered_claim_flag
claim_type
gross_loss
recovery_from_carrier
paid_loss
net_loss
claim_status
return_factor_*
return_probability
```

## 2. Data Validation

| Check | Result |
|---|---:|
| pricing_glm rows | 112,650 |
| claims input rows | 112,650 |
| unique exposure keys | 112,650 |
| ineligible expected loss nonzero rows | 0 |
| ineligible premium nonzero rows | 0 |
| missing GLM prediction fields | 0 |

结论：

```text
GLM 输出保持 exposure-level pricing 口径：
order_id + order_item_id + seller_id + product_id
```

## 3. Train/Test Validation

使用 order-level split：

```text
train orders: 80%
test orders: 20%
random_seed = 20260521
```

### Frequency

| Metric | Train | Test |
|---|---:|---:|
| exposures | 88,201 | 21,996 |
| actual claims | 6,770 | 1,715 |
| actual frequency | 7.68% | 7.80% |
| predicted frequency | 7.68% | 7.66% |
| AUC | 0.570 | 0.560 |
| Brier score | 0.0705 | 0.0717 |

Interpretation:

```text
Frequency model 在组合层校准正常，但排序能力温和。
这符合当前 synthetic claims 的第一版设定：标签生成机制较简单，GLM 主要用于可解释定价基准，而不是追求黑箱排序能力。
```

### Severity

| Metric | Train | Test |
|---|---:|---:|
| covered claims | 6,770 | 1,715 |
| actual severity | 19.20 | 19.34 |
| predicted severity | 19.30 | 19.43 |
| MAE | 2.37 | 2.45 |
| RMSE | 3.65 | 3.88 |

Interpretation:

```text
Severity GLM 能较好跟踪平均赔款水平。
由于第一版 severity 基于 freight_value_capped 模拟，Gamma GLM with log link 是合适的透明基准。
```

### Pure Premium

| Metric | Train | Test |
|---|---:|---:|
| actual total loss | 129,951.90 | 33,160.78 |
| predicted total loss | 131,300.85 | 33,062.58 |
| actual / expected | 0.990 | 1.003 |
| actual pure premium | 1.4734 | 1.5076 |
| predicted pure premium | 1.4887 | 1.5031 |

Interpretation:

```text
测试集 A/E 接近 1，说明 GLM expected loss 在组合层校准合理。
```

## 4. Portfolio Pricing Result

全量 eligible exposure 上，使用最终全量模型输出 exposure-level GLM premium。

| Metric | Value |
|---|---:|
| actual total net loss | 163,112.68 |
| GLM expected total loss | 164,831.10 |
| GLM actual / expected | 0.990 |
| baseline expected total loss | 163,112.68 |
| baseline actual / expected | 1.000 |
| GLM mean expected loss | 1.4958 |
| baseline mean expected loss | 1.4802 |
| GLM total commercial premium | 274,718.50 |
| GLM expected loss ratio | 60.00% |

说明：

```text
Baseline 是 portfolio average，因此全量 A/E 天然等于 1。
GLM 在 exposure 层重新分配 expected loss，使不同品类、路线、运费占比和商品尺寸获得不同价格。
```

## 5. Output Table

核心输出：

```text
data/processed/pricing_glm.csv
```

关键字段：

```text
glm_frequency
glm_severity
glm_expected_loss
glm_commercial_premium
glm_expected_loss_ratio_to_freight
glm_expected_loss_ratio_to_baseline
```

非 eligible exposure：

```text
glm_frequency = 0
glm_severity = 0
glm_expected_loss = 0
glm_commercial_premium = 0
```

## 6. Important Limitations

第一版 GLM 不代表最终生产定价。

当前限制：

```text
1. Claims 是 synthetic，不是真实 TikTok Shop 商家理赔。
2. 没有 seller credibility，seller_id 未作为直接 rating factor。
3. 没有 IBNR、赔付发展或真实观察窗口处理。
4. 没有 XGBoost challenger，也没有 SHAP。
5. 没有 dashboard 或 presentation。
```

下一步建议：

```text
Phase 3: seller credibility + loss ratio backtesting + stress testing + pricing memo
```
