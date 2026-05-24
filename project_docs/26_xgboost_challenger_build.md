# 26 XGBoost Challenger Build

## What Was Built

Phase 4 first built the challenger model and comparison layer.

New script:

```text
src/build_xgboost_challenger.py
```

New processed outputs:

```text
data/processed/pricing_xgboost_challenger.csv
data/processed/xgboost_challenger_summary.json
data/processed/model_comparison_glm_vs_xgboost.csv
data/processed/xgboost_challenger_pure_premium_calibration.csv
```

The script follows the same two-part insurance structure as GLM:

```text
frequency target = covered_claim_flag
severity target = net_loss on covered claims only
pure premium = frequency * severity
```

## Package Used

The first run used the sklearn fallback because `xgboost` was not installed.

After that, the environment was updated:

```text
brew install libomp
python -m pip install xgboost
```

Current local environment:

```text
xgboost installed = true
xgboost version = 3.2.0
actual model family = xgboost
```

`libomp` is installed through Homebrew so the native runtime dependency is easier to manage outside the Python package.

The frequency model parameters were updated after a small parameter sweep. See:

```text
28_xgboost_parameter_sweep.md
```

## Leakage Controls

The challenger used only quote-time-known variables:

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

It did not use outcome, post-bind, or synthetic generation fields as features:

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

`covered_claim_flag` and `net_loss` were used only as targets.

`seller_id` was not used as a direct model feature. Seller-specific experience remains in the Phase 3 credibility layer, where the shrinkage target is GLM base expected loss.

## Validation Method

The script used an order-level split:

```text
test size = 20%
random seed = 20260521
train eligible exposures = 88,201
test eligible exposures = 21,996
```

GLM was refit on the same split for a fair comparison. The challenger was reported in two forms:

```text
raw challenger
portfolio-calibrated challenger
```

The calibrated version applies the train-set pure-premium A/E as a multiplicative adjustment, then evaluates that adjusted score on the test set.

## Core Test Results

| Model | Frequency AUC | Brier | Pure Premium A/E | Predicted Pure Premium | Loss Ratio |
|---|---:|---:|---:|---:|---:|
| GLM | 0.560 | 0.0717 | 1.003 | 1.503 | 60.18% |
| XGBoost challenger raw | 0.561 | 0.0717 | 1.031 | 1.462 | 61.86% |
| XGBoost challenger calibrated | 0.561 | 0.0717 | 1.014 | 1.486 | 60.87% |

Interpretation:

```text
After regularizing the frequency model, XGBoost slightly improves test AUC versus GLM.
However, its pure premium A/E and loss ratio calibration are still weaker than GLM.
```

Training frequency AUC for XGBoost is 0.589 and test AUC is 0.561. This is a more stable challenger than the first over-flexible XGBoost run.

## Calibration Review

The calibrated challenger improved portfolio-level A/E compared with the raw challenger:

```text
raw test pure premium A/E = 1.031
calibrated test pure premium A/E = 1.014
```

But it still underpredicted test loss slightly:

```text
actual pure premium = 1.508
calibrated predicted pure premium = 1.486
loss ratio = 60.87%
```

The target loss ratio is 60%, so this is close but not better than GLM's 60.18% on the same test split.

## Final Exposure-Level Output

The final output keeps one row per exposure:

```text
rows = 112,650
unique exposure keys = 112,650
eligible exposures = 110,197
```

Validation checks:

```text
ineligible challenger expected loss nonzero = 0
ineligible challenger commercial premium nonzero = 0
```

The final full-data challenger output is portfolio-calibrated as a diagnostic pricing layer:

```text
actual total net loss = 163,112.68
challenger expected total loss = 163,112.69
challenger commercial premium = 271,854.47
portfolio loss ratio = 60.00%
```

This final calibration uses all current synthetic data, so it should be treated as an analytical comparison output, not as proof of production performance.

## Conclusion

The Phase 4 challenger layer is now built and verified.

Current conclusion:

```text
Do not replace GLM with the XGBoost challenger.
```

Reason:

```text
XGBoost now has slightly better test AUC, but GLM still has better pure premium A/E and loss-ratio calibration.
The challenger is still useful as a risk-score experiment and as evidence that model choice was tested rather than assumed.
```

Recommended next step:

```text
Add SHAP / feature importance only after deciding whether the challenger adds enough value.
Given these results, a better next step may be interview explanation and model governance notes before building a dashboard.
```
