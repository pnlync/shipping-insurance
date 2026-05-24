# 32 Interview Deck Outline

本文档是面试展示用的 deck narrative，不是最终 PPTX。

目标：

```text
把项目讲成一个完整的保险定价工作流，
而不是一堆零散的数据清洗、模型和输出表。
```

建议最终 deck 控制在：

```text
12 slides
10-15 minutes presentation
```

## 1. One-Minute Project Pitch

可以这样开场：

```text
I built an exposure-level return-shipping insurance pricing framework for e-commerce sellers.

The project is not a generic return prediction model.
It starts from a correct insurance exposure definition,
then builds a synthetic claims layer, baseline pricing,
two-part GLM pricing, seller credibility adjustment,
loss ratio monitoring, stress testing,
and finally an XGBoost challenger model with governance and interpretability.

The core pricing unit is order_id + order_item_id + seller_id + product_id,
because freight cost and seller attribution live at order-item level.

My final recommendation is to keep GLM + seller credibility as the current champion pricing basis,
while using XGBoost as a challenger risk score because it slightly improves frequency ranking
but does not beat GLM on pure premium calibration.
```

中文表达：

```text
我做的是一个面向电商中小卖家的退货运费险定价框架，
不是普通的退货预测模型。

我从 exposure 定义开始，把 Olist 订单明细转成保险风险暴露，
再构造 synthetic returns + claims layer，
做 baseline、GLM frequency/severity、seller credibility、
loss ratio monitoring、stress testing，
最后用 XGBoost 做 challenger model 和解释性分析。

最终结论是：GLM + seller credibility 更适合作为当前主定价模型；
XGBoost 可以作为 challenger risk score，因为它排序略好，
但 pure premium A/E 和 loss ratio calibration 不如 GLM。
```

## 2. Core Interview Message

整套展示只围绕一个主线：

```text
Insurance pricing is expected loss pricing under business constraints.
```

不要把项目讲成：

```text
I trained GLM and XGBoost and compared AUC.
```

要讲成：

```text
I designed a pricing framework:
1. define insurable exposure correctly
2. define claim and coverage consistently
3. estimate expected loss
4. convert expected loss into commercial premium
5. adjust seller experience with credibility
6. monitor loss ratio
7. stress test adverse scenarios
8. test challenger models without losing pricing governance
```

## 3. Recommended Slide Structure

### Slide 1: Title and Positioning

Title:

```text
Return-Shipping Insurance Pricing Engine for E-commerce Sellers
```

Subtitle:

```text
Exposure-level actuarial pricing workflow with GLM, credibility, monitoring, stress testing, and XGBoost challenger
```

What to show:

```text
One clean architecture line:
Exposure table -> Synthetic claims -> GLM pricing -> Credibility -> Monitoring -> Stress testing -> XGBoost challenger
```

Speaker notes:

```text
I would position this as an actuarial pricing project, not a generic machine learning project.
The key question is not only who returns an item, but how much expected insurance loss each exposure should carry.
```

### Slide 2: Business Problem and Product Assumption

Main point:

```text
The business needs a dynamic premium for return-shipping insurance.
```

Coverage assumption:

```text
Coverage A: Return Shipping
covered loss = compliant buyer return shipping cost
```

Not covered:

```text
product refund itself
fraud
refund without return
failed delivery / replacement shipping in first version
non-delivered exposure
```

Suggested visual:

```text
Simple product boundary box:
Covered / Not Covered
```

Speaker notes:

```text
I explicitly separated e-commerce return behavior from insurance claim cost.
A return event is not automatically an insurance claim.
The first version prices only return shipping coverage to keep the product scope clean.
```

### Slide 3: Exposure Definition

Main point:

```text
Correct exposure definition is the foundation of pricing.
```

Core exposure key:

```text
order_id + order_item_id + seller_id + product_id
```

Why not `order_id` alone:

