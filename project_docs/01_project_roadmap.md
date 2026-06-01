# 01 Project Roadmap

## Project Goal

Build a dynamic pricing project for return shipping insurance aimed at small and medium-sized TikTok Shop sellers.

The project focus is not simply to predict return rates, but to build a complete insurance pricing workflow:

```text
data definitions -> exposure table -> synthetic claims layer -> pure premium -> commercial premium
-> loss ratio monitoring -> credibility -> stress testing -> pricing memo
```

## Execution Phases

### Phase 1: Exposure Table + Baseline Pricing

Objective:

```text
generate an exposure-level modeling table
simulate the first version of the synthetic returns and insurance claims layer
calculate baseline pure premium and commercial premium
```

Core outputs:

```text
data/processed/exposure_table.csv
data/processed/pricing_baseline.csv
```

### Phase 2: GLM Pricing

Objective:

```text
build a claim frequency model
build a claim severity model
calculate exposure-level expected loss
check A/E ratio and calibration
```

### Phase 3: Actuarial Enhancements

Objective:

```text
seller credibility
loss ratio backtesting
stress testing
pricing memo
```

### Phase 4: Interview Presentation

Objective:

```text
XGBoost challenger
Streamlit dashboard
interview deck
final README polish
```

## Current Priority

The first versions of Phase 1, Phase 2, and Phase 3 are complete.

Phase 4 has started. So far, only the challenger model and GLM comparison are complete.

Do not move directly into SHAP, the dashboard, or a PDF report unless the decision is made to continue into the presentation layer.

Current progress:

```text
data understanding: done
field dictionary: done
data audit: done
exposure table build: done
exposure-level EDA: done
synthetic claims: done
baseline pricing: done
GLM pricing design: done
GLM pricing build: done
seller credibility design: done
seller credibility build: done
loss ratio backtesting design: done
loss ratio backtesting build: done
stress testing design: done
stress testing build: done
pricing memo: done
Phase 3 documentation review: done
XGBoost challenger: done with xgboost 3.2.0
GLM vs challenger comparison: done
XGBoost parameter sweep: done
model selection / governance note: done
XGBoost interpretability: done
interview deck outline: done
dashboard: not started
PPTX interview deck: not started
```

## Phase 4 Current Conclusion

Currently installed and used:

```text
xgboost 3.2.0
```

Validation results:

```text
GLM test frequency AUC = 0.560
XGBoost challenger calibrated test frequency AUC = 0.561
GLM test loss ratio = 60.18%
XGBoost challenger calibrated test loss ratio = 60.87%
```

Therefore, the challenger should not currently replace the final pricing model. XGBoost is slightly better than the GLM on frequency ranking, but its pricing calibration remains weaker.

Its value is:

```text
1. It demonstrates that the project includes a champion-challenger comparison.
2. It shows that a more complex model is not necessarily better for pricing calibration.
3. It provides a basis for later SHAP / feature importance / model governance work.
```
