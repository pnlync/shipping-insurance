# 31 XGBoost Interpretability Build

## What Was Built

New script:

```text
src/build_xgboost_interpretability.py
```

New outputs:

```text
data/processed/xgboost_interpretability_summary.json
data/processed/xgboost_frequency_feature_importance.csv
data/processed/xgboost_severity_feature_importance.csv
data/processed/xgboost_frequency_shap_summary.csv
data/processed/xgboost_severity_shap_summary.csv
data/processed/xgboost_frequency_base_feature_summary.csv
data/processed/xgboost_severity_base_feature_summary.csv
```

The script is also added to the pipeline:

```text
python main.py --run interpretability
python main.py --run phase4
```

## Method

The script retrains the same XGBoost challenger on the same order-level train split used for validation.

It then explains the model on:

```text
frequency:
test eligible exposures

severity:
test covered claims only
```

Two explanation types are produced:

```text
1. XGBoost built-in feature importance
2. XGBoost native SHAP-style contributions using pred_contribs=True
```

The external `shap` package was not used.

Important scale note:

```text
frequency contribution scale = log-odds margin
severity contribution scale = log1p(net_loss)
```

These are model-scale explanations, not direct premium-dollar explanations.

## Feature Importance Outputs

Feature importance 指的是 XGBoost tree split importance。

对应输出文件：

```text
data/processed/xgboost_frequency_feature_importance.csv
data/processed/xgboost_severity_feature_importance.csv
```

这些文件包含：

```text
encoded_feature
base_feature
weight
gain
cover
total_gain
total_cover
gain_share
```

主要看：

```text
gain
gain_share
```

解释：

```text
gain 表示该 feature 在 tree split 中平均带来的 split improvement。
gain_share 表示该 feature 的 gain 在所有 features 中的占比。
```

Feature importance 的用途：

```text
看模型在 tree split 上主要依赖哪些变量。
```

Feature importance 的限制：

```text
它只告诉我们哪些变量常带来 split improvement，
不直接告诉方向，也不等于每个 exposure 的风险贡献。
```

## SHAP-Style Contribution Outputs

SHAP-style contribution 指的是 XGBoost native contribution：

```text
booster.predict(DMatrix(...), pred_contribs=True)
```

对应输出文件：

```text
data/processed/xgboost_frequency_shap_summary.csv
data/processed/xgboost_severity_shap_summary.csv
data/processed/xgboost_frequency_base_feature_summary.csv
data/processed/xgboost_severity_base_feature_summary.csv
```

这些文件包含：

```text
encoded_feature
base_feature
mean_abs_contribution
mean_abs_contribution_share
mean_contribution
positive_share
p05_contribution
p50_contribution
p95_contribution
```

主要看：

```text
mean_abs_contribution
mean_abs_contribution_share
```

解释：

```text
mean_abs_contribution 表示该 feature 对模型输出的平均绝对影响大小。
mean_contribution 可以粗略看平均方向，但要注意 one-hot features 的方向解释需要结合具体类别。
```

这里没有画 beeswarm / waterfall 图，也没有安装外部 `shap` package。

所以当前完成的是：

```text
XGBoost native SHAP-style contribution summary
```

不是：

```text
full SHAP visualization package workflow
```

## Validation Checks

Input checks:

```text
rows = 112,650
eligible exposures = 110,197
train eligible exposures = 88,201
test eligible exposures = 21,996
test claims for severity = 1,715
unique exposure keys = 112,650
```

Feature count checks passed:

```text
transformed matrix columns = encoded feature names
frequency encoded features = 82
severity encoded features = 82
```

Leakage controls remain unchanged:

```text
seller_id_used_as_feature = false
excluded leakage fields = return_probability, covered_claim_probability,
return_factor_*, return_requested, return_reason, claim_type,
gross_loss, paid_loss, net_loss, claim_status
```

## Frequency Model Findings

This section uses two different explanation sources:

```text
Base feature contribution table:
from SHAP-style contribution summary

Encoded feature gain list:
from XGBoost built-in feature importance
```

Top base features by mean absolute contribution:

| Base Feature | Contribution Share |
|---|---:|
| category_group | 25.74% |
| cross_state_flag_cat | 16.82% |
| purchase_month_cat | 10.10% |
| log_freight_to_price_ratio_capped | 10.06% |
| log_product_weight_g_filled | 7.98% |
| route_group | 7.68% |
| log_price | 6.16% |
| log_estimated_delivery_days | 5.22% |

Interpretation:

```text
Frequency risk is driven by category, route/cross-state movement,
seasonality, freight-to-price ratio, product weight, and price.
```

This is directionally reasonable for return-shipping insurance:

```text
category affects return behavior
route and cross-state flag affect logistics risk
freight-to-price ratio affects return economics
weight and size affect shipping friction
month captures seasonality / campaign timing
```

Top encoded features by gain include:

Source:

```text
data/processed/xgboost_frequency_feature_importance.csv
metric = gain
```

```text
cross_state_flag_cat_0
cross_state_flag_cat_1
route_group_SP_to_SP
category_group_fashion_bags_accessories
category_group_health_beauty
log_freight_to_price_ratio_capped
category_group_electronics
log_product_weight_g_filled
```

This suggests the model is learning recognizable pricing signals rather than obviously invalid fields.

## Severity Model Findings

This section primarily uses SHAP-style contribution summary.

Source:

```text
data/processed/xgboost_severity_base_feature_summary.csv
metric = mean_abs_contribution_share
```

Top base features by mean absolute contribution:

| Base Feature | Contribution Share |
|---|---:|
| log_freight_value_capped | 80.69% |
| cross_state_flag_cat | 4.47% |
| log_price | 3.78% |
| log_freight_to_price_ratio_capped | 2.61% |
| category_group | 2.06% |
| route_group | 1.67% |
| log_product_weight_g_filled | 1.49% |
| purchase_month_cat | 1.20% |

Interpretation:

```text
Severity is overwhelmingly driven by freight value.
```

This is expected because the current coverage is:

```text
Coverage A: Return Shipping
```

and claim severity is linked to return shipping cost rather than product refund amount.

This supports the project logic:

```text
Frequency model explains who is likely to claim.
Severity model explains how expensive the shipping claim is if it happens.
```

The corresponding XGBoost built-in feature importance output is available here:

```text
data/processed/xgboost_severity_feature_importance.csv
```

In that file, `gain` is tree-split importance, while the table above is SHAP-style contribution share. The two views are related but not identical:

```text
gain:
which features improve tree splits

SHAP-style contribution:
which features move predictions on average
```

## Governance Interpretation

The interpretability results support keeping XGBoost as a challenger:

```text
The model uses plausible signals.
It does not rely on leakage fields.
It can slightly improve frequency ranking after regularization.
But GLM remains better calibrated for pure premium and loss ratio.
```

This is a useful interview conclusion:

```text
XGBoost is not rejected because it is wrong.
It is held as a challenger because its ranking signal is plausible,
but its pricing calibration has not yet justified replacing GLM.
```

## Limitations

The contribution outputs are not causal explanations.

They explain:

```text
how the fitted XGBoost model uses features
```

not:

```text
how the real world causally produces claims
```

Also, because the project uses synthetic claims, these importance patterns should be treated as framework validation rather than real TikTok Shop pricing evidence.