```text
one order can contain multiple items
one order can involve multiple sellers
freight_value is recorded at order-item level
premium and claim cost should be attributed to item/seller level
```

Key metrics:

```text
total rows = 112,650
eligible exposures = 110,197
ineligible exposures = 2,453
```

Suggested visual:

```text
Small hierarchy:
Portfolio -> Seller -> Order -> Order Item Exposure
```

Speaker notes:

```text
This is one of the most important actuarial decisions in the project.
If I priced at order_id level, I would misattribute freight cost and seller risk.
```

### Slide 4: Data and Synthetic Claims Layer

Main point:

```text
Olist has real e-commerce logistics data, but no real insurance claims.
```

Project solution:

```text
Build synthetic returns + claims layer.
```

Two-layer design:

```text
returns layer:
return_requested, return_approved, refund_without_return, return_reason

claims layer:
covered_claim_flag, claim_type, gross_loss, recovery, paid_loss, net_loss
```

Key metrics:

```text
eligible exposures = 110,197
return requested count = 9,338
covered claim count = 8,485
covered claim frequency = 7.70%
total net loss = 163,112.68
average severity = 19.22
```

Speaker notes:

```text
I did not just create a return_flag.
The claim layer is insurance-style: frequency target is covered_claim_flag,
and severity target is net_loss on covered claims only.
```

### Slide 5: Baseline Pricing

Main point:

```text
Start with a simple actuarial benchmark before modelling.
```

Formula:

```text
portfolio pure premium = total net loss / eligible exposures
commercial premium = pure premium / target loss ratio
```

Results:

```text
target loss ratio = 60%
portfolio pure premium = 1.4802
portfolio commercial premium = 2.4670
expected loss ratio = 60.00%
```

Suggested visual:

```text
Formula card + one small table
```

Speaker notes:

```text
Baseline is not a final model.
It is the control model: everyone gets the same price, so it cannot differentiate category, route, freight, or seller risk.
```

### Slide 6: GLM Pricing Model

Main point:

```text
GLM is the champion pricing model because it is explainable and calibrated.
```

Two-part GLM:

```text
frequency = Binomial GLM, target covered_claim_flag
severity = Gamma GLM, target net_loss on covered claims only
expected loss = frequency * severity
```

Allowed quote-time features:

```text
category
route
cross-state flag
purchase month / weekday
price
freight value
freight-to-price ratio
weight / volume
estimated delivery days
```

Explicit leakage exclusions:

```text
return_requested
return_reason
covered_claim_probability
return_factor_*
claim_type
paid_loss
net_loss
claim_status
```

Validation:

```text
test frequency AUC = 0.560
test pure premium A/E = 1.003
test predicted pure premium = 1.503
test actual pure premium = 1.508
```

Speaker notes:

```text
The frequency AUC is moderate, but pricing calibration is strong.
For insurance pricing, that matters because we are pricing expected loss, not only ranking individual claims.
```

### Slide 7: Seller Credibility Adjustment

Main point:

```text
Seller experience matters, but direct seller_id modelling is unstable.
```

Reason:

```text
2,970 sellers with eligible exposure
median eligible exposures per seller = 8
only 29 sellers have >= 500 exposures
```

Credibility formula:

```text
seller_observed_ae = seller_actual_net_loss / seller_glm_expected_loss
Z = n / (n + 500)
seller relativity = Z * seller_observed_ae + (1 - Z) * 1.0
```

Important clarification:

```text
Shrinkage target = seller's GLM base expected loss
not portfolio average price
```

Risk controls:

```text
raw relativity cap = 0.50 to 2.00
portfolio normalization preserves total GLM expected loss
```

Speaker notes:

```text
This is where the project becomes more actuarial.
Instead of letting a machine learning model memorize seller_id,
I use credibility to let larger sellers carry more of their own experience
while small sellers remain close to their GLM risk mix.
```

### Slide 8: Loss Ratio Monitoring

Main point:

