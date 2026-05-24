# Shipping Insurance Pricing Project

Exposure-level return-shipping insurance pricing project for an e-commerce seller setting.

The project is built as an actuarial pricing workflow, not a generic return prediction model:

```text
exposure table
-> synthetic returns and claims
-> baseline pricing
-> GLM frequency / severity pricing
-> seller credibility
-> loss ratio monitoring
-> stress testing
-> pricing memo
```

## Current Status

```text
Phase 1: completed
Phase 2: completed
Phase 3: first-version actuarial workflow completed
Phase 4: challenger model, interpretability, and interview deck outline completed
```

Phase 4 currently includes the XGBoost challenger comparison, parameter sweep, model governance note, native SHAP-style interpretability summary, and interview deck outline. Dashboard and PPTX deck are intentionally not built yet.

## Core Pricing Unit

The base exposure is:

```text
order_id + order_item_id + seller_id + product_id
```

Do not treat `order_id` alone as the exposure key. Olist freight is recorded at order-item level, and a single order can include multiple products or sellers.

## Main Outputs

Key processed outputs:

```text
data/processed/exposure_table.csv
data/processed/exposure_claims_synthetic.csv
data/processed/pricing_baseline.csv
data/processed/pricing_glm.csv
data/processed/pricing_glm_credibility.csv
data/processed/pricing_xgboost_challenger.csv
data/processed/model_comparison_glm_vs_xgboost.csv
data/processed/loss_ratio_backtesting_summary.json
data/processed/stress_testing_summary.json
data/processed/xgboost_challenger_summary.json
data/processed/xgboost_interpretability_summary.json
```

Main narrative memo:

```text
project_docs/23_pricing_memo.md
```

Current challenger notes:

```text
project_docs/25_xgboost_challenger_design.md
project_docs/26_xgboost_challenger_build.md
project_docs/29_model_selection_and_governance.md
project_docs/31_xgboost_interpretability_build.md
project_docs/32_interview_deck_outline.md
```

The current local run uses `xgboost 3.2.0`. Homebrew `libomp` is installed as the native runtime dependency.

Recommended documentation entry point:

```text
project_docs/README.md
project_docs/01_project_roadmap.md
project_docs/23_pricing_memo.md
project_docs/decision_log.md
```

## Running the Pipeline

List available steps:

```bash
python main.py --list
```

Run the full current pipeline:

```bash
python main.py --run all
```

Run only the current Phase 3 actuarial outputs:

```bash
python main.py --run phase3
```

Run only the current Phase 4 challenger and interpretability layer:

```bash
python main.py --run phase4
```

Individual steps are also available, for example:

```bash
python main.py --run stress
python main.py --run challenger
python main.py --run interpretability
```

## Important Limitations

This project uses Olist public e-commerce data and a synthetic claims layer. It demonstrates a transferable pricing framework, but the numerical rates are not production TikTok Shop insurance rates.

Real deployment would require:

```text
real order / return / claim data
historical training and future validation periods
claim development and IBNR treatment
explicit expense / capital / reinsurance assumptions
underwriting and compliance review
```
