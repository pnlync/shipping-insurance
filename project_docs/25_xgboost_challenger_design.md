# 25 XGBoost Challenger Design

## Purpose

Phase 4 starts with a challenger model, not with a dashboard or interview deck.

The goal is to test whether a tree-based model can improve risk ranking compared with the Phase 2 GLM, while keeping the actuarial pricing discipline:

```text
frequency = covered_claim_flag
severity = net_loss on covered claims only
pure premium = frequency * severity
commercial premium = pure premium / target_loss_ratio
```

The challenger is not automatically the final pricing model. In this project it is a comparison layer and risk score candidate.

## Exposure Level

The modelling row remains:

```text
order_id + order_item_id + seller_id + product_id
```

This is unchanged from Phase 1 to Phase 3.

## Model Structure

Use the same two-part structure as the GLM:

```text
Frequency challenger:
predict covered_claim_flag on all eligible exposures

Severity challenger:
predict net_loss on covered claims only

Expected loss:
challenger_frequency * challenger_severity
```

This keeps the comparison meaningful. A single model directly predicting total loss would mix claim probability and claim amount, which is harder to explain in insurance terms.

## Feature Eligibility

The challenger can only use variables known at quote time.

Allowed feature families:

```text
product category
route state
cross-state flag
purchase month
purchase weekday
price
freight value
freight-to-price ratio
product weight
product volume
estimated delivery days
```

Excluded leakage fields:

```text
return_probability
covered_claim_probability
return_factor_*
return_requested
return_approved
refund_without_return
partial_refund
request_days_after_delivery
return_reason
claim_type
gross_loss
paid_loss
net_loss
claim_status
```

`covered_claim_flag` and `net_loss` are targets only. They are never input features.

`seller_id` is also not used as a direct model feature in this first challenger. Seller experience is handled through the Phase 3 credibility layer. Putting high-cardinality seller IDs directly into a tree model would risk overfitting small sellers and would blur the actuarial credibility story.

## Validation Design

Use the same order-level split principle as the GLM:

```text
train/test split is made by order_id
all exposures from the same order stay in the same split
test size = 20%
random seed = 20260521
```

Order-level splitting avoids having one item from an order in training and another item from the same order in testing.

## Metrics

The comparison must not rely on AUC only.

Frequency metrics:

```text
AUC: ranking of claim vs non-claim exposures
Brier score: probability calibration error
actual frequency vs predicted frequency
```

Severity metrics:

```text
actual severity vs predicted severity
MAE
RMSE
```

Pricing metrics:

```text
actual total net loss
predicted expected loss
A/E = actual loss / expected loss
actual pure premium
predicted pure premium
commercial premium
loss ratio = actual loss / commercial premium
```

Pure premium deciles are also reviewed. If the challenger ranks risk better but has weak A/E or loss ratio calibration, that should be recorded rather than hidden.

## Calibration Treatment

Tree-based models often rank risk well but may not be naturally calibrated to insurance rate level.

The script therefore records both:

```text
raw challenger expected loss
portfolio-calibrated challenger expected loss
```

The validation comparison includes a raw challenger row and a calibrated challenger row. Calibration uses the training set actual-to-expected ratio as a multiplicative adjustment, then checks the adjusted result on the test set.

For the final exposure-level output trained on all eligible data, the same idea is applied at portfolio level so that the challenger pricing level is comparable with GLM and baseline outputs. This is a modelling diagnostic, not a production pricing approval.

## Package Fallback

Preferred implementation:

```text
xgboost.XGBClassifier
xgboost.XGBRegressor
```

If `xgboost` is not installed locally, the script uses:

```text
sklearn.ensemble.HistGradientBoostingClassifier
sklearn.ensemble.HistGradientBoostingRegressor
```

In that case the output files keep the Phase 4 naming convention, but the summary explicitly states that the actual fitted model is the sklearn fallback, not true XGBoost.

## Expected Outputs

```text
src/build_xgboost_challenger.py
data/processed/pricing_xgboost_challenger.csv
data/processed/xgboost_challenger_summary.json
data/processed/model_comparison_glm_vs_xgboost.csv
data/processed/xgboost_challenger_pure_premium_calibration.csv
project_docs/26_xgboost_challenger_build.md
```