```text
Portfolio A/E close to 1 is not enough.
Pricing must be monitored by segment.
```

Portfolio result:

```text
baseline loss ratio = 60.00%
GLM loss ratio = 59.37%
GLM + credibility loss ratio = 59.37%
```

Seller tier result:

```text
near_glm credibility loss ratio = 58.31%
elevated credibility loss ratio = 81.53%
lower_than_glm credibility loss ratio = 43.73%
```

Suggested visual:

```text
Bar chart: loss ratio by seller risk tier
```

Speaker notes:

```text
The portfolio looks adequate, but elevated sellers remain above target.
That gives a practical underwriting watchlist rather than just a model score.
```

### Slide 9: Stress Testing

Main point:

```text
A model can be calibrated today but still fragile under adverse scenarios.
```

Stress results:

```text
base observed loss ratio = 59.37%
frequency +20% = 71.25%
severity +20% = 71.25%
combined +10%/+10% = 71.84%
combined +20%/+20% = 85.50%
```

Suggested visual:

```text
Scenario bar chart:
base, freq +10, freq +20, severity +10, severity +20, combined +20/+20
```

Speaker notes:

```text
This is a pricing governance step.
It shows that current premiums are close to target in base conditions,
but a simultaneous frequency and severity deterioration creates high pressure.
```

### Slide 10: XGBoost Challenger

Main point:

```text
XGBoost is tested as challenger, not assumed to be final model.
```

Model structure:

```text
frequency = XGBClassifier
severity = XGBRegressor on log1p(net_loss)
expected loss = frequency * severity
```

Parameter sweep insight:

```text
first XGBoost was too flexible:
train AUC = 0.635
test AUC = 0.555

regularized XGBoost:
train AUC = 0.589
test AUC = 0.561
```

Final comparison:

```text
GLM test AUC = 0.5598
XGBoost test AUC = 0.5609

GLM pure premium A/E = 1.0030
XGBoost pure premium A/E = 1.0145

GLM loss ratio = 60.18%
XGBoost loss ratio = 60.87%
```

Speaker notes:

```text
XGBoost slightly improves frequency ranking,
but it does not improve pricing calibration.
That is why it remains a challenger risk score rather than replacing GLM.
```

### Slide 11: XGBoost Interpretability

Main point:

```text
The challenger uses plausible signals, but this does not override calibration.
```

Frequency top base features by SHAP-style contribution:

```text
category_group = 25.74%
cross_state_flag = 16.82%
purchase_month = 10.10%
freight_to_price_ratio = 10.06%
product_weight = 7.98%
route_group = 7.68%
```

Severity top base feature:

```text
freight_value_capped = 80.69%
```

Important note:

```text
These are XGBoost native SHAP-style contribution summaries,
not external shap package beeswarm / waterfall plots.
```

Speaker notes:

```text
The interpretation is directionally sensible.
Frequency is driven by category, route, seasonality, freight ratio, and weight.
Severity is mostly driven by freight value, which matches Coverage A: Return Shipping.
```

### Slide 12: Final Recommendation and Production Roadmap

Final recommendation:

```text
Use GLM expected loss + seller credibility as current technical pricing basis.
Use XGBoost as challenger risk score and monitoring layer.
Do not replace GLM with XGBoost yet.
```

Why:

```text
GLM is explainable and better calibrated.
Seller credibility handles seller experience in a controlled actuarial way.
XGBoost adds a plausible nonlinear benchmark but does not yet justify production replacement.
```

Production roadmap:

```text
replace synthetic claims with real TikTok Shop order / return / claim data
use historical train + future validation
add claim development / IBNR
add expense / commission / capital assumptions
define underwriting rules for elevated seller tiers
monitor drift, A/E, loss ratio, and stress indicators
```

Closing line:

```text
The value of the project is not one model score.
The value is a pricing workflow that connects exposure definition,
expected loss modelling, credibility, monitoring, stress testing, and model governance.
```

