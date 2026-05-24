# 30 XGBoost Interpretability Design

## Purpose

Phase 4 已经完成：

```text
XGBoost challenger
parameter sweep
model selection / governance note
```

下一步不是 dashboard，而是先解释：

```text
XGBoost 到底靠哪些 factors 做 risk ranking？
这些 signals 是否符合业务和精算直觉？
```

这个解释层可以支持后续：

```text
SHAP discussion
interview deck
dashboard
underwriting / risk flag rules
```

## What Will Be Explained

XGBoost 仍保持 two-part structure：

```text
frequency model:
target = covered_claim_flag

severity model:
target = log1p(net_loss)
population = covered claims only
```

因此 interpretability 也分两部分：

```text
frequency feature importance
frequency contribution summary
severity feature importance
severity contribution summary
```

## Method

Use two complementary explanations.

### 1. Built-in XGBoost Importance

XGBoost can report feature importance from tree splits.

The script records:

```text
gain
weight
cover
total_gain
total_cover
```

Main metric:

```text
gain
```

Interpretation:

```text
gain = how much a feature improves split quality on average
```

This is useful for ranking features but does not show direction.

### 2. Native XGBoost SHAP-Style Contributions

The local environment does not need the external `shap` package.

XGBoost supports native contribution output:

```text
booster.predict(DMatrix, pred_contribs=True)
```

The script uses this to produce SHAP-style summaries:

```text
mean_abs_contribution
mean_contribution
positive_share
p05 / p50 / p95 contribution
```

For the frequency classifier, contribution is on the model margin / log-odds scale.

For the severity regressor, contribution is on the `log1p(net_loss)` scale.

Important limitation:

```text
These are model-scale explanations, not direct premium-dollar explanations.
```

## Feature Grouping

The model one-hot encodes categorical variables.

For example:

```text
category_group_fashion_bags_accessories
route_group_SP_RJ
purchase_month_cat_11
```

The script outputs two levels:

```text
encoded feature level:
specific one-hot / numeric transformed feature

base feature level:
category_group, route_group, purchase_month_cat, log_price, etc.
```

Base feature grouping is useful for interview explanation because it answers:

```text
Is XGBoost mostly using category, route, freight, size, or timing?
```

## Leakage Controls

The interpretability script retrains the same XGBoost challenger using the same allowed features:

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

It does not add:

```text
seller_id
product_id
customer_id
order_id
return_probability
covered_claim_probability
return_factor_*
return_requested
return_reason
claim_type
gross_loss
paid_loss
net_loss
claim_status
```

Targets are used only for fitting and validation summaries.

## Expected Outputs

```text
src/build_xgboost_interpretability.py
data/processed/xgboost_interpretability_summary.json
data/processed/xgboost_frequency_feature_importance.csv
data/processed/xgboost_severity_feature_importance.csv
data/processed/xgboost_frequency_shap_summary.csv
data/processed/xgboost_severity_shap_summary.csv
data/processed/xgboost_frequency_base_feature_summary.csv
data/processed/xgboost_severity_base_feature_summary.csv
project_docs/31_xgboost_interpretability_build.md
```

## How to Use the Result

If XGBoost importance mostly aligns with known pricing logic, then it supports the model governance story:

```text
XGBoost is not obviously learning unreasonable signals.
```

If it relies heavily on unstable or hard-to-explain variables, that supports keeping it as challenger only.

Either outcome is useful, because the goal is not to force XGBoost into production pricing. The goal is to understand what it learned.