## 4. Suggested Visuals and Source Files

| Slide | Visual | Source |
|---|---|---|
| 1 | Pricing workflow diagram | project docs / manual diagram |
| 3 | Exposure hierarchy | `03_exposure_definition.md` |
| 4 | Claims layer table | `synthetic_claims_summary.json` |
| 5 | Baseline premium formula | `pricing_baseline_summary.json` |
| 6 | GLM validation table | `glm_pricing_summary.json` |
| 7 | Seller credibility formula and distribution | `seller_credibility_summary.json` |
| 8 | Loss ratio by seller tier | `backtest_by_seller_tier.csv` |
| 9 | Stress scenario bar chart | `stress_test_portfolio.csv` |
| 10 | GLM vs XGBoost table | `model_comparison_glm_vs_xgboost.csv` |
| 11 | XGBoost top features | `xgboost_*_base_feature_summary.csv` |
| 12 | Final recommendation | `29_model_selection_and_governance.md` |

## 5. Questions to Prepare For

### Why not use `order_id` as exposure?

Answer:

```text
Because freight_value and seller attribution are at order-item level.
A single order can have multiple products or sellers.
Pricing at order_id level would misattribute risk and premium.
```

### Why use synthetic claims?

Answer:

```text
Olist has real e-commerce logistics data but no real insurance claim data.
The synthetic layer lets me demonstrate a transferable pricing framework.
For production, I would replace it with real return and claim experience.
```

### Why not put `seller_id` directly in GLM or XGBoost?

Answer:

```text
Most sellers have small exposure counts.
Direct seller_id modelling would overfit and produce unstable seller relativities.
I use GLM for base risk and credibility for seller experience.
```

### Why is AUC not high?

Answer:

```text
AUC only measures frequency ranking.
The claim event is low-frequency and noisy, and pricing features are restricted to quote-time-known variables.
More importantly, GLM pure premium A/E is close to 1, meaning expected loss level is well calibrated.
```

### Why not choose XGBoost if its AUC is slightly higher?

Answer:

```text
Because pricing is not only ranking.
XGBoost AUC is slightly higher, but GLM has better pure premium A/E and loss ratio calibration.
For current pricing, GLM remains champion and XGBoost remains challenger.
```

### What would you do with real TikTok Shop data?

Answer:

```text
Use real order, shipment, return, refund, and claim tables.
Build historical training and future validation periods.
Estimate claim development and IBNR.
Validate by seller, category, route, and cohort.
Then decide whether GLM, XGBoost, or a hybrid rating approach is production appropriate.
```

### What is the biggest limitation?

Answer:

```text
Synthetic claims.
The framework is realistic, but numerical rates are not production rates.
The next real step is replacing synthetic claims with actual seller claim experience.
```

## 6. What Not to Overclaim

Do not say:

```text
This is a production TikTok Shop rate.
XGBoost is the best model.
AUC proves the pricing model is good.
Synthetic claims prove real profitability.
```

Say instead:

```text
This is a transferable actuarial pricing framework.
The numerical results are based on synthetic claims.
The project demonstrates exposure definition, expected loss modelling,
credibility, monitoring, stress testing, and challenger governance.
```

## 7. Final Deck Narrative

The story in one paragraph:

```text
I built a return-shipping insurance pricing framework at the correct exposure level.
Because Olist has logistics but no insurance claims, I created a synthetic claims layer
that separates returns from covered claims.
I started with a portfolio-average baseline, then built a two-part GLM for expected loss.
I added seller credibility to handle sparse seller experience,
then monitored loss ratio and stress tested adverse scenarios.
Finally, I tested XGBoost as a challenger.
It slightly improved frequency ranking after regularization,
but GLM remained better calibrated for pure premium and loss ratio.
Therefore my current recommendation is GLM + seller credibility as champion pricing,
with XGBoost retained as a challenger risk score and interpretability layer.
```
